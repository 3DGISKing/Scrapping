import json
import os
import re
import sqlite3
import requests
import pathvalidate
import time
from scrapy.http import TextResponse

g_outputPath = "D:\\Sci-hub"
if not os.path.exists(g_outputPath):
    g_outputPath = "E:\\Sci-hub"
g_downloadFailed = []
g_empty_doi = []
g_study_info_list = []
g_overwrite = False
g_retry_waiting = 2
g_writing_failed_path = "writing_failed"
if not os.path.exists(g_writing_failed_path):
    os.mkdir(g_writing_failed_path)

def add_faild_doi(doi_value):
    if doi_value not in g_downloadFailed:
        g_downloadFailed.append(doi_value)

def remove_faild_doi(doi_value):
    if doi_value in g_downloadFailed:
        g_downloadFailed.remove(doi_value)

def main():
    global g_outputPath

    doi_list_file = open('doi-list.txt', 'r')
    lines = doi_list_file.readlines()
    sqlite_conn = sqlite3.connect("index.db")
    cursor = sqlite_conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS journals (journal TEXT, title TEXT, year TEXT, month TEXT, filepath TEXT, doi TEXT NOT NULL UNIQUE)")

    doi_list = []
 
    count = 0
    # Strips the newline character
    for line in lines:
        doi_list.append(line.strip())

    sci_hub_url = "https://sci-hub.ru/"

    cur_downloading = 0

    path = os.path.join(g_outputPath, "")
    db_commit = 0

    for doi in doi_list:
        db_data = get_article_from_db(cursor, doi)
        if(len(db_data) > 0):
            print("Already downloaded for following DOI : {} - {}".format(cur_downloading, doi))
            cur_downloading = cur_downloading + 1
            continue
        study_info = get_study_info(doi)
        if not study_info:
            print("failed to get study info for following DOI : {} - {}".format(str(cur_downloading), doi))
            cur_downloading = cur_downloading + 1
            continue
        out_path = "{}/{}/{}".format(path, study_info["journal"], study_info["year"])
        if study_info["month"]:
            out_path = "{}/{}".format(out_path, study_info["month"])
        
        file_name = pathvalidate.sanitize_filename("{}.pdf".format(study_info["title"].strip("\{\}")))
        if(len(file_name) > 255):
            file_name = file_name[0:128]

        file_path = pathvalidate.sanitize_filepath(os.path.join(out_path, file_name))
        if os.path.exists(file_path):
            print("Already downloaded for following DOI : {} - {}".format(str(cur_downloading), doi))
            insert_article_db(cursor, study_info, doi, file_path)
            cur_downloading = cur_downloading + 1
        else:
            url = sci_hub_url + doi

            # print("requesting {}".format(url))

            resp = requests.get(url)
            textResp = TextResponse(url=url,
                                    body=resp.text,
                                    encoding='utf-8')
            
            pdf_url = textResp.xpath(
                '//div[@id="buttons"]/button').extract_first()
            
            if pdf_url == None:
                print("failed to get pdf url for following DOI : {}".format(doi))
                cur_downloading = cur_downloading + 1
                continue 
            
            start_keyword = "location.href=\'//"
            start = pdf_url.find(start_keyword)

            if start == -1:
                start_keyword = "location.href='/"
                start = pdf_url.find(start_keyword)

            if start == -1:
                print("unrecognized pdf url: {}".format(pdf_url))
                cur_downloading = cur_downloading + 1
                continue

            end = pdf_url.find('?download=true')

            pdf_url = pdf_url[start + len(start_keyword):end]

            # ex /tree/bb/56/bb5673427cd287fb70748d2ac813eeb2.pdf
            if pdf_url.find("tree/") != -1:
                pdf_url =  sci_hub_url + pdf_url
            else: 
                pdf_url =  "https://" + pdf_url
            
            if pdf_url.split("https://")[-1][:9] == "downloads":
                pdf_url =  "https://sci-hub.ru/" + pdf_url.split("https://")[-1]
            elif pdf_url.split("https://")[-1][:8] == "uptodate":
                pdf_url =  "https://sci-hub.ru/" + pdf_url.split("https://")[-1]


            print("downloading {} - {}".format(cur_downloading, len(doi_list)))

            retry_count = 0
            while retry_count < 5:
                retry_count += 1
                try:
                    respDownload = requests.get(pdf_url)
                except Exception as e:   
                    # tuple
                    add_faild_doi(doi) 

                    print("downloading failed {} - {} reason: {} url: {}".format(cur_downloading, len(doi_list), type(e), pdf_url))

                    time.sleep(g_retry_waiting)
                    if retry_count >= 5:
                        cur_downloading = cur_downloading + 1
                    continue

                print("size: {}, content-type: {}, url: {}".format(len(respDownload.content), respDownload.headers['Content-Type'], pdf_url))

                if len(respDownload.content) == 0:
                    add_faild_doi(doi) 
                    print("downloading failed {} - {} reason: zero content url: {}".format(cur_downloading, len(doi_list), pdf_url))
                    time.sleep(g_retry_waiting)
                    continue
                elif len(respDownload.content) == 146:
                    g_empty_doi.append(doi) 
                    print("There is no file doi: {}".format(doi))
                    cur_downloading = cur_downloading + 1
                    break
                elif len(respDownload.content) < 2048:
                    add_faild_doi(doi) 
                    print("downloading failed {} - {} reason: too small content url: {}".format(cur_downloading, len(doi_list), pdf_url))
                    time.sleep(g_retry_waiting)
                    continue
                elif respDownload.headers['Content-Type'] != 'application/pdf':
                    add_faild_doi(doi) 
                    print("downloading failed {} - {} reason: invalid content type - {}, url: {}, doi: {}".format(cur_downloading, len(doi_list), respDownload.headers.values['Content-Type'], pdf_url, doi))
                    time.sleep(g_retry_waiting)
                    continue

                written_file_name = write_file(respDownload, file_path)

                remove_faild_doi(doi)
                insert_article_db(cursor, study_info, doi, written_file_name)

                cur_downloading = cur_downloading + 1
                break
        db_commit = db_commit + 1
        if(db_commit >= 10):
            sqlite_conn.commit()
            print("index db committed!")
            db_commit = 0

def insert_article_db(db_cusour, study_info, doi, filepath):
    try:
       db_cusour.execute("INSERT INTO journals VALUES (?, ?, ?, ?, ?, ?)",
                      (study_info["journal"], study_info["title"], study_info["year"], study_info["month"], filepath, doi))
    except Exception as ex:
        print(ex)

def get_article_from_db(db_cursor, doi):
    try:
        db_cursor.execute("SELECT * FROM journals WHERE doi=?", (doi,) )
        rows = db_cursor.fetchall()
        return rows
    except Exception as ex:
        print(ex)
        return []

def get_study_info(doi):
    global g_outputPath

    url = "https://www.doi.org/{}".format(doi)

    payload = {}
    headers = {
        'Accept': 'application/x-bibtex; charset=utf-8'
    }

    repeat = True
    while repeat:
        try:
            repeat = False
            response = requests.request("GET", url, headers=headers, data=payload)
        except ConnectionError as ex:
            time.sleep(1)
            print("Connection error, retry!")
            repeat = True

    if response.status_code == 200:
        temp_str_list = response.text.split("\n")
        year = ""
        month = ""
        title = ""
        journal = ""
        for temp_str in temp_str_list:
            if "year =" in temp_str:
                year = temp_str.split("year =")[-1].strip()
                year = year[: len(year) - 1]
            elif "month =" in temp_str:
                month = temp_str.split("month =")[-1].split("{")[-1].split("}")[0].strip()
            elif "title =" in temp_str:
                title = temp_str.split("title =")[-1].strip()
            elif "journal =" in temp_str:
                journal = temp_str.split("journal =")[-1].split("{")[-1].split("}")[0].strip()
        
        if year and title and journal:
            # create directory
            journal_dir = "{}/{}".format(g_outputPath, journal)
            if not os.path.exists(journal_dir):
                os.mkdir(journal_dir)

            year_dir = "{}/{}".format(journal_dir, year)
            if not os.path.exists(year_dir):
                os.mkdir(year_dir)

            if month:
                month_dir = "{}/{}".format(year_dir, month)
                if not os.path.exists(month_dir):
                    os.mkdir(month_dir)

            return {
                "year": year,
                "month": month,
                "title" : title,
                "journal": journal
            }
    return None

def write_file(respDownload, file_path):
    try:
        if g_overwrite:
            os.remove(file_path)

        f = open(file_path, "wb")
        f.write(respDownload.content)
        f.close()
        return file_path
    except Exception as e:
        newFileName = "{}/{}.pdf".format(g_writing_failed_path, time.time())
        print("Failed to write file: {}\n saved this with name: {}".format(file_path, newFileName))
        f = open(newFileName, "wb")
        f.write(respDownload.content)
        f.close()
        return newFileName

    

def retry_failed_to_download():
    global g_outputPath, g_downloadFailed

    if len(g_downloadFailed) == 0:
        return
    
    new_failed = []

    retry_count = 0

    for failed in g_downloadFailed:
        downloadUrl = failed

        print("{}/{} Retrying downloading {}".format(retry_count, len(g_downloadFailed), downloadUrl))

        try:
            respDownload = requests.get(downloadUrl)
        except Exception as e:   
            new_failed.append((downloadUrl)) 
            print("downloading failed {}/{} reason: {} url: {}".format(retry_count, len(g_downloadFailed), type(e), downloadUrl))
            retry_count += 1
            continue

        print("size: {} url: {}".format(len(respDownload.content), downloadUrl))

        if len(respDownload.content) == 0:
            print("downloading failed {}/{} reason: zero content url: {}".format(retry_count, len(g_downloadFailed), downloadUrl))
            new_failed.append((downloadUrl)) 
            retry_count += 1
            continue

        if len(respDownload.content) < 1024:
            print("downloading failed {}/{} reason: too small content url: {}".format(retry_count, len(g_downloadFailed), downloadUrl))
            new_failed.append((downloadUrl)) 
            retry_count += 1
            continue


            
        write_file(respDownload)

        retry_count += 1

    if len(new_failed) > 0:
        g_downloadFailed = new_failed
        retry_failed_to_download()

main()

if len(g_downloadFailed) > 0:
    faild_doi_list_file = open('failed-doi-list.txt', 'w')
    faild_doi_list_file.write("\n".join(g_downloadFailed))
    faild_doi_list_file.close()

if len(g_empty_doi) > 0:
    empty_doi_list_file = open('empty-doi-list.txt', 'w')
    empty_doi_list_file.write("\n".join(g_empty_doi))
    empty_doi_list_file.close()

with open('index.json', 'w') as index_file:
    index_file.write("\n".join(json.dumps(g_study_info_list, indent=4)))
    index_file.close()
# retry_failed_to_download()

print("all done")

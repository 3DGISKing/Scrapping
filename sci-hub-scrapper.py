import os
import re
import requests
from scrapy.http import TextResponse

g_outputPath = "D:\\Sci-hub"
g_downloadFailed = []
g_overwrite = True

def main():
    global g_outputPath

    doi_list_file = open('doi-list.txt', 'r')
    lines = doi_list_file.readlines()

    doi_list = []
 
    count = 0
    # Strips the newline character
    for line in lines:
        doi_list.append(line.strip())

    sci_hub_url = "https://sci-hub.ru/"

    cur_downloading = 0;

    for doi in doi_list:
        study_info = get_study_info(doi)
        if not study_info:
            print("failed to get study info for following DOI : {}".format(doi))
            cur_downloading = cur_downloading + 1
            continue

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

        print("downloading {}/{}".format(cur_downloading, len(doi_list)))

        try:
            respDownload = requests.get(pdf_url)

        except Exception as e:   
            # tuple
            g_downloadFailed.append((pdf_url)) 

            print("downloading failed {}/{} reason: {} url: {}".format(cur_downloading, len(doi_list), type(e), pdf_url))
            cur_downloading = cur_downloading + 1
            continue

        print("size: {} url: {}".format(len(respDownload.content), pdf_url))

        if len(respDownload.content) == 0:
            g_downloadFailed.append((pdf_url)) 
            print("downloading failed {}/{} reason: zero content url: {}".format(cur_downloading, len(doi_list), pdf_url))
            cur_downloading = cur_downloading + 1
            continue

        if len(respDownload.content) < 1024:
            g_downloadFailed.append((pdf_url)) 
            print("downloading failed {}/{} reason: too small content url: {}".format(cur_downloading, len(doi_list), pdf_url))
            cur_downloading = cur_downloading + 1
            continue

        write_file(respDownload, study_info)

        cur_downloading = cur_downloading + 1

def get_study_info(doi):
    global g_outputPath

    url = "https://www.doi.org/{}".format(doi)

    payload = {}
    headers = {
        'Accept': 'application/x-bibtex; charset=utf-8'
    }

    response = requests.request("GET", url, headers=headers, data=payload)
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
                title = temp_str.split("title =")[-1].split("{")[-1].split("}")[0].strip()
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

def write_file(respDownload, study_info):
    global g_outputPath, g_overwrite

    path = os.path.join(g_outputPath, "");

    out_path = "{}/{}/{}".format(path, study_info["journal"], study_info["year"])
    if study_info["month"]:
        out_path = "{}/{}".format(out_path, study_info["month"])
    
    file_name = "{}.pdf".format(study_info["title"])

    fileName = os.path.join(out_path, file_name);

    if os.path.exists(fileName):
        if g_overwrite:
            os.remove(fileName)
        else:
            return

    f = open(fileName, "wb")
    f.write(respDownload.content)
    f.close()
    

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

retry_failed_to_download()

print("all done")
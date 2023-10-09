import argparse
import requests
import json
import os
import time
from scrapy.http import TextResponse
import threading

g_doi_pattern = ""
g_output_path = ""

g_full_doi_list_file_path = "sci-hub-doi-2022-02-12.txt"
# g_full_doi_list_file_path = "doi_list_full_test_100.txt"
g_new_doi_list_file_path = "doi-list.json"
g_doi_pattern_list = []
g_download_started_dois = []
g_data = []
g_count_of_started = 0
g_thread_lock = threading.Lock()
g_used_pdf_file_full_path_list = [];


def get_journal_info(doi):
    url = "https://www.doi.org/{}".format(doi)

    payload = {}
    headers = {
        'Accept': 'application/json; charset=utf-8'
    }

    try: 
        response = requests.request("GET", url, headers=headers, data=payload)

    except Exception as e:   
        print("failed to get journal info for doi: {} reason: {}".format(doi, type(e)))
        return None
    
    if url == 'https://www.doi.org/10.1007/1-4020-0613-6_9776':
        print("")
    
    if response.status_code == 200:
        json_obj = json.loads(response.text)

        year = ""
        month = "unknownMonth"
        title = json_obj.get("title", "")

        published = json_obj.get("published", "")

        if published:
            published_date_parts = published["date-parts"]

            year = published_date_parts[0][0]

            if len(published_date_parts[0]) > 1:
                month = published_date_parts[0][1]
        else:
            created = json_obj.get("created", "")

            if created:
                created_date_parts = created["date-parts"]

                year = created_date_parts[0][0]

                if len(created_date_parts[0]) > 1:
                    month = created_date_parts[0][1]
                
        if year and month and title:
            if "reference" in json_obj.keys():
                del json_obj["reference"]
            return {
                "year": str(year),
                "month": str(month),
                "title" : title,
                "journal" : json_obj.get("container-title", ""),
                "volume": json_obj.get("volume", ""),
                "raw_data": json.dumps(json_obj)
            }
        
    return None

def get_pdf_url(doi):
    sci_hub_url = "https://sci-hub.ru/"

    url = sci_hub_url + doi

    try: 
        resp = requests.get(url)

    except Exception as e:   
        print("failed to get pdf url for doi: {} reason: {}".format(doi, type(e)))
        return None    

    textResp = TextResponse(url=url,
                            body=resp.text,
                            encoding='utf-8')
    
    pdf_url = textResp.xpath(
        '//div[@id="buttons"]/button').extract_first()
    
    if pdf_url == None:
        print("failed to get pdf url for following DOI: {}".format(doi))
        return None 
    
    start_keyword = "location.href=\'//"
    start = pdf_url.find(start_keyword)

    if start == -1:
        start_keyword = "location.href='/"
        start = pdf_url.find(start_keyword)

    if start == -1:
        print("unrecognized pdf url: {}".format(pdf_url))
        return None

    end = pdf_url.find('?download=true')

    pdf_url = pdf_url[start + len(start_keyword):end]
    
    if pdf_url.find("tree/") != -1:
        # https://sci-hub.ru/tree/18/f3/18f3842c60c2d2cf87258d5ae129d520.pdf
        pdf_url = sci_hub_url + pdf_url
    elif pdf_url.find("downloads/") != -1:
        # https://sci-hub.ru/downloads/2019-10-26/89/wang2019.pdf
        pdf_url = sci_hub_url + pdf_url
    elif pdf_url.find("uptodate/") != -1:
        # https://sci-hub.ru/uptodate/S1364815221001766.pdf
        pdf_url = sci_hub_url + pdf_url
    else: 
        # https://dacemirror.sci-hub.ru/journal-article/9e324802ef65bfe6ace82a3b90b2045f/chappin2017.pdf
        pdf_url = "https://" + pdf_url

    return pdf_url

def get_valid_file_name(file_name):
    file_name = file_name.strip()

    file_name = file_name.replace("\\", " ")
    file_name = file_name.replace("/", " ")
    file_name = file_name.replace(":", " ")
    file_name = file_name.replace("?", "")
    file_name = file_name.replace("<", "")
    file_name = file_name.replace(">", "")
    file_name = file_name.replace("|", "")

    file_name = file_name.replace("  ", " ")

    if file_name.isascii():
        return file_name;
  
    new_file_name = ""

    for c in file_name:
        if ord(c) > 127: # no Ascii
            continue

        new_file_name += c

    return new_file_name

def get_pdf_file_info(journal_info):
    global g_output_path

    output_path = "{}/{}".format(g_output_path, journal_info["year"])

    if journal_info["month"]:
        output_path = "{}/{}".format(output_path, journal_info["month"])

    file_name = get_valid_file_name(journal_info["title"])

    file_full_path = output_path + "/" + file_name

    max_length = 250
    
    if len(file_full_path) > max_length:
        length = len(file_name) - (len(file_full_path) - max_length)
        file_name = file_name[0:length]

    file_name = "{}.pdf".format(file_name)

    return {
        "output_path": output_path,
        "file_name": file_name
    }

def get_unique_pdf_file_full_path(pdf_file_full_path):
    if not pdf_file_full_path in g_used_pdf_file_full_path_list:
       return pdf_file_full_path
    
    output_path = os.path.dirname(pdf_file_full_path)
    full_name = os.path.basename(pdf_file_full_path)
    splitted = os.path.splitext(full_name)
    file_name = splitted[0]
    file_name = file_name + "1"
    file_name = file_name + splitted[1]

    return output_path + "/" + file_name

class Worker(threading.Thread):
    def __init__(self, _id):
        threading.Thread.__init__(self)
        self.id = _id
        self.current_downloading = -1

    def run(self):
        # print("Download Worker {} started".format(self.id))

        global g_download_started_dois, g_doi_pattern_list, g_count_of_started

        for doi in g_doi_pattern_list:
            g_thread_lock.acquire()

            if doi not in g_download_started_dois:
                g_download_started_dois.append(doi)
            else:
                g_thread_lock.release()
                continue

            g_count_of_started = g_count_of_started + 1
            print("{}/{} doi:{} thread{}".format(g_count_of_started, len(g_doi_pattern_list), doi, self.id))
            g_thread_lock.release()

            self.get_data(doi)
        
    def get_data(self, doi):
        global g_data

        journal_info = get_journal_info(doi)

        retry = 0

        while not journal_info:
            print("retry({}) getting journal info for doi: {}".format(retry, doi))
            time.sleep(1)
            journal_info = get_journal_info(doi)
            retry += 1

        retry = 0

        pdf_url = get_pdf_url(doi)

        while not pdf_url:
            print("retry({}) getting pdf url for doi: {}".format(retry, doi))
            time.sleep(1)
            pdf_url = get_pdf_url(doi)
            retry += 1

        # if title is empty
        if journal_info["title"] == "":
            file_name = pdf_url.split("?")[0].split("/")[-1]
            journal_info["title"] = file_name.replace(".pdf", "")

        file_info = get_pdf_file_info(journal_info)

        output_path = file_info["output_path"]
        pdf_file_name = file_info["file_name"]
        pdf_file_full_path = output_path + "/" + pdf_file_name

        g_thread_lock.acquire()
        pdf_file_full_path = get_unique_pdf_file_full_path(pdf_file_full_path)
        g_used_pdf_file_full_path_list.append(pdf_file_full_path)
        g_thread_lock.release()

        data_info = {
            "doi": doi,
            "pdf_url": pdf_url,
            "full_path": pdf_file_full_path
        }

        data_info.update(journal_info)

        g_thread_lock.acquire()
        g_data.append(data_info)
        g_thread_lock.release()
    

def main():
    global g_output_path, g_full_doi_list_file_path, g_doi_pattern

    parser = argparse.ArgumentParser()

    parser.add_argument("g_doi_pattern")
    parser.add_argument("g_outputPath")
    parser.add_argument("g_new_doi_list_file_path")
    parser.add_argument("worker_count")

    args = vars(parser.parse_args())

    g_doi_pattern = args["g_doi_pattern"]
    g_output_path = args["g_outputPath"]
    g_new_doi_list_file_path = args["g_new_doi_list_file_path"]
    thread_count = args["worker_count"]

    if not os.path.exists(g_output_path):
        print("{} does not exists".format(g_output_path))
        exit(0)    

    if not os.path.exists(g_full_doi_list_file_path):
        print("{} does not exists".format(g_full_doi_list_file_path))
        exit(0)    

    print("doi pattern: {}".format(g_doi_pattern))
    print("output path: {}".format(g_output_path))

    print("preparing doi pattern list...")

    doi_list_file = open(g_full_doi_list_file_path, 'r', encoding="utf8")
    line = doi_list_file.readline()

    found = 0;
    cur_line = 0;

    while line:
        if not g_doi_pattern in line:
            try: 
                line = doi_list_file.readline()
            except Exception as e:
                print("failed to read line: {}".format(cur_line))

            cur_line += 1;
            continue

        found += 1
        doi = line.strip()

        g_doi_pattern_list.append(doi)

        try: 
            line = doi_list_file.readline()
        except Exception as e:
            print("failed to read line:{}".format(cur_line))

        cur_line += 1;
    
    print("found {} patterns".format(found))

    thread_count = int(thread_count)

    threads = []
    thread_id = 1

    for x in range(thread_count):
        worker = Worker(thread_id)

        worker.start()
        threads.append(worker)
        thread_id += 1

    # Wait for all threads to complete
    for t in threads:
        t.join()

    json_object = json.dumps(g_data, indent=4)

    new_doi_list_file = open(g_new_doi_list_file_path, 'w')
    new_doi_list_file.write(json_object)
    new_doi_list_file.close()

    print("all done")

main()


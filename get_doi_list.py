import argparse
import requests
import json
import os
import time
from scrapy.http import TextResponse

g_doi_pattern = ""
g_output_path = ""

g_full_doi_list_file_path = "sci-hub-doi-2022-02-12.txt"
g_new_doi_list_file_path = "doi-list.json"

def get_journal_info(doi):
    url = "https://www.doi.org/{}".format(doi)

    payload = {}
    headers = {
        'Accept': 'application/x-bibtex; charset=utf-8'
    }

    try: 
        response = requests.request("GET", url, headers=headers, data=payload)

    except Exception as e:   
        print("failed to get journal info for doi: {} reason: {}".format(doi, type(e)))
        return None
    
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
                
        if year and month:
            return {
                "year": year,
                "month": month,
                "title" : title,
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
    else: 
        # https://dacemirror.sci-hub.ru/journal-article/9e324802ef65bfe6ace82a3b90b2045f/chappin2017.pdf
        pdf_url = "https://" + pdf_url

    return pdf_url

def get_pdf_file_info(journal_info):
    global g_output_path

    output_path = "{}/{}".format(g_output_path, journal_info["year"])

    if journal_info["month"]:
        output_path = "{}/{}".format(output_path, journal_info["month"])

    file_name = journal_info["title"];

    file_name = file_name.replace("?", "")
    file_name = file_name.replace(":", " ")
    file_name = file_name.replace("/", " ")
    file_name = file_name.replace("\\", " ")

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

def main():
    global g_output_path, g_full_doi_list_file_path, g_doi_pattern

    parser = argparse.ArgumentParser()

    parser.add_argument("g_doi_pattern")
    parser.add_argument("g_outputPath")
    parser.add_argument("g_new_doi_list_file_path")
    

    args = vars(parser.parse_args())

    g_doi_pattern = args["g_doi_pattern"]
    g_output_path = args["g_outputPath"]
    g_new_doi_list_file_path = args["g_new_doi_list_file_path"]

    if not os.path.exists(g_output_path):
        print("{} does not exists".format(g_output_path))
        exit(0)    

    if not os.path.exists(g_full_doi_list_file_path):
        print("{} does not exists".format(g_full_doi_list_file_path))
        exit(0)    

    print("doi pattern: {}".format(g_doi_pattern))
    print("output path: {}".format(g_output_path))

    data = []

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

        journal_info = get_journal_info(doi)

        retry = 0

        while not journal_info:
            print("retry({}) getting journal info for doi: ".format(retry, doi))
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

        data.append({
            "doi": doi,
            "pdf_url": pdf_url,
            "full_path": pdf_file_full_path
        })

        print("{} doi: {} {} {}".format(found, doi, pdf_url, pdf_file_name))   
              
        try: 
            line = doi_list_file.readline()
        except Exception as e:
            print("failed to read line:{}".format(cur_line))

        cur_line += 1;

    json_object = json.dumps(data, indent=4)

    new_doi_list_file = open(g_new_doi_list_file_path, 'w')
    new_doi_list_file.write(json_object)
    new_doi_list_file.close()

main()



import argparse
import json
import os
import time
import requests
from scrapy.http import TextResponse
from pathlib import Path

g_overwrite = False
g_doi_list_file_path = "";
g_doi_list = []
g_cur_downloading = 0;
    
def main():
    global g_doi_list_file_path, g_cur_downloading

    parser = argparse.ArgumentParser()

    parser.add_argument("g_doi_list_file_path")

    args = vars(parser.parse_args())

    g_doi_list_file_path = args["g_doi_list_file_path"]

    if not os.path.exists(g_doi_list_file_path):
        print("doi list file: {} does not exist!".format(g_doi_list_file_path))
        exit(0)

    f = open(g_doi_list_file_path, 'r')
    g_doi_list = json.load(f)

    g_cur_downloading = 0;

    for info in g_doi_list:
        doi = info["doi"]
        pdf_url = info["pdf_url"]
        pdf_file_full_path = info["full_path"]

        if os.path.exists(pdf_file_full_path):
            if g_overwrite:
                os.remove(pdf_file_full_path)
            else:
                print("{}/{} (doi:{}) already downloaded {} into {}".format(g_cur_downloading, len(g_doi_list), doi, pdf_url, pdf_file_full_path))
                g_cur_downloading = g_cur_downloading + 1
                continue

        p = Path(pdf_file_full_path)
        output_path = p.parent 

        if not os.path.exists(output_path):
            os.makedirs(output_path) 

        print("{}/{} (doi:{}) downloading {} into {}".format(g_cur_downloading, len(g_doi_list), doi, pdf_url, pdf_file_full_path))
        
        success = download_file(pdf_url, pdf_file_full_path)

        retry = 0;

        while success == False:
            print("{}/{} retry({}) downloading {} into {}".format(g_cur_downloading, len(g_doi_list), retry, pdf_url, pdf_file_full_path))
            time.sleep(1)
            success = download_file(pdf_url, pdf_file_full_path)
            retry += 1

        g_cur_downloading = g_cur_downloading + 1

def download_file(url, local_filename):
    global g_cur_downloading, g_doi_list

    try:
        respDownload = requests.get(url)

    except Exception as e:   
        print("{}/{} downloading failed. reason: {}".format(g_cur_downloading, len(g_doi_list), type(e)))
        return False

    if len(respDownload.content) == 0:
        print("{}/{} downloading failed. reason: zero content".format(g_cur_downloading, len(g_doi_list)))
        return False

    if len(respDownload.content) < 1024:
        print("{}/{} downloading failed. reason: too small content".format(g_cur_downloading, len(g_doi_list)))
        return False
    
    f = open(local_filename, "wb")
    f.write(respDownload.content)
    f.close()

    return True
          
main()

print("all done")

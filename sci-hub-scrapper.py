
import argparse
import json
import os
import time
import requests
from scrapy.http import TextResponse
from pathlib import Path
import threading
import subprocess

g_overwrite = False
g_doi_list_file_path = ""
g_doi_list = []
g_count_of_started = 0
g_download_started_dois = []
g_thread_lock = threading.Lock()
    
def main():
    global g_doi_list_file_path, g_count_of_started, g_doi_list

    parser = argparse.ArgumentParser()

    parser.add_argument("g_doi_list_file_path")
    parser.add_argument("worker_count")

    args = vars(parser.parse_args())

    g_doi_list_file_path = args["g_doi_list_file_path"]
    thread_count = args["worker_count"]

    if not os.path.exists(g_doi_list_file_path):
        print("doi list file: {} does not exist!".format(g_doi_list_file_path))
        exit(0)

    f = open(g_doi_list_file_path, 'r')
    g_doi_list = json.load(f)

    g_count_of_started = 1;

    thread_count = int(thread_count)

    threads = []
    thread_id = 1

    for x in range(thread_count):
        worker = DownloadWorker(thread_id)

        worker.start()
        threads.append(worker)
        thread_id += 1

    # Wait for all threads to complete
    for t in threads:
        t.join()

    print("all done")

    return True
          
class DownloadWorker(threading.Thread):
    def __init__(self, _id):
        threading.Thread.__init__(self)
        self.id = _id
        self.current_downloading = -1

    def run(self):
        # print("Download Worker {} started".format(self.id))

        self.download_journals()

    def download_journals(self):
        global g_download_started_dois, g_count_of_started, g_doi_list

        for info in g_doi_list:
            doi = info["doi"]

            g_thread_lock.acquire()

            if doi not in g_download_started_dois:
                g_download_started_dois.append(doi)
            else:
                g_thread_lock.release()
                continue

            g_thread_lock.release()

            self.download_jounal(info)

    def download_jounal(self, info):
        global g_download_started_dois, g_overwrite, g_count_of_started, g_doi_list

        doi = info["doi"]
        pdf_url = info["pdf_url"]
        pdf_file_full_path = info["full_path"]

        if os.path.exists(pdf_file_full_path):
            if g_overwrite:
                os.remove(pdf_file_full_path)
            else:
                g_thread_lock.acquire()
                print("{}/{} doi:{} already downloaded. thread{}".format(g_count_of_started, len(g_doi_list), doi, self.id))
                self.current_downloading = g_count_of_started

                g_count_of_started = g_count_of_started + 1
                g_thread_lock.release()
                return

        p = Path(pdf_file_full_path)
        output_path = p.parent 

        if not os.path.exists(output_path):
            os.makedirs(output_path) 

        g_thread_lock.acquire()
        print("{}/{} doi:{} thread{}".format(g_count_of_started, len(g_doi_list), doi, self.id))
        self.current_downloading = g_count_of_started
        g_count_of_started = g_count_of_started + 1
        g_thread_lock.release()

        success = self.download_file(pdf_url, pdf_file_full_path, doi)

        retry = 0;

        while success == False:
            g_thread_lock.acquire()
            print("{}/{} retry({}) doi:{} thread{}".format(self.current_downloading, len(g_doi_list), retry, doi, self.id))
            g_thread_lock.release()

            time.sleep(1)
            success = self.download_file(pdf_url, pdf_file_full_path, doi)
            retry += 1
   

    def download_file(self, url, local_filename, doi):
        """
        process = subprocess.run(["wget", url, "-O", local_filename],
                       stdout = subprocess.DEVNULL,
                       stderr = subprocess.DEVNULL) 
        """

        process = subprocess.run(["wget", url, "-O", local_filename])
                                
        return_code = process.returncode

        if return_code != 0:
            return False

        if not os.path.exists(local_filename):
            return False
        
        file_size = os.path.getsize(local_filename)

        if file_size == 0:
            print("failed to download from {} into {}. reason zero byte".format(url, local_filename))
            Path.unlink(local_filename)
            return False
    
        if file_size < 1024 * 10:
            print("failed to download from {} into {}. too small size".format(url, local_filename))
            Path.unlink(local_filename)
            return False
        
        return True

main()



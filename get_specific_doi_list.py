import os
import re
import requests
import json
from scrapy.http import TextResponse

search_doi = "10.1016/j.apor"

doi_list = []

doi_list_file = open('sci-hub-doi-2022-02-12.txt', 'r')
line = doi_list_file.readline()
cnt = 1
while line:
    try:
        if search_doi in line:
            doi_list.append(line.strip())
        line = doi_list_file.readline()
    except Exception as e:   
        print("failes file read line {}".format(str(cnt)))
    cnt += 1

print("Completed reading of doi list file")

new_doi_list_file = open('doi-list.txt', 'w')
new_doi_list_file.write("\n".join(doi_list))
new_doi_list_file.close()

print("Done. Please check doi_list.txt")


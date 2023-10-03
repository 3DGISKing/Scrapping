python ./get_doi_list.py "10.1175/JTECH-D" "D:/Sci-hub/" "doi-list.json"
python ./sci-hub-scrapper.py doi-list.json 1
pause
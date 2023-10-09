### Scrapping Sci-hub

#### step1-get doi-list.json

```
python ./get_doi_list.py "10.1016/j.advengsoft" "F:/Sci-hub/Advances in Engineering Software" "doi-list-advengsoft.json" 10

```

#### step2-scrapping

```
python ./sci-hub-scrapper.py doi-list-advengsoft.json 10

```

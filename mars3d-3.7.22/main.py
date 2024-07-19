import os

import json
import urllib.request

# Opening JSON file
f = open('example.json', encoding="utf-8")

# returns JSON object as
# a dictionary
totalExample = json.load(f)

# Iterating through the json
# list

count = 0

output_dir = "D:/examples"

for exampleGroup in totalExample:
    for subExampleGroup in exampleGroup["children"]:
        for example in subExampleGroup["children"]:
            name = example["name"]
            thumnail = example["thumbnail"]
            main_prop = example["main"]

            index_html_url = f"http://mars3d.cn/example/{main_prop}/index.html"
            map_js_url = f"http://mars3d.cn/example/{main_prop}/map.js"

            dir = f"{output_dir}/{main_prop}"

            if not os.path.exists(dir):
                os.makedirs(dir)

            index_html_path = f"{dir}/index.html"
            map_js_path = f"{dir}/map.js"
            thumbnail_url = f"http://cdn.marsgis.cn/mars3d-example/thumbnail/{
                thumnail}"

            thumbnail_path = f"{output_dir}/thumbnail/{thumnail}"

            try:
                if not os.path.exists(index_html_path):
                    urllib.request.urlretrieve(index_html_url, index_html_path)

                if not os.path.exists(map_js_path):
                    urllib.request.urlretrieve(map_js_url, map_js_path)

                if not os.path.exists(thumbnail_path):
                    urllib.request.urlretrieve(
                        thumbnail_url, thumbnail_path)
            except Exception as e:
                print(f"{e}")

            count += 1

            print(f"{count} {name} {thumnail}")

print("done")

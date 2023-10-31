import requests
import os
import xml.dom.minidom as minidom

root_folder = "F:/QGISPlugins"
qgisversion = '2.4' # 3.28

total_count = 0;

def get_plugins():
    global total_count
    """
    Fetch the plugins from plugin repo
    :return: name, url, filename
    """
    plugin_request = requests.get("http://plugins.qgis.org/plugins/plugins.xml?qgis={}".format(qgisversion))
    xml = minidom.parseString(plugin_request.text)
    plugins = xml.getElementsByTagName("pyqgis_plugin")
    total_count = len(plugins)

    for plugin in plugins:
        name = plugin.attributes["name"].value
        url = plugin.getElementsByTagName("download_url")[0].childNodes[0].data
        filename = plugin.getElementsByTagName("file_name")[0].childNodes[0].data
        yield name, url, filename

downloaded = 0;

for name, url, filename in get_plugins():
    print("downloading {}/{}...".format(downloaded, total_count))

    full_file_name = os.path.join(root_folder, qgisversion, filename);

    if os.path.exists(full_file_name):
        downloaded += 1
        continue

    try:
        respDownload = requests.get(url)

    except Exception as e:   
        print(type(e))
        downloaded += 1
        continue
    
    path = os.path.join(root_folder, qgisversion);    

    if not os.path.exists(path):
        os.makedirs(path)

    f = open(full_file_name, "wb")
    f.write(respDownload.content)
    f.close()

    downloaded += 1


    
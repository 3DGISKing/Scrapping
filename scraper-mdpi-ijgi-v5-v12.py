import os
import re
import requests
from scrapy.http import TextResponse

g_outputPath = "G:\\MDPI-IJGI"
g_downloadFailed = []

def unique(list):
 
    # initialize a null list
    unique_list = []
 
    # traverse for all elements
    for x in list:
        # check if exists in unique_list or not
        if x not in unique_list:
            unique_list.append(x)
    
    return unique_list

def main():
    global g_outputPath;

    yearUrls = []

    for i in range(5, 13):
        yearUrls.append("https://www.mdpi.com/2220-9964/" + str(i))
        
    for urlIndex, url in enumerate(yearUrls):
        print("{}. Reading volume {}".format(str(urlIndex + 1), url))

        respVols = requests.get(url)
        textResp = TextResponse(url=url,
                                body=respVols.text,
                                encoding='utf-8')
        volumeUrls = textResp.xpath(
            '//div[@id="middle-column"]//div[@class="issue-cover"]/div/a/@href').extract()
        
        volumeUrls = unique(volumeUrls)

        for volumeIndex, volumeUrl in enumerate(volumeUrls):
            print("\t{}. Reading issue {}".format(str(volumeIndex + 1), volumeUrl))

            respArticles = requests.get("https://www.mdpi.com{}".format(volumeUrl))
            textResp = TextResponse(url=volumeUrl,
                                    body=respArticles.text,
                                    encoding='utf-8')
            articleUrls = textResp.xpath(
                '//div[@class="article-content"]/a[@class="title-link"]/@href').extract()

            for articleIndex, articleUrl in enumerate(articleUrls):
                respArticleContent = requests.get(
                    "https://www.mdpi.com{}".format(articleUrl))
                textResp = TextResponse(url=articleUrl,
                                        body=respArticleContent.text,
                                        encoding='utf-8')
                downloadUrl = textResp.xpath(
                    '//div[contains(@id, "drop-download-")]/a/@href').extract_first()
                
                breadcrumbs = textResp.xpath(
                    '//div[@class="breadcrumb__element"]/a/text()').extract()
                
                volume = breadcrumbs[2];
                issue = breadcrumbs[3];

                volume = volume.replace(" ", "");
                issue = issue.replace(" ", "");

                title = textResp.xpath("//h1[@class='title hypothesis_container']/text()").extract_first();

                title = title.strip()

                print("\t\t{}. Reading article {} {}".format(str(articleIndex + 1), articleUrl, title))
            
                # remove special characters
                title = re.sub('[^a-zA-Z0-9 \n\.]', '', title)
                title = title.replace(" ", "_");
                                            
                path = os.path.join(g_outputPath, volume, issue);

                if not os.path.exists(path):
                    os.makedirs(path)

                try:
                    respDownload = requests.get("https://www.mdpi.com{}".format(downloadUrl))

                except Exception as e:   
                    # tuple
                    g_downloadFailed.append((downloadUrl, path, title)) 
                    print(type(e))
                    continue
                
                fileName = respDownload.url.split("?")[0].split("/")[-1]

                fileName = os.path.join(path, title + "-" + fileName);

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
        downloadUrl = failed[0]
        path = failed[1]
        title = failed[2]

        print("{}/{} Retrying downloading {}".format(retry_count, len(g_downloadFailed), title))

        try:
            respDownload = requests.get("https://www.mdpi.com{}".format(downloadUrl))

        except Exception as e:   
            # tuple
            g_downloadFailed.append((downloadUrl, path, title)) 
            print(type(e))
            ++retry_count
            continue
            
        fileName = respDownload.url.split("?")[0].split("/")[-1]
        fileName = os.path.join(path, title + "-" + fileName);

        f = open(fileName, "wb")
        f.write(respDownload.content)
        f.close()

        ++retry_count

    if len(new_failed) > 0:
        g_downloadFailed = new_failed
        retry_failed_to_download()

main()

# g_downloadFailed.append(('/2220-9964/11/1/71/pdf?version=1642475471', 'G:\\MDPI-IJGI\\Volume11\\Issue1', 'Indoor_Positioning_Algorithm_Based_on_Reconstructed_Observation_Model_and_Particle_Filter'))

retry_failed_to_download()

print("all done")

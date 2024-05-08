"""Module"""

import requests
from scrapy.http import TextResponse


def decode_email_protection(encoded_string):
    """Function"""
    encoded_data = encoded_string.split("#")[-1]

    r = int(encoded_data[:2], 16)
    email = "".join(
        [
            chr(int(encoded_data[i : i + 2], 16) ^ r)
            for i in range(2, len(encoded_data), 2)
        ]
    )

    encoded_data = email.split("#")[-1]

    r = int(encoded_data[4:6], 16)
    encoded_data = encoded_data[:4] + encoded_data[6:]

    email = "".join(
        [
            chr(int(encoded_data[i : i + 2], 16) ^ r)
            for i in range(0, len(encoded_data), 2)
        ]
    )

    return email


URL = "https://www.mdpi.com/2220-9964/7/3/102"

respVols = requests.get(URL, timeout=5)
textResp = TextResponse(url=URL, body=respVols.text, encoding="utf-8")

email_href_list = textResp.xpath("//a[contains(@class,'email')]/@href")

for i, email_href in enumerate(email_href_list):
    EMAIL = decode_email_protection(email_href_list[i].root)
    print(EMAIL)

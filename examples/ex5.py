#!/usr/bin/python3
# -*-coding:utf8-*-

from aiospider import Spider

import re
import os
import os.path
import urllib.parse
from bs4 import BeautifulSoup

import aiohttp

BASE_URL = "http://www.allitebooks.in/page/{page}/"


def confirm_dir(base, *path):
    """
    ??? why not use exists ???

    create folder for one category if not exist
    """
    ph = os.path.join(base, *path)
    try:
        os.makedirs(ph)
    except FileExistsError:
        pass
    return ph


with Spider() as ss:
    swd = confirm_dir(os.path.abspath(os.path.dirname(__file__)), "ebooks")


    async def parse_ebook_detail(response: aiohttp.ClientResponse):
        content = await response.text()
        downloadTargets = re.findall(string=content, pattern=".*<a href=\"(.*pdf|.*epub)\">.*")
        for download in downloadTargets:
            name = os.path.basename(download)
            # print(os.path.join(swd, urllib.parse.unquote_plus(name)))
            ss.add_download(download, os.path.join(swd, urllib.parse.unquote_plus(name)))


    async def parse_ebook_list(response: aiohttp.ClientResponse):
        content = await response.text()
        bs = BeautifulSoup(content, "lxml")
        bookList = bs.find_all("a", {"rel": "bookmark"})

        for book in bookList:
            ss.add_request(book.get("href"), parse_ebook_detail)


    ss.start([BASE_URL.format(page=i) for i in range(1, 2)], [parse_ebook_list] * 1)

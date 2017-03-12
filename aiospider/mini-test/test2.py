#!/usr/bin/python3
#-*-coding:utf8-*-

'''
Emoji, I'm coming.
This project get emoji from [face.ersansan.cn]. Each category has one dictionary to hold its all pictures.
'''
import aiohttp
from aiospider import Spider
import os
from os.path import splitext, basename, exists, isdir, join

BASE_URL = "http://face.ersansan.cn/collection/{tid}?r_from=miniapp"


def confirmDir(path):
    '''
    ??? why not use exists ???
    '''
    try:
        os.mkdir(path)
    except FileExistsError:
        pass


with Spider() as ss:
    async def parse_category(response: aiohttp.Response):
        #print("url : {url}, status: {status}".format(url=response.url,status=response.status))
        js = await response.json()
        if not js.get("Count", 0):
            return
        category = js.get("title", "")
        if not category:
            return
        ss.log(str(js.get("Count", 0)), response.url)
        confirmDir(category)
        for pic in js.get("picList", []):
            src = pic.get("link", "")
            eid = pic.get("eid", "")
            if not src:
                continue
            name = str(eid) + splitext(src)[1] if eid else basename(src)
            dst = join(os.curdir, category, name)
            # print(dst)
            await ss.download(src, dst)

    ss.start([BASE_URL.format(tid=i)
              for i in range(0, 240)], [parse_category, ])

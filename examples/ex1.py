#!/usr/bin/python3
#-*-coding:utf8-*-

'''
Emoji, I'm coming.
This project get emoji from [face.ersansan.cn]. Each category has one dictionary to hold its all pictures.

This example will show you how download files with spider.
'''
import aiohttp
from aiospider import Spider
import os
from os.path import splitext, basename, exists, isdir, join

BASE_URL = "http://face.ersansan.cn/collection/{tid}?r_from=miniapp"


def confirmDir(path):
    '''
    ??? why not use exists ???

    create folder for one category if not exist
    '''
    try:
        os.mkdir(path)
    except FileExistsError:
        pass


with Spider() as ss:
    async def parse_category(response: aiohttp.Response):
        '''
        response can be parsed to a json-object.
        The field `Count` stands for how many emojis this category have.
        The field `title` is the name of this category.
        '''
        js = await response.json()
        if not js.get("Count", 0):
            return
        category = js.get("title", "")
        if not category:
            return
        ss.log(str(js.get("Count", 0)), response.url)
        confirmDir(category)
        # emojis contained by `picList`
        for pic in js.get("picList", []):
            src = pic.get("link", "")  # emoji's download link
            eid = pic.get("eid", "")  # emoji's id
            if not src:
                continue
            # name for saving
            name = str(eid) + splitext(src)[1] if eid else basename(src)
            dst = join(os.curdir, category, name)
            await ss.download(src, dst)

    ss.start([BASE_URL.format(tid=i)
              for i in range(0, 240)], [parse_category, ])

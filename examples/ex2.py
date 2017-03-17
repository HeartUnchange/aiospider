#!/usr/bin/python3
#-*- coding:utf-8 -*-
#import os
#os.environ['PYTHONASYNCIODEBUG'] = '1'
'''
This example will show you how to add targets while crawling.
'''
from aiospider import Spider
from urllib.parse import urljoin

from pyquery import PyQuery

import os
from os.path import splitext, basename, exists, isdir, join


def url_resolve(_from, to):
    return urljoin(_from, to)


def confirmDir(base, *path):
    '''
    ??? why not use exists ???

    create folder for one category if not exist
    '''
    ph = join(base, *path)
    try:
        os.makedirs(ph)
    except FileExistsError:
        pass
    return ph


with Spider() as ss:
    async def parse_page(response):
        url = response.url
        pq = PyQuery(await response.text())
        _class = pq("div.ArticleInfos > span.column > a").text()
        _name = pq("body > div.wrap > div.ArticleTitle").text()
        dic = confirmDir(_class, _name)
        src = pq('#ArticleId22 > p > img').attr('src')
        _num = url[url.index("_") + 1:url.rindex(".")] if "_" in url else "1"
        name = _num + splitext(src)[1]
        ss.add_download(src, join(dic, name))
        for p in pq('body > div.wrap > div.tag-page.l.oh > div.NewPages > ul > li > a'):
            element = PyQuery(p)
            nnew = element.attr("href")
            if nnew:
                ss.add_request(url_resolve(response.url, nnew), parse_page)

    async def parse_links(response):
        pq = PyQuery(await response.text())
        for p in pq('body > div.wrap > div.TypeList > ul > li > a'):
            element = PyQuery(p)
            nnew = element.attr("href")
            if nnew:
                ss.add_request(url_resolve(response.url, nnew), parse_page)

        for p in pq('body > div.wrap > div.NewPages > ul > li > a'):
            element = PyQuery(p)
            nnew = element.attr("href")
            if nnew:
                ss.add_request(url_resolve(response.url, nnew), parse_links)

    ss.start(['https://www.umei.cc/meinvtupian/', ], [parse_links, ])

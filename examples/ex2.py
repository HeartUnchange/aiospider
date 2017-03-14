#!/usr/bin/python3
#-*- coding:utf-8 -*-
#import os
#os.environ['PYTHONASYNCIODEBUG'] = '1'

from aiospider import Spider
from urllib.parse import urljoin

from pyquery import PyQuery

from os.path import splitext, basename


def url_resolve(_from, to):
    return urljoin(_from, to)


with Spider() as ss:
    async def parse_page(response):
        pq = PyQuery(await response.text())
        img = pq('#ArticleId22 > p > img')
        src = img.attr('src')
        name = img.attr('alt')
        await ss.download(src, name + splitext(src)[1])
        for p in pq('body > div.wrap > div.tag-page.l.oh > div.NewPages > ul > li'):
            element = PyQuery(p)
            ss.add_request(url_resolve(
                response.url, element.attr("href")), parse_page)

    async def parse_links(response):
        pq = PyQuery(await response.text())
        for p in pq('body > div.wrap > div.TypeList > ul > li > a'):
            element = PyQuery(p)
            print(element.attr("href"))
            ss.add_request(url_resolve(
                response.url, element.attr("href")), parse_page)

        for p in pq('body > div.wrap > div.NewPages > ul > li > a'):
            element = PyQuery(p)
            print(element.attr("href"))
            ss.add_request(url_resolve(
                response.url, element.attr("href")), parse_links)

    ss.start(['https://www.umei.cc/meinvtupian/', ], [parse_links, ])

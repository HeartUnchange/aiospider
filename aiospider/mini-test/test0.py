#!/usr/bin/python3
#-*-coding:utf8-*-

from aiospider import Spider
with Spider() as ss:
    async def parse_page(response):
        '''
        callback
        The response is just an aiohttp.ClientResponse object now.
        '''
        print("request url is %s, response status is %d"%(response.url,response.status))
    ss.start('https://www.python.org/',parse_page)
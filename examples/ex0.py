#!/usr/bin/python3
#-*-coding:utf8-*-

'''
This is a simple usage of sipder.
'''

from aiospider import Spider
with Spider() as ss:
    def parse_page_1(response):
        '''
        callback
        The response is just an aiohttp.ClientResponse object now.
        The callback will be called when the response is available.
        If callback is not a coroutine function, it will be called by loop.call_soon_threadsafe.
        '''
        print("request url is %s, response status is %d" %
              (response.url, response.status))
    async def parse_page_2(response):
        '''
        callback function also support coroutine function.
        '''
        print("request url is %s, response status is %d" %
              (response.url, response.status))
    ss.start(['https://www.python.org/',"https://github.com/" ], [parse_page_1, parse_page_2])

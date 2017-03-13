#!/usr/bin/python3
#-*- coding:utf-8 -*-
'''
main part
'''
import asyncio
import logging
import sys
from itertools import zip_longest
from collections import namedtuple

import aiohttp

DEFAULT_HEADER = {'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36',
                        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
                        }


_Request = namedtuple("Request",["method","url","callback","header","data"])
def Request(method, url, callback, header=DEFAULT_HEADER, data=None):
    return _Request(method,url,callback,header,data)

class Spider:
    '''
    spider class
    '''

    default_config = {
        # How many requests can be run in parallel
        "concurrent": 5,
        # How long to wait after each request
        "delay": 0,
        # A stream to where internal logs are sent, optional
        "logs": sys.stdout,
        # Re - visit visited URLs, false by default
        "allowDuplicates": False,
    }

    def __init__(self, **kwargs):
        self.config = Spider.default_config.copy()

        self.config.update(kwargs.get("config", {}))

        self.loop = kwargs.get("loop", None) #if no loop, get one
        if self.loop is None or not isinstance(self.loop, asyncio.BaseEventLoop):
            self.loop = asyncio.get_event_loop()
        '''
        if no session , new one.
        Providing a session is convenient when you spider some that you need to login, you can just pass a logged-in session.
        Of course, you can provide a function which will be call before all spider requests to log in.
        '''
        self.session = kwargs.get("session", None)
        if self.session is None or not isinstance(self.session, aiohttp.ClientSession):
            self.session = aiohttp.ClientSession(loop=self.loop)

        '''
         The methods contained here will be called before any requests.
         For example,if spider need to login, you may need provide login method.
        '''
        self.before_start_funcs = []
        self.will_continue = True
        '''
         The methods contained here will be called after all requests.
         For example,if spider need to logout, you may need provide logout method.
        '''
        self.after_crawl_funcs = []

        self.logger = logging.getLogger(self.__class__.__name__)
        self.pending = asyncio.Queue()
        self.active = []
        self.visited = set()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.session.closed:
            self.session.close()
        if not self.loop.is_closed():
            self.loop.close()

    def log(self, status, url):
        self.logger.warning(status + " " + url)

    def add_request(self, url, callback, method="GET", **kwargs):
        '''
         Add request wo queue.
        :param url: request's url
        :param callback: which will be called after request finished.
        :param method: request's method
        :param kwargs: additional parameters for request
        :return: None
        '''
        if url in self.visited:
            return
        if not self.config["allowDuplicates"]:
            self.visited.add(url)
        request = Request(method, url, callback)
        self.pending.put_nowait(request)
        self.log("ADD", url)

    def before_start(self,func):
        '''
        add function called b
        :param func:
        :return:
        '''
        self.before_start_funcs.append(func)
        return func
    def after_spider(self,func):
        self.after_crawl_funcs.append(func)
        return func

    async def try_trigger_before_start_functions(self):
        for func in self.before_start_funcs:
            if callable(func) :
                if asyncio.iscoroutinefunction(func):
                    await func(self)
                else:
                    func(self)
    async def try_trigger_after_crawl_functions(self):
        for func in self.after_crawl_funcs:
            if callable(func) :
                if asyncio.iscoroutinefunction(func):
                    await func(self)
                else:
                    func(self)
    async def load(self):
        '''
         pop request from queue to send
        :return:
        '''
        try:
            while True:
                request = await self.pending.get()
                self.log("Loading", request.url)
                await self.request_with_callback(request)
                self.pending.task_done()
        except asyncio.CancelledError:
            pass

    async def request_with_callback(self, request: _Request):
        async with self.session.request(request.method, request.url) as resp:
            if callable(request.callback) and asyncio.iscoroutinefunction(request.callback):
                # loop.call_later better?
                await request.callback(resp)

    async def download(self, src, dst):
        self.log("DOWNLOADING", src + dst)
        async with self.session.request("get", src) as resp:
            with open(dst, "wb") as fd:
                # while True:
                chunk = await resp.content.read()
                #   if not chunk:
                #       break
                # print(len(chunk))
                fd.write(chunk)

    async def __start(self):
        workers = [asyncio.Task(self.load(), loop=self.loop)
                   for _ in range(self.config["concurrent"])]

        await self.pending.join()
        for w in workers:
            w.cancel()

    def start(self, urls, callbacks):
        for url, callback in zip_longest(urls, callbacks, fillvalue=callbacks[len(callbacks) - 1]):
            self.add_request(url, callback)

        self.loop.run_until_complete(self.try_trigger_before_start_functions())
        if self.will_continue :
            self.loop.run_until_complete(self.__start())
        self.loop.run_until_complete(self.try_trigger_after_crawl_functions())

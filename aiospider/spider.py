#!/usr/bin/python3
#-*- coding:utf-8 -*-
'''
main part
'''
import asyncio

import sys
from itertools import zip_longest
from collections import namedtuple
import traceback

import aiohttp

from .taskqueue import TaskQueue, makeTask
from .log import logging

DEFAULT_HEADER = {'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36',
                  'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
                  }
_Request = namedtuple(
    "Request", ["method", "url", "header", "data", "callback"])


def Request(method, url, header=DEFAULT_HEADER, data=None, callback=None):
    return _Request(method, url, header, data, callback)


class Spider:
    '''
    spider class
    '''
    # Log levels,
    CRITICAL = logging.CRITICAL
    ERROR = logging.ERROR
    WARNING = logging.WARNING
    INFO = logging.INFO
    DEBUG = logging.DEBUG

    default_config = {
        # How many requests can be run in parallel
        "concurrent": 5,
        # How many download requests can be run in parallel
        "download_concurrent": 5,
        # How long to wait after each request
        "delay": 0,
        # A stream to where internal logs are sent, optional
        "logs": sys.stdout,
        # Re - visit visited URLs, false by default
        "allowDuplicates": False,
        #
        "chunk_size": 1024,
    }

    def __init__(self, **kwargs):
        '''
        config default
        '''
        self.config = Spider.default_config.copy()

        self.config.update(kwargs.get("config", {}))

        self.loop = kwargs.get("loop", None)  # if no loop, get one
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
         The variable `will_continue` stands for whether this spider continue or not after all `before_start_funcs` called.
        '''
        self.before_start_funcs = []
        self.will_continue = True
        '''
         The methods contained here will be called after all requests.
         For example,if spider need to logout, you may need provide logout method.
        '''
        self.after_crawl_funcs = []
        '''
        spider's logger
        '''
        self.logger = logging.getLogger(self.__class__.__name__)

        '''
        The reasons that only sipder's download_pending uses TaskQueue are:
         1. TaskQueue is still not stable.
         2. When there are too many request waited to send, it has to keep many contexts for each waiting request 
            including the method request_with_callback. So the request queue still use asyncio.Queue.
        '''
        self.pending = asyncio.Queue()
        # downloading concurrent should not be too large.
        self.download_pending = TaskQueue(
            maxsize=self.config["download_concurrent"])
        self.visited = set()
        # you cannot call method `start` twice.
        self.running = False
        # active tasks
        self.active = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cancel()
        if not self.session.closed:
            self.session.close()
        if not self.loop.is_closed():
            self.loop.stop()
            self.loop.run_forever()
            self.loop.close()

    def _cancel(self):
        for task in self.active:
            task.cancel()

    def log(self, lvl, msg):
        self.logger.log(lvl, msg)

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
        request = Request(method, url, callback=callback)
        self.pending.put_nowait(request)
        self.log(logging.INFO, "Add url: {} to queue.".format(url))

    def add_requests(self, urls, callbacks):
        '''
        add many targets and callback once.
        if targets are more than callbacks, None will be used to fillup.
        if targets are less than callbacks, callbacks will be cut.
        '''
        if isinstance(urls, (list, tuple)) and isinstance(callbacks, (list, tuple)):
            if len(urls) >= len(callbacks):
                pass
            else:
                callbacks = callbacks[:len(urls)]
            for url, callback in zip_longest(urls, callbacks):
                self.add_request(url, callback)
        elif isinstance(urls, str):
            self.add_request(urls, callbacks)

    def before_start(self, func):
        '''
        add function called before start
        :param func:
        :return:
        '''
        self.before_start_funcs.append(func)
        return func

    def after_spider(self, func):
        self.after_crawl_funcs.append(func)
        return func

    async def try_trigger_before_start_functions(self):
        for func in self.before_start_funcs:
            if callable(func):
                if asyncio.iscoroutinefunction(func):
                    await func(self)
                else:
                    func(self)

    async def try_trigger_after_crawl_functions(self):
        for func in self.after_crawl_funcs:
            if callable(func):
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
                self.log(logging.INFO,
                         "Loading url: {} from queue.".format(request.url))
                await self.request_with_callback(request, request.callback)
                self.pending.task_done()
        except asyncio.CancelledError:
            pass

    async def request_with_callback(self, request: _Request, callback=None):
        if not callback:
            callback = request.callback
        if callable(callback):
            try:
                async with self.session.request(request.method, request.url) as resp:
                    '''
                    if callback is a coroutine-function, the await is necessary.
                    if not, call_soon_threadsafe is better.
                    But why not coroutine ?
                    '''
                    if asyncio.iscoroutinefunction(callback):
                        await callback(resp)
                    else:
                        self.loop.call_soon_threadsafe(callback, resp)
                    self.log(logging.INFO, "Request [{method}] `{url}` finishend.(There are still {num})".format(
                        method=request.method, url=request.url, num=self.pending.qsize()))
            except Exception as e:
                self.log(logging.ERROR, "Error happened in request [{method}] `{url}`, Request is ignored.\n{error}".format(
                    error=traceback.format_exc(), url=request.url, method=request.method))
        else:
            self.log(logging.WARNING, "Callback for request [{method}] `{url}` is not callable. Request is ignored.".format(
                url=request.url, method=request.method))

    async def download(self, src, dst):
        '''
        async def save(resp, dst=dst):
            with open(dst, "wb") as fd:
                while True:
                    chunk = await resp.content.read()
                    if not chunk:
                        break
                    fd.write(chunk)
            self.log(logging.INFO, "Target `{src}` download to {dst}".format(src=resp.url, dst=dst))
        '''
        #self.log(logging.INFO, "Add download task : {src}".format(src=src))
        # await self.download_pending.put(makeTask(self.request_with_callback,
        # Request("GET", src, callback=save)))
        """
        Unfortunately, TaskQueue doesn't work well when there too many download tasks.
        So raw request may be better.
        """
        self.add_download(src, dst)
        # await self.request_with_callback(Request("GET", src, callback=save))

    def add_download(self, src, dst):
        '''
        add download task in  a synchronous way.
        '''
        async def save(resp, dst=dst):
            with open(dst, "wb") as fd:
                while True:
                    chunk = await resp.content.read(self.config["chunk_size"])
                    if not chunk:
                        break
                    fd.write(chunk)
            self.log(logging.INFO, "Target `{src}` download to {dst}".format(
                src=resp.url, dst=dst))
        self.log(logging.INFO, "Add download task : {src}".format(src=src))
        self.download_pending.add_task(
            makeTask(self.request_with_callback, Request("GET", src, callback=save)))

    async def __start(self):
        for _ in range(self.config["concurrent"]):
            self.active.append(asyncio.ensure_future(
                self.load(), loop=self.loop))
        self.log(
            logging.INFO, "Spider has been started. Waiting for all requests and download tasks to finish.")
        await self.pending.join()
        self.log(logging.INFO, "Requests have finished. Waiting for download task.")
        await self.download_pending.join()

    def start(self, urls, callbacks):
        if self.running:
            self.log("Warning", "Spider is running now.")
            return
        self.running = True

        self.add_requests(urls, callbacks)
        self.loop.run_until_complete(self.try_trigger_before_start_functions())
        # before_start_functions can change will_continue vaule.
        if self.will_continue:
            self.log(logging.INFO, "Spider Start.")
            self.loop.run_until_complete(self.__start())
        else:
            self.log(logging.WARN,
                     "Spider canceled by the last `before_start_function`.")
        self.running = False
        self.log(logging.INFO, "All tasks done.Spider starts to shutdown.")
        self.loop.run_until_complete(self.try_trigger_after_crawl_functions())
        self.log(logging.INFO, "Spider shutdown.")

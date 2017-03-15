#!/usr/bin/python3
#-*-coding:utf8-*-

'''
This example will show you how to use `before_start` to login.
To run this example  you need a Zhihu account.
'''

import aiohttp
from aiospider import Spider
from functools import partial
from pyquery import PyQuery

ZHIHU_INDEX = "https://www.zhihu.com/"
ZHIHU_LOGIN = "https://www.zhihu.com/login/email"

with Spider() as ss:
    @ss.before_start
    async def login(spider):
        # not suitable, will changed later
        async with spider.session.request("get", ZHIHU_INDEX) as resp:
            pq = PyQuery(await resp.text())
            _xsrf = PyQuery(pq('input[type="hidden"][name="_xsrf"]')[
                            0]).attr("value")
        password = ""
        email = ""
        async with spider.session.request("POST", ZHIHU_LOGIN, data={"email": email, "password": password, "_xsrf": _xsrf}) as resp:
            js = await resp.json()
            if not js.get("r", 1):
                print(js.get("msg", ""))
            else:
                spider.will_continue = False
                print(js.get("msg", ""))

    async def logged(response: aiohttp.Response):
        print(response.url)
    ss.start(["https://www.zhihu.com/people/edit", ], [logged, ])

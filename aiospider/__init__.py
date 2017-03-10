#!/usr/bin/python3
#-*- coding:utf-8 -*-

'''
By reference to the node-spider module ,I write this "aio-spider".
aiohttp(client) for requests and pyquery for parsing.
'''
import os
os.environ['PYTHONASYNCIODEBUG'] = '1'

from  .spider import *

__all__ = ["Spider"]

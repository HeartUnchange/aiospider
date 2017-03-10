#AioSpider

This is a little toy I write when I learn python's asynchron.
By reference to the nodejs package [node-spider](https://github.com/flesler/node-spider), I write this "aiospider".Their apis are similar.

But because of the difference between python and javascript, I can't convert `splice` to `remove` simplily when I want to control the maximum of tasks.
Fortunately I found this [crawler-demo](https://github.com/aosabook/500lines/tree/master/crawler). It just uses a list of which length exactly is the maximum concurrent number.

##Usage:
```python
from aiospider import Spider
with Spider() as ss:
    async def parse_page(response):
        '''
        callback
        The response is just an aiohttp.ClientResponse object now.
        '''
        print(responde.status)
    ss.start('https://www.python.org/',parse_links)
```
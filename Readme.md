#AioSpider

This is a little toy I write when I learn python's asynchron.<br>
By reference to the nodejs package [node-spider](https://github.com/flesler/node-spider), I write this "aiospider".They have similar apis.

But because of the difference between python and javascript, I can't convert `splice` to `remove` simplily when I want to control the maximum of tasks.

Fortunately I found this [crawler-demo](https://github.com/aosabook/500lines/tree/master/crawler). It just uses a list of which length exactly is the maximum concurrent number. Just look like this:
```python
workers = [asyncio.Task(self.work(), loop=self.loop) for _ in range(self.max_tasks)]
await self.q.join()
for w in workers:
    w.cancel()
```

##Usage:
```
    python3 setup.py install
    pip install -r requirements.txt
```
##Example:
```python
from aiospider import Spider
with Spider() as ss:
    async def parse_page(response):
        '''
        callback
        The response is just an aiohttp.ClientResponse object now.
        '''
        print("request url is %s, response status is %d"%(response.url,response.status))
    ss.start('https://www.python.org/',parse_page)
'''
my result : request url is https://www.python.org/, response status is 200
'''
```
import asyncio
import logging
import os.path as stdpath

import aiohttp
from aiospider.storage import SqliteStorage
from aiospider.task import TaskQueue

from allitebooks import BookDownloader, BookPageRunner, PageRunner, PageTask

logging.basicConfig(level=logging.INFO)


class ALLITBook:

    http_client = None

    def __init__(self, root_dir="./", m_c=1, c_c=1, i_c=5):
        self.loop = asyncio.get_event_loop()

        self.http_client = aiohttp.ClientSession(loop=self.loop)

        self.storage = SqliteStorage()
        self.queue = TaskQueue(self.storage)

        # 图片存储的根目录
        self.root_dir = stdpath.abspath(root_dir)
        # 主页面并发数
        self.m_c = m_c
        # 内容页面并发数
        self.c_c = c_c
        # 图片下载并发数
        self.i_c = i_c

        self.runners = []

    def cancel(self):

        for t in self.runners:
            t.stop()

        if self.http_client and not self.http_client.closed:
            self.loop.run_until_complete(self.http_client.close())
        if not self.loop.is_closed():
            self.loop.stop()
            self.loop.run_forever()
            self.loop.close()

    def run(self, entrypoint):
        try:
            self.loop.run_until_complete(self.main(entrypoint))
        except Exception as e:
            logging.exception("spider get error")
        finally:
            self.cancel()

    async def main(self, entrypoint):

        await self.queue.submit_task(PageTask.build(entrypoint))

        for i in range(self.m_c):
            mr = PageRunner(self.http_client, self.queue)
            mr.start()
            self.runners.append(mr)
        for i in range(self.c_c):
            cr = BookPageRunner(self.http_client, self.queue)
            cr.start()
            self.runners.append(cr)
        for i in range(self.i_c):
            ir = BookDownloader(self.root_dir, self.http_client, self.queue)
            ir.start()
            self.runners.append(ir)

        await self.queue.finished()


if __name__ == '__main__':
    books = ALLITBook(root_dir="./book")
    books.run("http://www.allitebooks.in/")

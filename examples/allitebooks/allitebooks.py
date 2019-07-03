import asyncio
import hashlib
import logging
import os
import os.path as stdpath
import re
from urllib.parse import unquote, urljoin

import aiohttp
from aiospider.base import Task
from aiospider.task import Consumer, TaskQueue
from bs4 import BeautifulSoup

DEFAULT_HEADER = {'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36',
                  'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
                  }


class ALLITTask(Task):
    def generate_id(self):
        return hashlib.md5(self.get_content("target", "").encode()).hexdigest()


class PageTask(ALLITTask):
    task_type = 1
    content = {"target": ""}

    @staticmethod
    def build(target=""):
        pt = PageTask()
        pt.set_content("target", target)
        return pt


class BookPageTask(ALLITTask):
    task_type = 2
    content = {"target": ""}

    @staticmethod
    def build(target=""):
        pt = BookPageTask()
        pt.set_content("target", target)
        return pt


class BookDownloadTask(ALLITTask):
    task_type = 3
    content = {"target": "", "book_type": "", "category": "", "tags": []}

    @staticmethod
    def build(target="", book_type="", category="", tags=None):
        bdt = BookDownloadTask()
        bdt.set_content("target", target)
        bdt.set_content("book_type", book_type)
        bdt.set_content("category", category)
        bdt.set_content("tags", tags if tags else [])
        return bdt


class Runner(Consumer):
    def __init__(self, client: aiohttp.ClientSession, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = client

    def setup(self):
        self.client._default_headers.update(DEFAULT_HEADER)


class BookDownloader(Runner):

    CHUNK_SIZE = 1024*512

    def __init__(self, root_dir, *args, **kwargs):
        self.root_dir = root_dir
        super().__init__(*args, **kwargs)

        os.makedirs(self.root_dir, exist_ok=True)

    async def run(self):
        task = await self._queue.get_task(BookDownloadTask.task_type)
        if not task:
            logging.warn("book-runner get none")
            return

        target = task.get_content("target", None)
        if not target or not target.startswith("http"):
            return await self._queue.task_done(task.task_id)

        logging.info("start download book %s" % target)
        basename = unquote(stdpath.basename(target))
        filename = stdpath.join(self.root_dir, basename)

        async with self.client.get(target) as resp:
            assert resp.status == 200
            with open(filename, "wb") as fd:
                while True:
                    chunk = await resp.content.read(BookDownloader.CHUNK_SIZE)
                    if not chunk:
                        break
                    fd.write(chunk)
            await self._queue.task_done(task.task_id)


class BookPageRunner(Runner):

    PATTERN = re.compile(
        ".*<a href=\"(.*)\"><span.*>(Download PDF|Download ePub)</span>.*")

    async def run(self):
        task = await self._queue.get_task(BookPageTask.task_type)
        if not task:
            logging.warn("book-page-runner get none")
            return
        target = task.get_content("target", None)
        if not target or not target.startswith("http"):
            return await self._queue.task_done(task.task_id)
        logging.info("start crawl book page %s" % target)
        async with self.client.get(target) as resp:
            assert resp.status == 200
            _content = await resp.text()
            bs = BeautifulSoup(_content, features="lxml")

            category = bs.select_one(".entry-category > a").text
            ts = bs.select(".td-tags > li")
            tags = [t.text for t in ts if t.text != 'TAGS']

            for download, _format in BookPageRunner.PATTERN.findall(_content):
                if _format == "Download PDF":
                    await self._queue.submit_task(BookDownloadTask.build(download, "pdf", category, tags))
                elif _format == "Download ePub":
                    await self._queue.submit_task(BookDownloadTask.build(download, "epub", category, tags))
            await self._queue.task_done(task.task_id)


class PageRunner(Runner):

    async def run(self):
        task = await self._queue.get_task(PageTask.task_type)
        if not task:
            logging.warn("page-runner get none")
            return
        target = task.get_content("target", None)
        if not target or not target.startswith("http"):
            return await self._queue.task_done(task.task_id)

        logging.info("start crawl page %s" % target)
        async with self.client.get(target) as resp:
            assert resp.status == 200
            _content = await resp.text()
            bs = BeautifulSoup(_content, features="lxml")

            book_pages = bs.select("h3.entry-title > a")
            for bps in book_pages:
                bps_href = bps.get('href')
                if not bps_href:
                    continue
                await self._queue.submit_task(BookPageTask.build(bps_href))
            pages = bs.select("div.page-nav > a.page")
            for p in pages:
                p_href = p.get("href")
                if not p_href:
                    continue
                await self._queue.submit_task(PageTask.build(p_href))
            await self._queue.task_done(task.task_id)

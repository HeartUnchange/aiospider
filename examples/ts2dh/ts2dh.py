import hashlib
import logging
import os
import os.path as stdpath
from urllib.parse import urljoin
import asyncio

import aiohttp
from bs4 import BeautifulSoup

from aiospider.base import Task
from aiospider.task import Consumer, TaskQueue


class TS2DHTask(Task):
    def generate_id(self):
        return hashlib.md5(self.get_content("target", "").encode()).hexdigest()

class PageTask(TS2DHTask):
    task_type = 1
    content = {"target": ""}

    @staticmethod
    def build(target=""):
        pt = PageTask()
        pt.set_content("target", target)
        return pt

class ContentTask(TS2DHTask):
    task_type = 2
    content = {"target": "", "folder_name": "", "tags": []}

    @staticmethod
    def build(target="", folder_name="", tags=None):
        ct = ContentTask()
        ct.set_content("target", target)
        ct.set_content("folder_name", folder_name)
        ct.set_content("tags", tags if tags else [])
        return ct

class DownloadTask(TS2DHTask):
    task_type = 3
    content = {"target": "", "folder_name": ""}

    @staticmethod
    def build(target="", folder_name=""):
        dt = DownloadTask()
        dt.set_content("target", target)
        dt.set_content("folder_name", folder_name)
        return dt

class Runner(Consumer):
    def __init__(self, client: aiohttp.ClientSession, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = client

class ImageDownloader(Runner):

    CHUNK_SIZE = 1024*512

    async def run(self):
        task = await self._queue.get_task(DownloadTask.task_type)
        if not task:
            logging.warn("image get none")
            return
        base_dir = task.get_content("folder_name", "./")
        target = task.get_content("target", None)

        if not target or not target.startswith("http"):
            return await self._queue.task_done(task.task_id)

        logging.info("start download image %s to %s" % (target, base_dir))
        basename = stdpath.basename(target)
        filename = stdpath.join(base_dir, basename)

        async with self.client.get(target) as resp:
            assert resp.status == 200
            with open(filename, "wb") as fd:
                while True:
                    chunk = await resp.content.read(ImageDownloader.CHUNK_SIZE)
                    if not chunk:
                        break
                    fd.write(chunk)
            await self._queue.task_done(task.task_id)

class ContentPageRunner(Runner):

    async def run(self):
        task = await self._queue.get_task(ContentTask.task_type)
        if not task:
            logging.warn("cp get none")
            return
        folder_name = task.get_content("folder_name", "./")
        target = task.get_content("target", None)

        # 为这个页面创建一个文件夹, 存在就忽略
        os.makedirs(folder_name, exist_ok=True)
        logging.info("start crawl content page %s" % target)

        async with self.client.get(target) as resp:
            assert resp.status == 200
            _content = await resp.read()
            bs = BeautifulSoup(_content.decode("gb2312", "ignore"), features="lxml")

            image_hrefs = bs.select(".article-content > p > img")
            for _i in image_hrefs:
                _t = _i.attrs.get("src")
                if not _t:
                    continue
                # 添加下载任务
                await self._queue.submit_task(DownloadTask.build(_t, folder_name))

            pages_hrefs = bs.select(".pagination > ul > li > a")
            for _p in pages_hrefs:
                _num = _p.attrs.get('href')
                if not _num:
                    continue
                await self._queue.submit_task(ContentTask.build(urljoin(target, _num), folder_name))
            await self._queue.task_done(task.task_id)

class MainPageRunner(Runner):
    def __init__(self, root_dir, root_url: str, *args, **kwargs):
        # 网站的根路径, 为某些场合的url拼接用
        self.root_url = root_url
        self.root_dir = root_dir
        super().__init__(*args, **kwargs)

    async def run(self):
        task = await self._queue.get_task(PageTask.task_type)
        if not task:
            logging.warn("mp get none")
            return
        target = task.get_content("target", None)

        logging.info("start crawl main page %s" % target)
        async with self.client.get(target) as resp:
            assert resp.status == 200
            logging.debug("main page %s fetched" % target)
            _content = await resp.read()
            bs = BeautifulSoup(_content.decode("gb2312", "ignore"), features="lxml")

            articles = bs.select("article.excerpt")
            for _article in articles:
                article_href = _article.select_one("header > h2 > a")
                _tags = _article.select("p > span > a")
                tags = [_t.text for _t in _tags]
                name = article_href.attrs.get("title")
                href = article_href.attrs.get("href")
                if not href:
                    continue
                # 添加内容页面任务
                await self._queue.submit_task(
                    ContentTask.build(urljoin(self.root_url, href), stdpath.join(self.root_dir, name), tags)
                )

            pages_hrefs = bs.select(".pagination > ul > li > a")
            for _p in pages_hrefs:
                _sub = _p.attrs.get('href')
                if not _sub:
                    continue
                logging.debug("add new main page task%s" % urljoin(target, _sub))
                await self._queue.submit_task(PageTask.build(urljoin(target, _sub)))
            await self._queue.task_done(task.task_id)

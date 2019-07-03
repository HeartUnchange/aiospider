import asyncio
import json
import time
import uuid


class Task:

    task_type = 0

    task_id = ""

    done = False

    content = {}

    def generate_id(self):
        return uuid.uuid4().hex

    def set_content(self, key, value):
        self.content[key] = value

    def get_content(self, key, default):
        return self.content.get(key, default)

    def encode(self):
        if not self.task_id:
            self.task_id = self.generate_id()
        return {"task_id": self.task_id, "task_type": self.task_type, "content": self.content, "done": self.done}

    @staticmethod
    def decode(o):
        t = Task()
        if isinstance(o, str):
            t.__dict__.update(json.loads(o))
        elif isinstance(o, dict):
            t.__dict__.update(o)
        else:
            raise TypeError
        return t

class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class RWLock:

    def __init__(self, *args, **kargs):

        self.read_count = 0
        self.mutex = asyncio.Semaphore(1)
        self.write_lock = asyncio.Semaphore(1)
        self.read_lock = asyncio.Semaphore(1)

    async def read(self, _callable, *args, **kargs):
        await self.write_lock.acquire()

        await self.mutex.acquire()
        if self.read_count == 0:
            await self.read_lock.acquire()
        self.read_count += 1
        self.mutex.release()

        self.write_lock.release()

        result = _callable()

        await self.mutex.acquire()
        self.read_count -= 1
        if self.read_count == 0:
            self.read_lock.release()
        self.mutex.release()

        return result

    async def write(self, _callable, *args, **kargs):
        await self.write_lock.acquire()
        await self.read_lock.acquire()

        _callable()

        self.read_lock.release()
        self.write_lock.release()

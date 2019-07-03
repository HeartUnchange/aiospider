import asyncio
import collections
import logging
from functools import partial

from .base import RWLock, Singleton, Task
from .storage import SqliteStorage, Storage


class TaskQueue:

    __metaclass__ = Singleton

    def __init__(self, _storate: Storage):

        self._size = 0
        self._loop = asyncio.get_event_loop()
        self._finished = asyncio.Event(loop=self._loop)
        self._finished.set()

        self._getters = {}
        self._putters = {}
        self._type_num = {}

        self._storage = _storate
        self._rwlock = RWLock()

        self.__recover()

    def __recover(self):
        TASK_TYPES = self._storage.recover()
        for _type, _count in TASK_TYPES.items():
            self._type_num[_type] = _count
            self._getters[_type] = collections.deque()
            self._putters[_type] = collections.deque()
        self._size = sum(self._type_num.values())
        if self._size > 0:
            self._finished.clear()

    def _wakeup_next(self, waiters):
        while waiters:
            waiter = waiters.popleft()
            if not waiter.done():
                waiter.set_result(None)
                break

    def empty(self, _type):
        return self._type_num.get(_type, 0) == 0

    async def finished(self):
        if self._size > 0:
            await self._finished.wait()

    def __task_done(self, task_id):
        self._storage.task_done(task_id=task_id)
        self._size -= 1
        logging.debug("still have %d tasks" % self._size)
        if self._size == 0:
            self._finished.set()

    async def task_done(self, task_id):
        await self._rwlock.write(partial(self.__task_done, task_id))

    def __submit_task(self, task: Task):
        self._storage.save_task(task)

        old = self._type_num.get(task.task_type, 0)
        self._type_num[task.task_type] = self._storage.count_task(task_type=task.task_type)
        self._size += (self._type_num[task.task_type]-old)
        if self._size > 0:
            self._finished.clear()
        self._wakeup_next(self._getters.get(task.task_type, None))

    async def submit_task(self, task: Task):
        await self._rwlock.write(partial(self.__submit_task, task))

    def __get_task(self, _type: int):
        if self.empty(_type):
            raise asyncio.QueueEmpty
        task = self._storage.get_task(task_type=_type)
        if not task:
            return None
        self._type_num[_type] -= 1
        return task

    async def get_task(self, _type: int) -> Task:
        while self.empty(_type):
            getter = self._loop.create_future()
            self._getters.setdefault(_type, collections.deque())
            self._getters[_type].append(getter)
            try:
                await getter
            except:
                getter.cancel()  # Just in case getter is not done yet.
                try:
                    # Clean self._getters from canceled getters.
                    self._getters[_type].remove(getter)
                except ValueError:
                    # The getter could be removed from self._getters by a
                    # previous put_nowait call.
                    pass
                if not self.empty(_type) and not getter.cancelled():
                    # We were woken up by put_nowait(), but can't take
                    # the call.  Wake up the next in line.
                    self._wakeup_next(self._getters[_type])
                raise
        return await self._rwlock.read(partial(self.__get_task, _type))


class Consumer:

    _runner = None
    _queue = None

    def __init__(self, queue: TaskQueue, loop=None):
        self._queue = queue
        self.loop = loop if loop else asyncio.get_event_loop()

    def prepare(self):
        pass

    def start(self):
        self.prepare()
        self._runner = self.loop.create_task(self.__start())

    def __call__(self, *args, **kargs):
        return self.start()

    async def __start(self):
        while True:
            try:
                await self.run()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.exception("consumer got error")
                break

    async def run(self):
        raise NotImplementedError

    def stop(self):
        if self._runner:
            self._runner.cancel()

#!/usr/bin/python3
#-*-coding:utf8-*-
'''
This example aims to show the usage of TaskQueue.
TaskQueue can be used Individually.
Actually, you don't need to write any code to control TaskQueue. Spider have done that for user.
'''
import asyncio
from aiospider import TaskQueue, makeTask


def exe(a):
    '''
    task 
    Just print the argument `a` and raise an exception.
    '''
    print("args : " + str(a))
    raise OSError("Hi, I'm an exception~")

loop = asyncio.get_event_loop()
taskqueue = TaskQueue(loop=loop)

async def main(queue, loop=None):
    # task with exception_handle
    await queue.put(makeTask(exe, "haha", exception_handle=lambda e: print("Found an exception.")))
    # add task in a synchronous way without exception_handle, 
    queue.add_task(makeTask(exe, "haha", ))
    await queue.join()

loop.run_until_complete(main(taskqueue))
loop.close()

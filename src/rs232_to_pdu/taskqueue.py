"""
rs232-to-pdu
Copyright (C) 2024 InkBridge Networks (legal@inkbridge.io)

rs232-to-pdu © 2024 by InkBridge is licensed under CC BY-NC 4.0. To view a copy
of this license, visit https://creativecommons.org/licenses/by-nc/4.0/
"""
import asyncio
from asyncio import BaseEventLoop
from typing import Callable


class TaskQueue:
    """
    Class that places commands in a queue and runs them one after another
    """

    def __init__(self, event_loop: BaseEventLoop) -> None:
        # Initializes an priority queue with no size limit
        self.queue = asyncio.PriorityQueue()

        # Initializes the priority counter to 0. To be used when setting
        # priority of new items
        self.__prio_counter = 0

        self.__event_loop = event_loop

    def create_task(self):
        """
        starts the dequeue-ing task on the event loop
        Returns:

        """
        self.__event_loop.create_task(self.__dequeue())

    async def enqueue(self, func: Callable, high_prio: bool = False) -> None:
        """
        Puts an command item into the queue.

        Can set priority to be high or low.
        New high priority items have highest priority (run first)
        New low priority items have lowest priority (run last)

        Args:
            func:
            high_prio (bool): whether the command should be run first or last
        """
        # priority is either positive or negative depending on high/low prio
        priority = -self.__prio_counter if high_prio else self.__prio_counter
        self.__prio_counter += 1

        # puts item into queue
        await self.queue.put((priority, func))

    async def __dequeue(self):
        """
        Gets top priority item from queue and runs the command

        Args:
            event_loop (BaseEventLoop): event loop that is expected to keep
                                        producing commands
        """

        # as long as the event loop is running, we should be expecting new
        # items to be put into the queue
        while self.__event_loop.is_running():
            # retrieve next item from queue and run the command
            # Will not grab next item until the previous command has been
            # completed
            _, func = await self.queue.get()
            await func()

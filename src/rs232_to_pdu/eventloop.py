import asyncio
from typing import Callable

print(type(asyncio.new_event_loop()))

class EventLoop:
    def __init__(self):
        self.event_loop = asyncio.new_event_loop()
        self.event_loop.set_exception_handler(self.__exception_handler)
        self.handlers = {}

    def add_exception_handler(self, error, handler: Callable):
        self.handlers[error] = handler

    def del_exception_handler(self, error):
        del self.handlers[error]

    def __exception_handler(self, loop, context):
        for error, handler in self.handlers.items():
            if isinstance(context['exception'], error):
                handler(loop, context)
        raise context['exception']

import asyncio
from asyncio.unix_events import SelectorEventLoop
from typing import Callable

print(type(asyncio.new_event_loop()))

class EventLoop(SelectorEventLoop):
    def __init__(self):
        super().__init__()

        super().set_exception_handler(self.__exception_handler)
        self.handlers = {}

    def add_exception_handler(self, error, handler: Callable):
        self.handlers[error] = handler

    def del_exception_handler(self, error):
        del self.handlers[error]

    def __exception_handler(self, loop, context):
        if context['exception'] in self.handlers:
            self.handlers[context['exception']](loop, context)
        raise context['exception']

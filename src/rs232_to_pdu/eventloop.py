"""
rs232-to-pdu
Copyright (C) 2024 InkBridge Networks (legal@inkbridge.io)

rs232-to-pdu © 2024 by InkBridge is licensed under CC BY-NC 4.0. To view a copy
of this license, visit https://creativecommons.org/licenses/by-nc/4.0/
"""

import asyncio
from asyncio import BaseEventLoop
from typing import Callable


class EventLoop:
    """
    Event loop wrapper to contain dynamic exception handlers

    Thin wrapper is used over subclassing because new_event_loop() acts as a
    factory function that returns different event loop types based on the OS.
    This makes is hard to subclass properly while being OS-agnostic.
    """
    def __init__(self):
        # calls on factory method to obtain correct event loop
        self.loop = asyncio.new_event_loop()
        self.loop.set_exception_handler(self.__exception_handler)
        self.__handlers = {}

    def add_exception_handler(self, error: Exception, handler: Callable):
        """
        adds exception handler
        Args:
            error: type of exception
            handler: handler for given error

        Returns:

        """
        self.__handlers[error] = handler

    def del_exception_handler(self, error: Exception):
        """
        removes exception handler
        Args:
            error: type of exception

        Returns:

        """
        del self.__handlers[error]

    def __exception_handler(self, loop: BaseEventLoop, context):
        for error, handler in self.__handlers.items():
            if isinstance(context['exception'], error):
                handler(loop, context)
        raise context['exception']

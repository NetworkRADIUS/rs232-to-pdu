"""
Copyright (C) 2024 InkBridge Networks (legal@inkbridge.io)

This software may not be redistributed in any form without the prior
written consent of InkBridge Networks.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
SUCH DAMAGE.
"""

import asyncio
from asyncio import BaseEventLoop
from typing import Callable, AsyncContextManager


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

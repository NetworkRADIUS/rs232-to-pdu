import functools
import logging
from typing import Callable

import serial
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from serial.serialutil import SerialException
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from rs232_to_pdu.eventloop import EventLoop

logger = logging.getLogger(__name__)


class LookForFileEH(FileSystemEventHandler):
    def __init__(self, file, callback: Callable):
        self.file = file
        self.callback = callback

    def on_created(self, event):
        if event.src_path == self.file:
            self.callback()


class SerialConn:
    def __init__(self, event_loop: EventLoop,
                 device: str, reader: Callable):
        self.__event_loop = event_loop
        self.__device = device
        self.__reader = functools.partial(reader)

        self.__jobs = {}
        self.__scheduler = AsyncIOScheduler(event_loop=event_loop)
        self.file_wd = Observer()

        self.conn = None

    def open(self):
        try:
            self.conn = serial.Serial(
                port=self.__device
            )

            if self.conn.is_open:
                logger.info(f'Opened serial device {self.__device}')
                self.__event_loop.add_reader(self.conn, self.__reader, self.conn)
                self.__event_loop.add_exception_handler(OSError,
                                                        self.__error_handler)
                return
            self.__error_handler(None, None)
        except SerialException:
            logger.error(f'Failed to open serial device {self.__device}')
            self.__error_handler(None, None)

    def close(self):
        self.__event_loop.remove_reader(self.conn)
        self.__event_loop.del_exception_handler(OSError)
        self.conn.close()

    def __reconnect(self):
        if self.open():
            self.__scheduler.remove_job(self.__jobs['reconnect'])
            del self.__jobs['reconnect']
            self.file_wd.stop()

    def __error_handler(self, loop, context):
        self.conn.close()

        if 'reconnect' not in self.__jobs:
            self.__jobs['reconnect'] = self.__scheduler.add_job(
                self.conn.open, 'interval', seconds=5
            )

        if not self.file_wd.isAlive():
            self.file_wd.schedule(
                LookForFileEH(self.__device, self.conn.open),
                '/'.join(self.__device.split('/')[:-1])
            )

            self.file_wd.start()
            self.file_wd.join()

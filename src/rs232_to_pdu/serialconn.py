"""
rs232-to-pdu
Copyright (C) 2024 InkBridge Networks (legal@inkbridge.io)

rs232-to-pdu © 2024 by InkBridge is licensed under CC BY-NC 4.0. To view a copy
of this license, visit https://creativecommons.org/licenses/by-nc/4.0/
"""
import functools
import logging
from typing import Callable

import serial
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from serial.serialutil import SerialException
from watchdog.events import FileSystemEventHandler
from watchdog.observers.polling import PollingObserver

from rs232_to_pdu.eventloop import EventLoop

logger = logging.getLogger(__name__)


class EventHandlerFileCreation(FileSystemEventHandler):
    """
    event handler to call a callback when a specific file is created
    """
    def __init__(self, file, callback: Callable):
        self.file = file
        self.callback = callback

    def on_created(self, event):
        if event.src_path == self.file:
            self.callback()


class SerialConn:
    """
    class representing a serial connection
    """
    def __init__(self, event_loop: EventLoop,
                 device: str, reader: Callable):
        self.__event_loop = event_loop
        self.__device = device
        self.__reader = functools.partial(reader)

        self.conn = None

        self.__jobs = {}
        self.__file_wd = PollingObserver()
        self.__scheduler = AsyncIOScheduler(event_loop=event_loop.loop)
        self.__scheduler.start()

    def open(self):
        """
        attempts to open the connection
        Returns:

        """
        try:
            self.conn = serial.Serial(port=self.__device)

            # devices can be falsely opened without throwing an error, thus we
            # double-check ourselves
            if self.conn.is_open:
                logger.info(f'Opened serial device {self.__device}')
                # add callback for adding a reader
                self.__event_loop.loop.add_reader(self.conn, self.__reader,
                                                  self.conn)
                self.__event_loop.add_exception_handler(OSError,
                                                        self.__error_handler)
                return True
            self.__error_handler(None, None)
        except SerialException:
            logger.error(f'Failed to open serial device {self.__device}')
            self.__error_handler(None, None)
        return False

    def close(self):
        """
        closes the connection
        Returns:

        """
        # performs cleanup:
        #   - remove reader from event loop
        #   - remove exception handler
        #   - closes connection
        self.__event_loop.loop.remove_reader(self.conn)
        self.__event_loop.del_exception_handler(OSError)
        self.conn.close()

    def __reconnect(self):
        if self.open():
            # if reconnected successfully, stop the reconnection jobs
            self.__jobs['reconnect'].remove()
            del self.__jobs['reconnect']
            self.__file_wd.stop()

    def __error_handler(self, loop, context):  # pylint: disable=unused-argument
        """
        error handler for disconnected serial device
        Args:
            loop: event loop
            context: context of error

        Returns:

        """
        # remove reader and close the serial connection
        # we do not call self.close() because the error handler should not be
        # removed at this point.
        self.__event_loop.loop.remove_reader(self.conn)
        self.conn.close()

        # attempt to reconnect on a regular interval
        if 'reconnect' not in self.__jobs:
            self.__jobs['reconnect'] = self.__scheduler.add_job(
                self.__reconnect, 'interval', seconds=5
            )

        # watchdog for device file in filesystem
        if not self.__file_wd.is_alive():
            self.__file_wd.schedule(
                EventHandlerFileCreation(self.__device, self.__reconnect),
                f"{'/'.join(self.__device.split('/')[:-1])}/"
            )

            self.__file_wd.start()
            self.__file_wd.join()

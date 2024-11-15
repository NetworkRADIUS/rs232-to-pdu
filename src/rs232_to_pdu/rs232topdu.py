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

Entry point for rs-232 to SNMP converter script

Author: Patrick Guo
Date: 2024-08-13
"""
import asyncio
import functools
import logging
import time
from typing import Callable

import serial
import systemd_watchdog as sysdwd
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from serial.serialutil import SerialException
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from rs232_to_pdu.device import Device
from rs232_to_pdu.parsers.base import ParseError
from rs232_to_pdu.parsers.kvmseq import ParserKvmSequence

logger = logging.getLogger(__name__)


class QueueRunner:
    """
    Class that places commands in a queue and runs them one after another
    """

    def __init__(self) -> None:
        # Initializes an priority queue with no size limit
        self.queue = asyncio.PriorityQueue()

        # Initializes the priority counter to 0. To be used when setting
        # priority of new items
        self.prio_counter = 0

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
        priority = -self.prio_counter if high_prio else self.prio_counter
        self.prio_counter += 1

        # puts item into queue
        await self.queue.put((priority, func))

    async def dequeue(self, event_loop: asyncio.AbstractEventLoop):
        """
        Gets top priority item from queue and runs the command

        Args:
            event_loop (BaseEventLoop): event loop that is expected to keep
                                        producing commands
        """

        # as long as the event loop is running, we should be expecting new
        # items to be put into the queue
        while event_loop.is_running():
            # retrieve next item from queue and run the command
            # Will not grab next item until the previous command has been
            # completed
            _, func = await self.queue.get()
            await func()


class LookForFileEH(FileSystemEventHandler):
    """
    Event Handler to perform callback if desired file is created
    """

    def __init__(self, file_to_watch, callback: Callable) -> None:
        self.file_to_watch = file_to_watch
        self.callback_when_found = callback

    def on_created(self, event):
        if event.src_path == self.file_to_watch:
            self.callback_when_found()


class Rs232ToPdu:  # pylint: disable=too-many-instance-attributes
    """
    Command converter that takes in rs232 input and create/sends device
    commands
    """

    def __init__(  # pylint: disable=too-many-arguments
            self,
            serial_device: str, serial_timeout: int,
            max_attempts: int, delay: int, cmd_timeout: int,
            devices: dict[str: Device], healthcheck_frequency: int,
            toggle_delay: int
    ):
        """

        Args:
            serial_device: path to serial device
            serial_timeout: timeout in seconds for connecting to serial device
            max_attempts: maximum number of attempts for a command
            delay: delay between command retries
            cmd_timeout: timeout in seconds for a command
            device_config: dictionary containing config data for devices
            healthcheck_frequency: frequency of a healthcheck
            toggle_delay: delay between of and on cmds for manual toggle
        """
        # Initialize parser and command issuer
        self.kvm_parser = ParserKvmSequence()
        self.device_cmd_runner = QueueRunner()

        self.serial_device = serial_device
        self.serial_timeout = serial_timeout

        self.event_loop = asyncio.new_event_loop()

        self.scheduler = AsyncIOScheduler(event_loop=self.event_loop)
        self.jobs = {}

        self.file_watchdog = None

        self.serial_conn = None

        self.healthcheck_frequency = healthcheck_frequency

        # Initialization of other variables to be used in class
        self.read_buffer = []

        self.retry = {
            'max_attempts': max_attempts,
            'delay': delay,
            'timeout': cmd_timeout
        }

        self.devices = devices

        self.toggle_delay = toggle_delay

        self.cmd_counter = 0

        self.sysdwd = sysdwd.watchdog()

    def serial_conn_open(self):
        """
        Establishes the serial port connection

        Args:
            None

        Returns:
            None
        """
        self.sysdwd.status('Opening serial port')

        # Makes the connection
        try:
            self.serial_conn = serial.Serial(
                port=self.serial_device, timeout=self.serial_timeout,
                xonxoff=True
            )
            if self.serial_conn.is_open:
                logger.info(f'Opened serial device {self.serial_device}')
                self.sysdwd.status('Serial port successfully opened')
                return True
            logger.warning(f'Serial device {self.serial_device} is not open')
            self.sysdwd.status('Serial port is not open')
            return False
        except SerialException:
            logger.error(f'Failed to open serial device {self.serial_device}')
            self.sysdwd.status('Failed to open serial device')
            return False

    def serial_conn_close(self):
        """
        Closes the serial port connection

        Returns:

        """
        self.sysdwd.status('Closing serial port')
        self.serial_conn.close()
        self.sysdwd.status('Serial port closed')

    def serial_conn_reconnect(self):
        """
        Attempts to reconnect the serial port

        Returns:

        """
        time.sleep(0.5)
        if self.serial_conn_open():
            self.event_loop.add_reader(self.serial_conn.ser,
                                       self.serial_conn_read)
            self.jobs['reconnect'].remove()
            self.file_watchdog.stop()

    def serial_error_handler(self, loop, context):
        """
        Error handler for serial connections
        Args:
            loop: event loop
            context: error context

        Returns:

        """
        if isinstance(context['exception'], OSError):
            loop.remove_reader(self.serial_conn.ser)
            self.serial_conn_close()

            self.jobs['reconnect'] = self.scheduler.add_job(
                self.serial_conn_reconnect, 'interval', seconds=5
            )

            watch_path = '/'.join(
                self.serial_device.split('/')[:-1]
            )
            self.file_watchdog = Observer()
            self.file_watchdog.schedule(
                LookForFileEH(self.serial_device,
                              self.serial_conn_reconnect
                              ),
                watch_path
            )
            self.file_watchdog.start()
            self.file_watchdog.join()

    def healthcheck_enqueue(self) -> None:
        """
        Adds a healthcheck to the cmd queue

        Returns:

        """
        for _, device in self.devices.items():
            async def send(d):
                logger.info(
                    f'Command {self.cmd_counter} retrieving outlet {d.outlets[0]} of '
                    f'device {d.name}')
                success = await d.transport.outlet_state_get(
                    d.outlets[0])
                logger.info(
                    f'Command {self.cmd_counter} {"passed" if success else "failed"}')

            self.cmd_counter += 1
            self.event_loop.create_task(
                self.device_cmd_runner.enqueue(functools.partial(send, device),
                                               True
                                               )
            )

    def power_change_enqueue(
            self,
            device: Device, outlet: str, state: any
    ) -> None:
        """
        Adds a power change to the cmd queue

        Args:
            device: Device object
            outlet: string representation of target outlet
            state: desired outlet state

        Returns:

        """

        async def send(d, o, s):
            logger.info(
                f'Command {self.cmd_counter} setting outlet {o} of device '
                f'{d.name} to state {s}')
            success = await d.transport.outlet_state_set(
                o, d.power_states[s]
            )
            logger.info(
                f'Command {self.cmd_counter} {"passed" if success else "failed"}')

        self.cmd_counter += 1
        self.event_loop.create_task(
            self.device_cmd_runner.enqueue(
                functools.partial(send, device, outlet, state), False
            )
        )

    async def outlet_manual_toggle(self, device: Device, outlet: str):
        """
        Manually toggle the power of an outlet through off and on commands
        Args:
            device: device object
            outlet: outlet to toggle

        Returns:

        """
        logger.info(f'Performing manual power toggle for device {device.name}')
        self.power_change_enqueue(device, outlet, 'of')
        await asyncio.sleep(self.toggle_delay)
        self.power_change_enqueue(device, outlet, 'on')

    def start(self):
        """
        Entry point for starting listener

        Also sets up the healthcheck scheduler

        Returns:
            None
        """
        self.sysdwd.status('Initiating application')

        while not self.serial_conn_open():
            time.sleep(self.serial_timeout)

        self.event_loop.add_reader(self.serial_conn, self.serial_conn_read)

        self.event_loop.create_task(
            self.device_cmd_runner.dequeue(self.event_loop)
        )
        self.event_loop.set_exception_handler(self.serial_error_handler)

        self.jobs['healthcheck'] = self.scheduler.add_job(
            self.healthcheck_enqueue, 'interval',
            seconds=self.healthcheck_frequency
        )
        self.jobs['systemd_notify'] = self.scheduler.add_job(
            self.sysdwd.notify, 'interval', seconds=self.sysdwd.timeout / 2e6
        )
        self.scheduler.start()

        try:
            self.event_loop.run_forever()
        except KeyboardInterrupt:
            self.serial_conn_close()
            self.event_loop.stop()
            self.scheduler.shutdown(False)
            self.sysdwd.status('Shutting down application')

    def serial_conn_read(self):
        """
        Parses input from rs232 device and add cmd to queue if needed

        Returns:

        """
        self.read_buffer += self.serial_conn.read(
            self.serial_conn.in_waiting
        ).decode('utf-8')

        curr_seq_start_pos = 0

        for cursor_pos, buffer_char in enumerate(self.read_buffer):

            if buffer_char == '\r':
                self.buffer_parse(
                    self.read_buffer[curr_seq_start_pos:cursor_pos + 1]
                )
                curr_seq_start_pos = cursor_pos + 1

        # Delete parsed portion of buffer
        # Note that we do not attempt to reparse failed sequences because
        # we only parse completed (\r at end) sequences
        del self.read_buffer[:curr_seq_start_pos]

    def buffer_parse(self, buffer):
        """
        Parses \r terminated section of buffer
        Args:
            buffer: section of serial buffer

        Returns:

        """
        # If the \r char is encountered, attempt to parse sequence
        try:
            logger.debug((f'Received command sequence: "'
                          f'{"".join(self.read_buffer)}"')
                         )
            # Attempt to parse part of read buffer containing sequence
            parsed_tokens = self.kvm_parser.parse(''.join(buffer))

        # Errors will be raised when only a portion of the sequence has
        # been received and attempted to be parsed
        except ParseError:
            logger.warning((f'Parser failed to parse: "'
                            f'{"".join(self.read_buffer)}"')
                           )

        # If there was no error when parsing, attempt to send sequence
        else:
            self.parsed_tokens_consume(parsed_tokens)

    def parsed_tokens_consume(self, tokens):
        """
        Consumes parsed tokens to act accordingly
        Args:
            tokens: parsed token

        Returns:

        """
        if tokens[0] in ['quit', '']:
            logger.info('Quit or empty sequence detected')

        else:
            cmd, device, outlet = tokens
            logger.info(f'Setting Device {device} Outlet {outlet} to '
                        f'{cmd}')

            if cmd == 'cy' and cmd not in self.devices[
                f'{int(device):03d}'].power_states:  # pylint: disable=line-too-long
                self.event_loop.create_task(
                    self.outlet_manual_toggle(
                        self.devices[f'{int(device):03d}'],
                        f'{int(outlet):03d}')
                )
            else:
                self.power_change_enqueue(
                    self.devices[f'{int(device):03d}'],
                    f'{int(outlet):03d}', cmd
                )
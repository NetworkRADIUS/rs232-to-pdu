"""
Entry point for rs-232 to SNMP converter script

Author: Patrick Guo
Date: 2024-08-13
"""
import asyncio
import time
from typing import Callable

import pysnmp.hlapi.asyncio as pysnmp
import serial
import systemd_watchdog as sysdwd
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from serial.serialutil import SerialException
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

import rs232_to_tripplite.logfactory as nrlogfac
from rs232_to_tripplite.commands.base import BaseDeviceCommand
from rs232_to_tripplite.commands.retries import (GetCommandWithRetry,
                                                 SetCommandWithRetry)
from rs232_to_tripplite.device import Device
from rs232_to_tripplite.parsers.base import ParseError
from rs232_to_tripplite.parsers.kvmseq import ParserKvmSequence

# Set up logger for this module
nrlogfac.setup_logging()
logger = nrlogfac.create_logger(__name__)

POWERBAR_VALUES = {
    'on': pysnmp.Integer(2),
    'of': pysnmp.Integer(1),
    'cy': pysnmp.Integer(3)
}


class DeviceCmdRunner:
    """
    Class that places commands in a queue and runs them one after another
    """

    def __init__(self) -> None:
        # Initializes an priority queue with no size limit
        self.queue = asyncio.PriorityQueue()

        # Initializes the priority counter to 0. To be used when setting
        # priority of new items
        self.prio_counter = 0

    async def put_into_queue(self,
                             device_cmd: BaseDeviceCommand,
                             high_prio: bool = False) -> None:
        """
        Puts an command item into the queue.

        Can set priority to be high or low.
        New high priority items have highest priority (run first)
        New low priority items have lowest priority (run last)

        Args:
            device_cmd (BaseDeviceCmd): command object to be stored in queue
            high_prio (bool): whether the command should be run first or last
        """
        # priority is either positive or negative depending on high/low prio
        priority = -self.prio_counter if high_prio else self.prio_counter
        self.prio_counter += 1

        # puts item into queue
        await self.queue.put((priority, device_cmd))

    async def queue_processor(self, event_loop: asyncio.AbstractEventLoop):
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
            _, device_cmd = await self.queue.get()
            await device_cmd.send_command()

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

class Rs2323ToTripplite: # pylint: disable=too-many-instance-attributes
    """
    Command converter that takes in rs232 input and create/sends device
    commands
    """
    def __init__( # pylint: disable=too-many-arguments
            self,
            serial_device: str, serial_timeout: int,
            max_attempts: int, delay: int, cmd_timeout: int,
            devices: dict[str: Device], healthcheck_frequency: int ):
        """

        Args:
            serial_device: path to serial device
            serial_timeout: timeout in seconds for connecting to serial device
            max_attempts: maximum number of attempts for a command
            delay: delay between command retries
            cmd_timeout: timeout in seconds for a command
            devices: dictionary containing names to devices
            healthcheck_frequency: frequency of a healthcheck
        """
        # Initialize parser and command issuer
        self.kvm_parser = ParserKvmSequence()
        self.device_cmd_runner = DeviceCmdRunner()

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

        self.devices: dict[str: Device] = devices

        self.toggle_delay = config['power_options']['cy_delay']

        self.cmd_counter = 0

        self.sysdwd = sysdwd.watchdog()

    def make_connection(self):
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

    def close_connection(self):
        """
        Closes the serial port connection

        Returns:

        """
        self.sysdwd.status('Closing serial port')
        self.serial_conn.close()
        self.sysdwd.status('Serial port closed')

    def attempt_reconnect(self):
        """
        Attempts to reconnect the serial port

        Returns:

        """
        time.sleep(0.5)
        if self.make_connection():
            self.event_loop.add_reader(self.serial_conn.ser,
                                       self.read_serial_conn)
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
        if isinstance(OSError, context['exception']):
            loop.remove_reader(self.serial_conn.ser)
            self.close_connection()

            self.jobs['reconnect'] = self.scheduler.add_job(
                self.attempt_reconnect, 'interval', seconds=5
            )

            watch_path = '/'.join(
                self.serial_device.split('/')[:-1]
            )
            self.file_watchdog = Observer()
            self.file_watchdog.schedule(
                LookForFileEH(self.serial_device,
                              self.attempt_reconnect
                              ),
                watch_path
            )
            self.file_watchdog.start()
            self.file_watchdog.join()

    def add_healthcheck_to_queue(self) -> None:
        """
        Adds a healthcheck to the cmd queue

        Returns:

        """
        for _, device in self.devices.items():
            self.cmd_counter += 1
            self.event_loop.create_task(
                self.device_cmd_runner.put_into_queue(
                    GetCommandWithRetry(
                        device,
                        # always check the first outlet
                        device.outlets[0],
                        self.retry['timeout'], 1, 0,
                        self.cmd_counter
                    ), True
                )
            )

    def add_power_change_to_queue(
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
        self.cmd_counter += 1
        self.event_loop.create_task(
            self.device_cmd_runner.put_into_queue(
                SetCommandWithRetry(
                    device, outlet, state,
                    self.retry['timeout'], self.retry['max_attempts'],
                    self.retry['delay'],
                    self.cmd_counter
                )
            )
        )

    async def manual_outlet_toggle(self, device: Device, outlet: str):
        logger.info(f'Performing manual power toggle for device {device.name}')
        self.add_power_change_to_queue(device, outlet, 'of')
        await asyncio.sleep(self.toggle_delay)
        self.add_power_change_to_queue(device, outlet, 'on')

    def start(self):
        """
        Entry point for starting listener

        Also sets up the healthcheck scheduler

        Returns:
            None
        """
        self.sysdwd.status('Initiating application')

        while not self.make_connection():
            time.sleep(self.serial_timeout)

        self.event_loop.add_reader(self.serial_conn, self.read_serial_conn)

        self.event_loop.create_task(
            self.device_cmd_runner.queue_processor(self.event_loop)
        )
        self.event_loop.set_exception_handler(self.serial_error_handler)

        self.jobs['healthcheck'] = self.scheduler.add_job(
            self.add_healthcheck_to_queue, 'interval',
            seconds=self.healthcheck_frequency
        )
        self.jobs['systemd_notify'] = self.scheduler.add_job(
            self.sysdwd.notify, 'interval', seconds=self.sysdwd.timeout / 2e6
        )
        self.scheduler.start()

        try:
            self.event_loop.run_forever()
        except KeyboardInterrupt:
            self.close_connection()
            self.event_loop.stop()
            self.scheduler.shutdown(False)
            self.sysdwd.status('Shutting down application')

    def read_serial_conn(self):
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
                self.parse_buffer(
                    self.read_buffer[curr_seq_start_pos:cursor_pos + 1]
                )
                curr_seq_start_pos = cursor_pos + 1

        # Delete parsed portion of buffer
        # Note that we do not attempt to reparse failed sequences because
        # we only parse completed (\r at end) sequences
        del self.read_buffer[:curr_seq_start_pos]

    def parse_buffer(self, buffer):
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
            self.consume_parsed_tokens(parsed_tokens)

    def consume_parsed_tokens(self, tokens):
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

            if cmd == 'cy' and cmd not in self.devices[f'{int(device):03d}'].power_options:
                self.event_loop.create_task(
                    self.manual_outlet_toggle(self.devices[f'{int(device):03d}'], f'{int(outlet):03d}')
                )
            else:
                self.add_power_change_to_queue(
                    self.devices[f'{int(device):03d}'],
                    f'{int(outlet):03d}', POWERBAR_VALUES[cmd]
                )

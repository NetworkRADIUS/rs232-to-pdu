"""
Entry point for rs-232 to SNMP converter script

Author: Patrick Guo
Date: 2024-08-13
"""
import asyncio
import pathlib
import time
from typing import Callable

import pysnmp.hlapi.asyncio as pysnmp
import serial
import systemd_watchdog as sysdwd
import yaml
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from serial.serialutil import SerialException
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

import rs232_to_tripplite.logfactory as nrlogfac
from rs232_to_tripplite.commands.base import BaseDeviceCommand
from rs232_to_tripplite.commands.retries import (GetCommandWithRetry,
                                                 SetCommandWithRetry)
from rs232_to_tripplite.device import create_device_from_config_dict, Device
from rs232_to_tripplite.parsers.base import ParseError
from rs232_to_tripplite.parsers.kvmseq import ParserKvmSequence

# Read and setup configs
CONFIG_FILE = pathlib.Path('config.yaml')
with open(CONFIG_FILE, 'r', encoding='utf-8') as fileopen:
    config = yaml.load(fileopen, Loader=yaml.FullLoader)

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
            priority, device_cmd = await self.queue.get()
            await device_cmd.send_command()


class ListenerScheduler:
    def __init__(self, event_loop):
        self.scheduler = AsyncIOScheduler(event_loop=event_loop)

        self.jobs = {}

    def start_healthcheck_job(self, add_hc_to_queue_func, frequency=5):
        self.jobs['healthcheck'] = self.scheduler.add_job(
            add_hc_to_queue_func, 'interval', seconds=frequency
        )

    def start_reconnect_job(self, reconnect_func, frequency=5):
        self.jobs['reconnect'] = self.scheduler.add_job(
            reconnect_func, 'interval', seconds=frequency
        )

    def start_systemd_notify(self, notify_func, frequency):
        self.jobs['systemd_notify'] = self.scheduler.add_job(
            notify_func, 'interval', seconds=frequency
        )

    def remove_reconnect_job(self):
        self.jobs['reconnect'].remove()

    def start(self):
        self.scheduler.start()

    def shutdown(self, wait=False):
        self.scheduler.shutdown(wait)


class LookForFileEH(FileSystemEventHandler):
    def __init__(self, file_to_watch, callback: Callable) -> None:
        self.file_to_watch = file_to_watch
        self.callback_when_found = callback

    def on_created(self, event):
        if event.src_path == self.file_to_watch:
            self.callback_when_found()


class SerialConnection:
    """
    Wrapper class for making a serial connection
    """

    def __init__(self) -> None:
        self.ser = None

    def make_connection(self,
                        port: str = None,
                        baud: int = 9600,
                        timeout: int = None,
                        xonxoff: bool = True) -> bool:
        """
        Makes connection with given parameters

        Args:
            port (str): name of serial port to make connection with
            baud (int): baud rate of connection
            timeout (int): timeout on read operations
            xonxoff (bool): enabling of software flow control

        Returns:
            None
        """
        try:
            self.ser = serial.Serial(port=port, timeout=timeout,
                                     xonxoff=xonxoff)
            logger.info((f'Serial port opened, device {port}, baud {baud}, '
                         f'timeout {timeout}, Software Flow Control {xonxoff}')
                        )
            # Checks if connection was actually opened
            return not self.ser is None
        except SerialException as e:
            logger.info((f'Serial port failed to open: device {port}, '
                         f'baud {baud}, timeout {timeout}, Software Flow '
                         f'Control {xonxoff}, Error: {e}')
                        )
            return False

    def read_all_waiting_bytes(self) -> str:
        """
        Reads all bytes waiting in the stream

        Args:
            None

        Returns:
            decoded string of bytes read
        """
        return self.ser.read(self.ser.in_waiting).decode('utf-8')

    def close_connection(self) -> str:
        """
        Closes connection with serial port

        Args:
            None

        Returns:
            None
        """
        self.ser.close()


class SerialListener:
    """
    Listen for serial messages and convert into SNMP commands
    """

    def __init__(self):
        # Initialize parser and snmp command issuer
        self.kvm_parser = ParserKvmSequence()
        self.device_cmd_runner = DeviceCmdRunner()

        self.event_loop = asyncio.new_event_loop()
        self.scheduler = ListenerScheduler(self.event_loop)
        self.file_watchdog = None

        # Create serial connection
        self.serial_conn = SerialConnection()

        # Initialization of other variables to be used in class
        self.read_buffer = []

        self.retry = {
            'max_attempts': int(config['snmp']['retry']['max_attempts']),
            'delay': int(config['snmp']['retry']['delay']),
            'timeout': int(config['snmp']['retry']['timeout'])
        }

        self.devices: dict[str: Device] = {}
        for device_name in config['devices'].keys():
            self.devices[device_name] = create_device_from_config_dict(
                device_name, config['devices'][device_name]
            )

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
        serial_port = config['serial']['device']
        serial_timeout = int(config['serial']['timeout'])
        if self.serial_conn.make_connection(serial_port,
                                            timeout=serial_timeout):
            self.sysdwd.status('Serial port successfully opened')
            return True
        self.sysdwd.status('Serial port failed to open')
        return False

    def close_connection(self):
        self.sysdwd.status('Closing serial port')
        self.serial_conn.close_connection()
        self.sysdwd.status('Serial port closed')

    def attempt_reconnect(self):
        time.sleep(0.5)
        if self.make_connection():
            self.event_loop.add_reader(self.serial_conn.ser,
                                       self.read_serial_conn)
            self.scheduler.remove_reconnect_job()
            self.file_watchdog.stop()

    def serial_error_handler(self, loop, context):
        match type(context['exception']):
            case OSError:
                loop.remove_reader(self.serial_conn.ser)
                self.close_connection()

                self.scheduler.start_reconnect_job(self.attempt_reconnect)

                watch_path = '/'.join(
                    config['serial']['device'].split('/')[:-1]
                )
                self.file_watchdog = Observer()
                self.file_watchdog.schedule(
                    LookForFileEH(config['serial']['device'],
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
        for device_name in self.devices:
            self.cmd_counter += 1
            self.event_loop.create_task(
                self.device_cmd_runner.put_into_queue(
                    GetCommandWithRetry(
                        self.devices[device_name],
                        # always check the first outlet
                        self.devices[device_name].outlets[0],
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
            state: desired outlet state (in pysnmp state)

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

    def start(self):
        """
        Entry point for starting listener

        Also sets up the healthcheck scheduler

        Returns:
            None
        """
        self.sysdwd.status('Initiating application')

        while not self.make_connection():
            time.sleep(config['serial']['timeout'])

        self.event_loop.add_reader(self.serial_conn.ser, self.read_serial_conn)

        self.event_loop.create_task(
            self.device_cmd_runner.queue_processor(self.event_loop)
        )
        self.event_loop.set_exception_handler(self.serial_error_handler)

        self.scheduler.start_healthcheck_job(
            self.add_healthcheck_to_queue, config['healthcheck']['frequency']
        )
        self.scheduler.start_systemd_notify(
            self.sysdwd.notify, self.sysdwd.timeout / 2e6
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
        self.read_buffer += self.serial_conn.read_all_waiting_bytes()

        curr_seq_start_pos = 0

        for cursor_pos, buffer_char in enumerate(self.read_buffer):

            if buffer_char != '\r':
                continue

            # If the \r char is encountered, attempt to parse sequence
            try:
                logger.debug((f'Received command sequence: "'
                              f'{"".join(self.read_buffer)}"')
                             )
                # Attempt to parse part of read buffer containing sequence
                parsed_tokens = self.kvm_parser.parse(
                    ''.join(
                        self.read_buffer[curr_seq_start_pos:cursor_pos + 1]
                    )
                )

            # Errors will be raised when only a portion of the sequence has
            # been received and attempted to be parsed
            except ParseError:
                logger.warning((f'Parser failed to parse: "'
                                f'{"".join(self.read_buffer)}"')
                               )

            # If there was no error when parsing, attempt to send sequence
            else:
                # Upon encountering quit and empty sequence, do nothing
                if parsed_tokens[0] in ['quit', '']:
                    logger.info('Quit or empty sequence detected')

                else:
                    cmd, device, outlet = parsed_tokens
                    logger.info(f'Setting Device {device} Outlet {outlet} to '
                                f'{cmd}')

                    self.add_power_change_to_queue(
                        self.devices[f'{int(device):03d}'],
                        f'{int(outlet):03d}', cmd
                    )

            curr_seq_start_pos = cursor_pos + 1

        # Delete parsed portion of buffer
        # Note that we do not attempt to reparse failed sequences because
        # we only parse completed (\r at end) sequences
        del self.read_buffer[:curr_seq_start_pos]


if __name__ == '__main__':
    serial_listener = SerialListener()
    serial_listener.start()

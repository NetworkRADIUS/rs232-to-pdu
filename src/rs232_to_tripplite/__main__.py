"""
Entry point for rs-232 to SNMP converter script

Author: Patrick Guo
Date: 2024-08-13
"""
import asyncio
import pathlib
import time
import systemd_watchdog as sysdwd

import pysnmp.hlapi.asyncio as pysnmp
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Callable
import yaml

import rs232_to_tripplite.logfactory as nrlogfac
from rs232_to_tripplite.serialconn import SerialConnection
from rs232_to_tripplite.parsers.base import ParseError
from rs232_to_tripplite.parsers.kvmseq import ParserKvmSequence
from rs232_to_tripplite.requests.tripplitedevicehealthcheckcmd import TrippliteDeviceHealthcheckCmd
from rs232_to_tripplite.requests.tripplitedevicepowerchangecmd import TrippliteDevicePowerChangeCmd
from rs232_to_tripplite.cmdrunner import DeviceCmdRunner
from rs232_to_tripplite.scheduler import ListenerScheduler
from rs232_to_tripplite.transport.base import create_device_from_config_dict, Device

# Read and setup configs
CONFIG_FILE = pathlib.Path('/etc', 'ser2snmp', 'config.yaml')
with open(CONFIG_FILE, 'r', encoding='utf-8')as fileopen:
    config = yaml.load(fileopen, Loader=yaml.FullLoader)

# Set up logger for this module
nrlogfac.setup_logging()
logger = nrlogfac.create_logger(__name__)


POWERBAR_VALUES = {
    'on': pysnmp.Integer(2),
    'of': pysnmp.Integer(1),
    'cy': pysnmp.Integer(3)
}

class LookForFileEH(FileSystemEventHandler):
    def __init__(self, file_to_watch, callback: Callable) -> None:
        self.file_to_watch = file_to_watch
        self.callback_when_found = callback

    def on_created(self, event):
        if event.src_path == self.file_to_watch:
            self.callback_when_found()

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
            'retry_delay': int(config['snmp']['retry']['delay']),
            'timeout': int(config['snmp']['retry']['timeout'])
        }

        self.devices: dict[str: Device] = {}
        for device_name in config['transport'].keys():
            self.devices[device_name] = create_device_from_config_dict(
                device_name, config['transport'][device_name]
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
        serial_port    = config['serial']['device']
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
            self.event_loop.add_reader(self.serial_conn.ser, self.read_serial_conn)
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
                    TrippliteDeviceHealthcheckCmd(
                        self.devices[device_name],
                        # always check the first outlet
                        self.devices[device_name].outlets[0],
                        self.retry['timeout'],
                        self.cmd_counter
                    )
                )
            )

    def add_power_change_to_queue(
            self,
            device: Device, target_outlet: str, outlet_state: any
        ) -> None:
        """
        Adds a power change to the cmd queue

        Args:
            device: Device object
            target_outlet: string representation of target outlet
            outlet_state: desired outlet state (in pysnmp state)

        Returns:

        """
        self.cmd_counter += 1
        self.event_loop.create_task(
            self.device_cmd_runner.put_into_queue(
                TrippliteDevicePowerChangeCmd(
                    device, target_outlet, outlet_state,
                    self.retry['max_attempts'], self.retry['delay'],
                    self.retry['timeout'],
                    self.cmd_counter
                )
            )
        )


    def start(self):
        """
        Entry point for starting listener

        Also sets up the healthcheck scheduler

        Args:
            None

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

            # Errors will be raised when only a portion of the sequence has been
            # received and attempted to be parsed
            except ParseError:
                logger.warning((f'Parser failed to parse: "'
                            f'{"".join(self.read_buffer)}"')
                           )

            else:
                # Upon encountering quit and empty sequence, do nothing
                if parsed_tokens[0] in ['quit', '']:
                    logger.info('Quit or empty sequence detected')

                else:
                    cmd, device, outlet = parsed_tokens
                    logger.info(f'Setting Device {device} Outlet {outlet} to '
                                f'{cmd}')

                    self.add_power_change_to_queue(
                        device, f'{int(outlet):03d}', POWERBAR_VALUES[cmd]
                    )

            curr_seq_start_pos = cursor_pos + 1

        # Delete parsed portion of buffer
        # Note that we do not attempt to reparse failed sequences because
        # we only parse completed (\r at end) sequences
        del self.read_buffer[:curr_seq_start_pos]

if __name__ == '__main__':
    serial_listerner = SerialListener()
    serial_listerner.start()

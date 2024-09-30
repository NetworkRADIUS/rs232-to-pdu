"""
Entry point for rs-232 to SNMP converter script

Author: Patrick Guo
Date: 2024-08-13
"""

import asyncio
import configparser
import enum
import pathlib
import time
import systemd_watchdog as sysdwd

import pysnmp.hlapi.asyncio as pysnmp
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Callable

import sersnmplogging.loggingfactory as nrlogfac
from sersnmpconnectors.conn_serial import SerialConnection
from sersnmpparsers.parse_base import ParseError
from sersnmpparsers.parse_kvmseq import ParserKvmSequence
from sersnmprequests.basesnmpcmd import AgentLocator, SnmpUser
from sersnmprequests.healthcheckcmd import HealthcheckCmd
from sersnmprequests.powerchangecmd import PowerChangeCmd
from sersnmprequests.snmpcmdrunner import SnmpCmdRunner
from sersnmpscheduler.sersnmpscheduler import ListenerScheduler

# Read and setup configs
CONFIG_FILE = pathlib.Path('config.ini')
CONFIG = configparser.ConfigParser()
CONFIG.read(CONFIG_FILE)

# Set up logger for this module
nrlogfac.setup_logging()
logger = nrlogfac.create_logger(__name__)


class PowerbarValues(enum.Enum):
    """Possible power values for powerbar ports
    """
    OFF = 1
    ON = 2
    CYCLE = 3

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
        self.snmp_cmd_runner = SnmpCmdRunner()

        self.event_loop = asyncio.new_event_loop()
        self.scheduler = ListenerScheduler(self.event_loop)
        self.file_watchdog = None

        self.sysdwd = sysdwd.watchdog()

        # if not self.sysdwd.is_enabled:
        #     raise OSError('Systemd watchdog not enabled')

        # Create serial connection
        self.serial_conn = SerialConnection()

        # Initialization of other variables to be used in class
        self.read_buffer = []

        # Reads configs
        self.agent_loc = AgentLocator(CONFIG['PDU_LOCATION']['IP_ADDRESS'],
                                      int(CONFIG['PDU_LOCATION']['PORT']))
        self.snmp_user = SnmpUser(
            CONFIG['PDU_AUTH']['USER'],
            CONFIG['PDU_AUTH']['AUTH_PASSPHRASE'],
            CONFIG['PDU_AUTH']['PRIV_PASSPHRASE'],
            pysnmp.usmHMACSHAAuthProtocol if CONFIG['PDU_AUTH']['AUTH'] == 'SHA' else None,
            pysnmp.usmAesCfb128Protocol if CONFIG['PDU_AUTH']['PRIV'] == 'AES' else None
        )

        self.timeout = int(CONFIG['SNMP_RETRY']['TIMEOUT'])

        self.max_attempts = int(CONFIG['SNMP_RETRY']['MAX_ATTEMPTS'])
        self.retry_delay = int(CONFIG['SNMP_RETRY']['RETRY_DELAY'])

        self.cmd_counter = 0


    def make_connection(self):
        """
        Establishes the serial port connection

        Args:
            None

        Returns:
            None
        """
        self.sysdwd.status('Openning serial port')

        # Makes the connection
        serial_port    = CONFIG['SERIAL_CONFIGS']['SERIAL_PORT']
        serial_timeout = int(CONFIG['SERIAL_CONFIGS']['TIMEOUT'])
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
                    CONFIG['SERIAL_CONFIGS']['SERIAL_PORT'].split('/')[:-1]
                )
                self.file_watchdog = Observer()
                self.file_watchdog.schedule(
                    LookForFileEH(CONFIG['SERIAL_CONFIGS']['SERIAL_PORT'],
                                self.attempt_reconnect
                    ),
                    watch_path
                )
                self.file_watchdog.start()
                self.file_watchdog.join()
    
    def add_healthcheck_to_queue(self) -> None:
        """
        Adds a health check command to the priority queue with high priority

        Args:
            None

        Returns:
            None
        """

        # create new command object
        new_cmd = HealthcheckCmd(
            self.agent_loc.agent_ip, self.agent_loc.agent_port,
            self.snmp_user.username,
            self.snmp_user.auth, self.snmp_user.priv,
            self.snmp_user.auth_protocol,
            self.snmp_user.priv_procotol,
            self.timeout, self.max_attempts, self.retry_delay,
            self.cmd_counter
        )

        self.cmd_counter += 1

        # create new coroutine to add task to queue
        self.event_loop.create_task(
            self.snmp_cmd_runner.put_into_queue(new_cmd, True)
        )

    def add_power_change_to_queue(
            self,
            object_value: int, object_identities: str,
            outlet_bank: int, outlet_port: int
        ) -> None:
        """
        Adds a power change command to the priority queue with low priority

        Args:
            object_value (int): new value for power outlet MIB
            object_identities (str): OID for MIB
            outlet_bank (int): bank number for outlet
            outlet_port (int): bank number for outlet
        """

        # create new command object
        new_cmd = PowerChangeCmd(
            self.agent_loc.agent_ip, self.agent_loc.agent_port,
            self.snmp_user.username,
            self.snmp_user.auth, self.snmp_user.priv,
            self.snmp_user.auth_protocol, self.snmp_user.priv_procotol,
            self.timeout, self.max_attempts, self.retry_delay,
            object_value, object_identities,
            outlet_bank, outlet_port,
            self.cmd_counter
        )

        self.cmd_counter += 1

        # create new coroutine to add task to queue
        self.event_loop.create_task(
            self.snmp_cmd_runner.put_into_queue(new_cmd)
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
            time.sleep(self.timeout)

        self.event_loop.add_reader(self.serial_conn.ser, self.read_serial_conn)

        self.event_loop.create_task(
            self.snmp_cmd_runner.queue_processor(self.event_loop)
        )
        self.event_loop.set_exception_handler(self.serial_error_handler)

        self.scheduler.start_healthcheck_job(self.add_healthcheck_to_queue)
        self.scheduler.start_systemd_notify(self.sysdwd.notify, self.sysdwd.timeout / 2e6)
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
        Listener callback function to read serial input

        Args:
            None
        
        Returns:
            None
        """
        # Read and appends all waiting bytes to read buffer
        self.read_buffer += self.serial_conn.read_all_waiting_bytes()

        # variable for holding the start position of the current seq
        curr_seq_start_pos = 0

        # Iterate through entire read buffer
        for cursor_pos, buffer_char in enumerate(self.read_buffer):

            # If the \r char is encountered, attempt to parse sequence
            if buffer_char == '\r':
                try:
                    logger.debug('Received command sequence: "%s"',
                                ''.join(self.read_buffer))
                    # Attempt to parse part of read buffer containing sequence
                    parsed_tokens = self.kvm_parser.parse(''.join(self.read_buffer[curr_seq_start_pos:cursor_pos + 1]))

                    # Upon encountering quit and empty sequence, do nothing
                    if parsed_tokens[0] in ['quit', '']:
                        logger.info('Quit or empty sequence detected')
                        return
                    
                    cmd, bank, port = parsed_tokens
                    logger.info('Setting Bank %s Port %s to %s',
                                bank, port, cmd.upper())

                    # Retrieve OID from config
                    obj_oid = (CONFIG[f'BANK{bank:03d}'][f'PORT{port:03d}'],)

                    # Create SNMP command based on command from sequence
                    match cmd:
                        case 'on':
                            self.add_power_change_to_queue(
                                pysnmp.Integer(PowerbarValues.ON.value), obj_oid,
                                bank, port
                            )
                        case 'of':
                            self.add_power_change_to_queue(
                                pysnmp.Integer(PowerbarValues.OFF.value), obj_oid,
                                bank, port
                            )
                        case 'cy':
                            self.add_power_change_to_queue(
                                pysnmp.Integer(PowerbarValues.CYCLE.value), obj_oid,
                                bank, port
                            )

                # Errors will be raised when only a portion of the sequence has been
                # received and attempted to be parsed
                except ParseError:
                    logger.warning('Parser failed to parse: "%s"',
                                ''.join(self.read_buffer))
                curr_seq_start_pos = cursor_pos + 1

        # Delete parsed portion of buffer
        # Note that we do not attempt to re-parse failed sequences because
        # we only parse completed (\r at end) sequences
        del self.read_buffer[:curr_seq_start_pos]

if __name__ == '__main__':
    serial_listerner = SerialListener()
    serial_listerner.start()

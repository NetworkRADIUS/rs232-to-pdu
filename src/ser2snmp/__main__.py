"""
Entry point for rs-232 to SNMP converter script

Author: Patrick Guo
Date: 2024-08-13
"""
import asyncio
import enum
import pathlib
import time
import systemd_watchdog as sysdwd

import pysnmp.hlapi.asyncio as pysnmp
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Callable
import yaml

import ser2snmp.logging.loggingfactory as nrlogfac
from ser2snmp.connectors.conn_serial import SerialConnection
from ser2snmp.parsers.parse_base import ParseError
from ser2snmp.parsers.parse_kvmseq import ParserKvmSequence
from ser2snmp.requests.basesnmpcmd import SnmpUser
from ser2snmp.requests.healthcheckcmd import HealthcheckCmd
from ser2snmp.requests.powerchangecmd import PowerChangeCmd
from ser2snmp.requests.snmpcmdrunner import SnmpCmdRunner
from ser2snmp.scheduler.sersnmpscheduler import ListenerScheduler

# Read and setup configs
CONFIG_FILE = pathlib.Path('/etc', 'ser2snmp', 'config.yaml')
with open(CONFIG_FILE, 'r', encoding='utf-8')as fileopen:
    CONFIG = yaml.load(fileopen, Loader=yaml.FullLoader)

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

        # Create serial connection
        self.serial_conn = SerialConnection()

        # Initialization of other variables to be used in class
        self.read_buffer = []

        self.snmp_user = SnmpUser(
            CONFIG['pdu_auth']['user'],
            CONFIG['pdu_auth']['auth_passphrase'],
            CONFIG['pdu_auth']['priv_passphrase'],
            pysnmp.usmHMACSHAAuthProtocol if CONFIG['pdu_auth']['auth'] == 'SHA' else None,
            pysnmp.usmAesCfb128Protocol if CONFIG['pdu_auth']['priv'] == 'AES' else None
        )

        self.timeout = int(CONFIG['snmp_retry']['timeout'])

        self.max_attempts = int(CONFIG['snmp_retry']['max_attempts'])
        self.retry_delay = int(CONFIG['snmp_retry']['retry_delay'])

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
        self.sysdwd.status('Openning serial port')

        # Makes the connection
        serial_port    = CONFIG['serial_configs']['serial_port']
        serial_timeout = int(CONFIG['serial_configs']['timeout'])
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
                    CONFIG['serial_configs']['serial_port'].split('/')[:-1]
                )
                self.file_watchdog = Observer()
                self.file_watchdog.schedule(
                    LookForFileEH(CONFIG['serial_configs']['serial_port'],
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
        for bank_num in CONFIG['banks'].keys():
            agent_ip = CONFIG['banks'][bank_num]['ip_address']
            agent_port = int(CONFIG['banks'][bank_num]['snmp_port'])

            # create new command object
            new_cmd = HealthcheckCmd(
                agent_ip, agent_port,
                self.snmp_user.username,
                self.snmp_user.auth, self.snmp_user.priv,
                self.snmp_user.auth_protocol,
                self.snmp_user.priv_procotol,
                self.timeout, self.max_attempts, self.retry_delay,
                self.cmd_counter, bank_num=bank_num
            )

            self.cmd_counter += 1

            # create new coroutine to add task to queue
            self.event_loop.create_task(
                self.snmp_cmd_runner.put_into_queue(new_cmd, True)
            )

    def add_power_change_to_queue(
            self,
            agent_ip: str, agent_port: int,
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
            agent_ip, agent_port,
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
        Listener callback function to read serial input

        Args:
            None
        
        Returns:
            None
        """
        self.read_buffer += self.serial_conn.read_all_waiting_bytes()

        curr_seq_start_pos = 0

        for cursor_pos, buffer_char in enumerate(self.read_buffer):

            # If the \r char is encountered, attempt to parse sequence
            if buffer_char == '\r':
                try:
                    logger.debug('Received command sequence: "%s"',
                                ''.join(self.read_buffer))
                    # Attempt to parse part of read buffer containing sequence
                    parsed_tokens = self.kvm_parser.parse(
                        ''.join(
                            self.read_buffer[curr_seq_start_pos:cursor_pos + 1]
                        )
                    )

                    # Upon encountering quit and empty sequence, do nothing
                    if parsed_tokens[0] in ['quit', '']:
                        logger.info('Quit or empty sequence detected')
                        return

                    cmd, bank, port = parsed_tokens
                    logger.info('Setting Bank %s Port %s to %s',
                                bank, port, cmd.upper())

                    agent_ip = CONFIG['banks'][f'{bank:03d}']['ip_address']
                    agent_port = int(CONFIG['banks'][f'{bank:03d}']['snmp_port'])
                    obj_oid = (CONFIG['banks'][f'{bank:03d}']['ports'][f'{port:03d}'],)

                    match cmd:
                        case 'on':
                            self.add_power_change_to_queue(
                                agent_ip, agent_port,
                                pysnmp.Integer(PowerbarValues.ON.value),
                                obj_oid, bank, port
                            )
                        case 'of':
                            self.add_power_change_to_queue(
                                agent_ip, agent_port,
                                pysnmp.Integer(PowerbarValues.OFF.value),
                                obj_oid, bank, port
                            )
                        case 'cy':
                            self.add_power_change_to_queue(
                                agent_ip, agent_port,
                                pysnmp.Integer(PowerbarValues.CYCLE.value),
                                obj_oid, bank, port
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

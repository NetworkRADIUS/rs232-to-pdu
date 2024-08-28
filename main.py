"""
Entry point for rs-232 to SNMP converter script

Author: Patrick Guo
Date: 2024-08-13
"""

import asyncio
import configparser
import enum
import pathlib

import pysnmp.hlapi.asyncio as pysnmp
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import nrlogging.loggingfactory as nrlogfac
from nrconnectors.conn_serial import SerialConnection
from nrparsers.parse_base import ParseError
from nrparsers.parse_kvmseq import ParserKvmSequence
from nrrequests.basesnmpcmd import AgentLocator, SnmpUser
from nrrequests.healthcheckcmd import HealthcheckCmd
from nrrequests.powerchangecmd import PowerChangeCmd
from nrrequests.snmpcmdrunner import SnmpCmdRunner

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


class SerialListener:
    """
    Listen for serial messages and convert into SNMP commands
    """
    def __init__(self):
        # Initialize parser and snmp command issuer
        self.kvm_parser = ParserKvmSequence()
        self.snmp_cmd_runner = SnmpCmdRunner()

        self.event_loop = None
        self.scheduler = None

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

        self.max_attempts = int(CONFIG['SNMP_RETRY']['RETRY_ATTEMPTS'])
        self.retry_delay = int(CONFIG['SNMP_RETRY']['RETRY_DELAY'])


    def make_connection(self):
        """
        Establishes the serial port connection

        Args:
            None

        Returns:
            None
        """
        # Makes the connection
        serial_port    = CONFIG['SERIAL_CONFIGS']['SERIAL_PORT']
        serial_timeout = int(CONFIG['SERIAL_CONFIGS']['TIMEOUT'])
        self.serial_conn.make_connection(serial_port, timeout=serial_timeout)

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
            self.timeout, self.max_attempts, self.retry_delay
        )

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
            outlet_bank, outlet_port
        )

        # create new coroutine to add task to queue
        self.event_loop.create_task(
            self.snmp_cmd_runner.put_into_queue(new_cmd)
        )

    def start_listening(self):
        """
        Entry point for starting listener

        Also sets up the healthcheck scheduler

        Args:
            None

        Returns:
            None
        """
        self.event_loop = asyncio.new_event_loop()
        self.event_loop.add_reader(self.serial_conn.ser, self.read_serial_conn)

        self.event_loop.create_task(
            self.snmp_cmd_runner.queue_processor(self.event_loop)
        )

        # # Create and start the scheduler for running healthchecks
        self.scheduler = AsyncIOScheduler(event_loop=self.event_loop)
        self.scheduler.add_job(
            self.add_healthcheck_to_queue, 'interval', [], seconds=5)
        self.scheduler.start()

        self.event_loop.run_forever()

    def read_serial_conn(self):
        """
        Listener callback function to read serial input

        Args:
            None
        
        Returns:
            None
        """
        # Read and append byte from serial port to parsing buffer
        read_data = self.serial_conn.read_byte()

        # Don't attempt to parse if end-of-sequence character not received
        if read_data != '\r':
            self.read_buffer.append(read_data)

        # Only parse if the end-of-sequence character was received
        else:
            try:
                logger.debug('Received command sequence: "%s"',
                             ''.join(self.read_buffer))
                # Attempts to parse current buffer
                cmd, bank, port = self.kvm_parser.parse(''.join(self.read_buffer))

                if cmd in ['quit', '']:
                    logger.info('Quit or empty sequence detected')
                    return

                logger.info('Setting Bank %s Port %s to %s',
                            bank, port, cmd.upper())

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

                # Reset buffer to avoid re-parsing the same sequence twice
                # Note that we only do this if the parser successfully parsed a
                # sequence.
                self.read_buffer.clear()

            # Errors will be raised when only a portion of the sequence has been
            # received and attempted to be parsed
            except ParseError:
                logger.warning('Parser failed to parse: "%s"',
                            ''.join(self.read_buffer))


if __name__ == '__main__':
    serial_listerner = SerialListener()
    serial_listerner.make_connection()
    serial_listerner.start_listening()

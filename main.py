"""
Entry point for rs-232 to SNMP converter script

Author: Patrick Guo
Date: 2024-08-13
"""

import asyncio
import configparser
import pathlib

import nrlogging.loggingfactory as nrlogfac
from nrconnectors.conn_serial import SerialConnection
from nrparsers.parse_base import ParseError
from nrparsers.parse_kvmseq import ParserKvmSequence
from nrrequests.req_snmp import SnmpCommandIssuer

# Read and setup configs
CONFIG_FILE = pathlib.Path('config.ini')
CONFIG = configparser.ConfigParser()
CONFIG.read(CONFIG_FILE)

# Set up logger for this module
nrlogfac.setup_logging()
logger = nrlogfac.create_logger(__name__)

class SerialListener:
    """
    Listen for serial messages and convert into SNMP commands
    """
    def __init__(self):
        # Initialize parser and snmp command issuer
        self.kvm_parser = ParserKvmSequence()
        self.snmp_cmd_issuer = SnmpCommandIssuer()

        # Create serial connection
        serial_port    = CONFIG['SERIAL_CONFIGS']['SERIAL_PORT']
        serial_timeout = int(CONFIG['SERIAL_CONFIGS']['TIMEOUT'])
        self.serial_conn = SerialConnection(serial_port, serial_timeout)

        logger.info('Created SerialConnection on port %s with timeout %d',
                    serial_port, serial_timeout)

        # Initialization of other variables to be used in class
        self.read_buffer = []
        self.event_loop = None
        self.target_ip = CONFIG['PDU_LOCATION']['IP_ADDRESS']
        self.target_port = CONFIG['PDU_LOCATION']['PORT']

    def start_listening(self):
        """
        Entry point for starting listener

        Args:
            None

        Returns:
            None
        """
        logger.info('Beginning listener')
        self.event_loop = asyncio.new_event_loop()
        self.event_loop.add_reader(self.serial_conn.ser, self.read_serial_conn)
        self.event_loop.run_forever()

    @staticmethod
    def get_bank_port_oid(bank: str, port: str) -> str:
        """
        Retrieves OID for specific bank/port from config file

        Args:
            bank (str): bank number as a string
            port (str): port number as a string

        Returns:
            String conatining full OID of bank/port outlet command
        """
        return CONFIG[f'BANK{bank:03d}'][f'PORT{port:03d}']

    def read_serial_conn(self):
        """
        Listener callback function to read serial input

        Args:
            None
        
        Returns:
            None
        """
        logger.debug('Reading data from RS-232 connector: %s',
                     CONFIG['SERIAL_CONFIGS']['SERIAL_PORT'])

        # Read and append byte from serial port to parsing buffer
        read_data = self.serial_conn.read_byte()


        # Don't attempt to parse if end-of-sequence character not received
        if read_data != '\r':
            self.read_buffer.append(read_data)

        # Only parse if the end-of-sequence character was received
        else:
            try:
                # Attempts to parse current buffer
                logger.debug('Attempting to parse %s', ''.join(self.read_buffer))
                cmd, bank, port = self.kvm_parser.parse(''.join(self.read_buffer))

                logger.info('Successfully parsed sequence(s)')


                logger.debug('Running sequence %s %s %s', cmd, bank, port)

                # Retrieve OID using bank and port from sequence
                port_oid = self.get_bank_port_oid(bank, port)

                # Create SNMP command based on command from sequence
                match cmd:
                    case 'on':
                        self.snmp_cmd_issuer.set_port_on(port_oid,
                                                        self.target_ip,
                                                        self.target_port)
                    case 'of':
                        self.snmp_cmd_issuer.set_port_off(port_oid,
                                                        self.target_ip,
                                                        self.target_port)

                # Reset buffer to avoid re-parsing the same sequence twice
                # Note that we only do this if the parser successfully parsed a
                # sequence.
                self.read_buffer.clear()
                logger.debug('Cleared read buffer')

            # Errors will be raised when only a portion of the sequence has been
            # received and attempted to be parsed
            except ParseError:
                logger.warning('Parser failed to parse: %s',
                            ''.join(self.read_buffer))


if __name__ == '__main__':
    serial_listerner = SerialListener()
    serial_listerner.start_listening()

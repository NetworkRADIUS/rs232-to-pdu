"""
Contains wrapper class for pyserial to make a serial connection

Author: Patrick Guo
Date: 2024-08-23
"""
import serial
import sersnmplogging.loggingfactory as nrlogfac
from serial.serialutil import SerialException
import time
import os

LOG_FILE = './serialconnections.log'
LOG_NAME = 'Serial Connection'

# Set up logger for this module
logger = nrlogfac.create_logger(__name__)


ENCODING = 'utf-8'

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
                        xonxoff: bool = True) -> None:
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
            self.ser = serial.Serial(port=port, timeout=timeout, xonxoff=xonxoff)
            logger.info(('Serial port opened, device %s, baud %s, timeout %s, '
                         'Software Flow Control %s'),
                         port, baud, timeout, xonxoff)
            return not self.ser is None
        except SerialException as e:
            logger.info(('Serial port failed to open: device %s, baud%s, '
                          'timeout %s, Software Flow Control %s, Error: %s'),
                          port, baud, timeout, xonxoff, e)
            return False

    def read_all_waiting_bytes(self) -> str:
        """
        Reads all bytes waiting in the stream

        Args:
            None

        Returns:
            decoded string of bytes read
        """
        return self.ser.read(self.ser.in_waiting).decode(ENCODING)

    def close_connection(self):
        self.ser.close()

"""
Contains wrapper class for pyserial to make a serial connection

Author: Patrick Guo
Date: 2024-08-23
"""
import serial
import sersnmplogging.loggingfactory as nrlogfac


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
        self.ser = serial.Serial(port=port, timeout=timeout, xonxoff=xonxoff)
        logger.info(('Serial port opened, device %s, baud %s, timeout %s, '
                     'Software Flow Control %s'),
                     port, baud, timeout, xonxoff)

    def read_byte(self, num_bytes: int = 1) -> str:
        """
        Read number of bytes from connection

        Args:
            num_bytes (int): number of bytes to read from connection
        
        Returns:
            string of bytes read
        """
        bytes_read = self.ser.read(num_bytes)
        decoded_data = bytes_read.decode(ENCODING)
        return decoded_data

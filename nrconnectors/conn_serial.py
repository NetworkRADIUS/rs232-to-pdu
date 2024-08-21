import serial
import nrlogging.loggingfactory as nrlogfac


LOG_FILE = './serialconnections.log'
LOG_NAME = 'Serial Connection'

# Set up logger for this module
nrlogfac.setup_logging()
logger = nrlogfac.create_logger(__name__)


ENCODING = 'utf-8'

class SerialConnection:
    # We need software flow control (xonxoff) to be enabled
    def __init__(self, port=None, timeout=None, xonxoff=True):
        self.ser = serial.Serial(port=port, timeout=timeout)
    
    def write_to_serial(self, data: str):
        bytes_written = self.ser.write(data.encode(ENCODING))
        return bytes_written

    def read_byte(self, num_bytes=1):
        bytes_read = self.ser.read(num_bytes)
        decoded_data = bytes_read.decode(ENCODING)
        return decoded_data

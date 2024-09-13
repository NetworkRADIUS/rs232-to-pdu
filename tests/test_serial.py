import unittest
import asyncio
import subprocess
import os
import signal
import time

from serial.serialutil import SerialException
from sersnmpconnectors.conn_serial import SerialConnection
import serial

class TestSerialConn(unittest.TestCase):
    """
    Test cases for testing the serial connection
    """

    @classmethod
    def setUp(cls):
        """
        Creates the connector and event loop objects and connects to the port
        """
        cls.socat = subprocess.Popen(['socat', '-d', '-d', '-T', '1', 'pty,raw,echo=0,link=./ttyUSBCI0', 'pty,raw,echo=0,link=./ttyUSBCI1'])
        time.sleep(1)


        cls.ser_conn = SerialConnection()
        cls.ser_conn.make_connection('./ttyUSBCI0')


        cls.event_loop = asyncio.new_event_loop()

        cls.changed = False

    @classmethod
    def tearDown(cls):
        """
        Tear down of test case to close the event loop
        """
        cls.event_loop.close()
        if cls.socat.poll() is None:
            os.kill(cls.socat.pid, signal.SIGTERM)

            # wait until the socat process is successfully killed
            while cls.socat.poll() is None:
                pass

    def test_make_connection_success(self):
        """
        Test case for successfully making a connection with the serial port
        """
        self.assertIsInstance(self.ser_conn.ser, serial.Serial)

    async def write_to_port(self):
        """
        Async helper function for writing to the loopback device
        """
        subprocess.call('sudo sh -c \'echo -n "sest" > /dev/ttyUSBCI1\'', shell=True)

    async def dummy_wait(self, duration=5):
        """
        Async function to just wait and do nothing
        """
        await asyncio.sleep(duration)

    def test_connect_to_bad_port(self):
        """
        Test case for attempting to connect to a non-existing port
        """
        self.assertFalse(self.ser_conn.make_connection('/dev/doesNotExistTty'))

    def serial_port_error_handler(self, loop, context):
        """
        Event loop error handler
        """
        match type(context['exception']):
            case OSError:
                self.event_loop.remove_reader(self.ser_conn)
                self.ser_conn.close()
                self.changed = True

    def dummy_read(self):
        """
        Dummy function that occurs when port is ready to read
        """

    async def dummy_raise_os_exception(self):
        """
        Helper funciton to raise exception simulating a disconnected port
        """
        await asyncio.sleep(0)
        raise OSError()

    def test_error_handler_success(self):
        """
        Test case to ensure that the error handler is called
        """
        # sets up serial connection, reader event listener,
        # and exception handler
        self.ser_conn = serial.Serial('./ttyUSBCI0')
        self.event_loop.add_reader(self.ser_conn, self.dummy_read)
        self.event_loop.set_exception_handler(self.serial_port_error_handler)

        # kill the socat process
        os.kill(self.socat.pid, signal.SIGTERM)
        while self.socat.poll() is None:
            pass
        # why is it not throwing an error now that my port is gone :(

        # raise the exception
        self.event_loop.create_task(self.dummy_raise_os_exception())

        # wait for error handler to handle exception
        self.event_loop.run_until_complete(self.dummy_wait())

        # check that the error handler was called
        self.assertTrue(self.changed)

"""
rs232-to-pdu
Copyright (C) 2024 InkBridge Networks (legal@inkbridge.io)

rs232-to-pdu © 2024 by InkBridge is licensed under CC BY-NC 4.0. To view a copy
of this license, visit https://creativecommons.org/licenses/by-nc/4.0/
"""
import unittest
import asyncio
import subprocess
import os
import signal
import time

from serial.serialutil import SerialException
import serial

class TestSerialConn(unittest.TestCase):
    """
    Test cases for testing the serial connection
    """

    @classmethod
    def setUpClass(cls):
        """
        Creates the connector and event loop objects and connects to the port
        """
        cls.socat = subprocess.Popen( # pylint: disable=consider-using-with
            ['socat', '-d', '-d', '-T', '60',
             'pty,raw,echo=0,link=./ttyUSBCI0',
             'pty,raw,echo=0,link=./ttyUSBCI1']
        )

        time.sleep(1)

        cls.ser_conn_rd = serial.Serial('./ttyUSBCI0', xonxoff=True)
        cls.ser_conn_wr = serial.Serial('./ttyUSBCI1', xonxoff=True)
        cls.event_loop = asyncio.new_event_loop()
        cls.changed = False

    @classmethod
    def tearDownClass(cls):
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
        self.assertIsInstance(self.ser_conn_rd, serial.Serial)
        self.assertIsInstance(self.ser_conn_wr, serial.Serial)

    async def dummy_wait(self, duration=5):
        """
        Async function to just wait and do nothing
        """
        await asyncio.sleep(duration)

    def test_connect_to_bad_port(self):
        """
        Test case for attempting to connect to a non-existing port
        """
        self.assertRaises(
            SerialException,
            serial.Serial, './does_not_exist')

"""
Copyright (C) 2024 InkBridge Networks (legal@inkbridge.io)

This software may not be redistributed in any form without the prior
written consent of InkBridge Networks.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
SUCH DAMAGE.

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

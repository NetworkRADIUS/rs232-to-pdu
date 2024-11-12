"""
Test cases for the Rs232ToTripplite class
"""

import os
import signal
import subprocess
import time
import unittest
from unittest import mock

import serial
import pysnmp.hlapi.asyncio as pysnmp

from rs232_to_tripplite.device import Device
from rs232_to_tripplite.rs232tripplite import Rs2323ToTripplite # pylint: disable=import-error
from rs232_to_tripplite.transport.snmp import TransportSnmpV1V2


class TestConverter(unittest.TestCase):
    """
    Test cases for the Rs232ToTripplite class
    """
    @classmethod
    def setUpClass(cls):
        cls.socat = subprocess.Popen(  # pylint: disable=consider-using-with
            ['socat', '-d', '-d', '-T', '60',
             'pty,raw,echo=0,link=./ttyUSBCI0',
             'pty,raw,echo=0,link=./ttyUSBCI1'
             ]
        )

        # need to give socat a few moments to actually start
        time.sleep(1)

        cls.rs232_wr_dev = serial.Serial('./ttyUSBCI1')

    @classmethod
    def tearDownClass(cls):
        """
        Tear down of test case to close the event loop
        """
        if cls.socat.poll() is None:
            os.kill(cls.socat.pid, signal.SIGTERM)

            # wait until the socat process is successfully killed
            while cls.socat.poll() is None:
                pass


    def setUp(self):
        self.converter = Rs2323ToTripplite(
            './ttyUSBCI0', 10, 5, 5, 5,
            {
                '001': Device(
                    '001', ['001', '002'], {
                        'on': pysnmp.Integer(1),
                        'of': pysnmp.Integer(2),
                        'cy': pysnmp.Integer(3)
                    }, TransportSnmpV1V2(
                        {'001': '1.3.6.1',
                         '002': '1.3.6.2'},
                        1, '192.168.0.1', 161, 'public', 'private', 5, 5
                    )
                ),
                '002': Device(
                    '002', ['001', '002'], {
                        'on': pysnmp.Integer(1),
                        'of': pysnmp.Integer(2)
                    }, TransportSnmpV1V2(
                        {'001': '1.3.6.1',
                         '002': '1.3.6.2'},
                        1, '192.168.0.1', 161, 'public', 'private', 5, 5
                    )
                )
            }, 10, 5
        )
        self.converter.serial_conn_open()

    def tearDown(self):
        self.converter.serial_conn_close()

    @mock.patch('rs232_to_tripplite.rs232tripplite.Rs2323ToTripplite.'
                'power_change_enqueue')
    def test_converter_read_parse(self, mock_func):
        """
        Tests an end-to-end parsing from the Rs2323ToTripplite class
        Args:
            mock_func: mocking add_power_change_to_queue

        Returns:

        """
        self.rs232_wr_dev.write('on 1 1\r'.encode('utf-8'))
        # without sleep, by time we read, buffer is still empty (race cond)
        time.sleep(1)
        self.converter.serial_conn_read()
        mock_func.assert_called()
        mock_func.reset_mock()

        self.rs232_wr_dev.write('quit\r'.encode('utf-8'))
        time.sleep(1)
        self.converter.serial_conn_read()
        mock_func.assert_not_called()
        mock_func.reset_mock()

        self.rs232_wr_dev.write('\r'.encode('utf-8'))
        time.sleep(1)
        self.converter.serial_conn_read()
        mock_func.assert_not_called()
        mock_func.reset_mock()

        self.rs232_wr_dev.write('bad input\r'.encode('utf-8'))
        time.sleep(1)
        self.converter.serial_conn_read()
        mock_func.assert_not_called()
        mock_func.reset_mock()

        # non-existent outlet should not fail HERE because the check for
        # outlets is abstracted to be elsewhere
        self.rs232_wr_dev.write('on 1 10\r'.encode('utf-8'))
        time.sleep(1)
        self.converter.serial_conn_read()
        mock_func.assert_called()
        mock_func.reset_mock()

        # non-existent device should fail as converter should not be able to
        # find device in its list
        self.rs232_wr_dev.write('on 10 1\r'.encode('utf-8'))
        time.sleep(1)
        self.assertRaises(
            KeyError,
            self.converter.serial_conn_read
        )

    def test_power_states(self):
        """
        Tests end-to-end with power options
        Returns:

        """
        with mock.patch('rs232_to_tripplite.rs232tripplite.Rs2323ToTripplite.'
                        'power_change_enqueue') as mock_func:

            self.rs232_wr_dev.write('cy 1 1\r'.encode('utf-8'))
            time.sleep(1)
            self.converter.serial_conn_read()
            mock_func.assert_called()
            mock_func.reset_mock()

            # device 2 does not have a cycle power option
            self.rs232_wr_dev.write('cy 2 1\r'.encode('utf-8'))
            time.sleep(1)
            self.converter.serial_conn_read()
            # In theory, should be called twice, but because we wrapped it in
            # a coroutine (and we never started the event loop), will never be
            # called
            mock_func.assert_not_called()
            mock_func.reset_mock()

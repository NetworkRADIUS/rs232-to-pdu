import unittest
import asyncio

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
        cls.ser_conn = SerialConnection()
        cls.ser_conn.make_connection('/dev/ttyUSBCI0')

        cls.event_loop = asyncio.new_event_loop()
    
    @classmethod
    def tearDown(cls):
        """
        Tear down of test case to close the event loop
        """
        cls.event_loop.close()

    def test_make_connection_success(self):
        """
        Test case for successfully making a connection with the serial port
        """
        self.assertIsInstance(self.ser_conn.ser, serial.Serial)

    def test_read_all_waiting_bytes_success(self):
        """
        Test case to make the connector can read all waiting bytes from port
        """
        
        self.event_loop.add_reader(self.ser_conn.ser, self.read_all_waiting)
        self.event_loop.run_forever()

    def read_all_waiting(self):
        self.assertEqual(self.ser_conn.read_all_waiting_bytes(), 'Test')
        self.event_loop.stop()

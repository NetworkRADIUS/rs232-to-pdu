"""
rs232-to-pdu
Copyright (C) 2024 InkBridge Networks (legal@inkbridge.io)

rs232-to-pdu © 2024 by InkBridge is licensed under CC BY-NC 4.0. To view a copy
of this license, visit https://creativecommons.org/licenses/by-nc/4.0/
"""
import asyncio
import unittest
from unittest import mock
import pysnmp.hlapi.asyncio as pysnmp


from rs232_to_pdu.device import Device # pylint: disable=import-error
from rs232_to_pdu.transport.snmp import TransportSnmpV1V2, TransportSnmpV3 # pylint: disable=import-error, line-too-long


class TestSnmpTransport(unittest.TestCase):
    """
    Unit tests for the Snmp Transport classes
    """
    @classmethod
    def setUpClass(cls):
        cls.v1v2_transport = TransportSnmpV1V2(
            {'001':'1.1', '002':'1.2', '003':'1.3'}, 1,
            '127.0.0.1', 161, 'public', 'private', 1, 1
        )
        cls.v1v2_device = Device(
            'v1v2', ['001', '002', '003'],
            {'on': pysnmp.Integer(1), 'of': pysnmp.Integer(2)},
            cls.v1v2_transport
        )

        cls.v3_transport = TransportSnmpV3(
            {'001': '1.1', '002': '1.2', '003': '1.3'}, 3,
            '127.0.0.1', 161, 'username', 'SHA', '<PASSWORD>', 'AES',
            '<PASSWORD>', 'authPriv', 1, 1
        )
        cls.v3_device = Device(
            'v3', ['001', '002', '003'],
            {'on': pysnmp.Integer(1), 'of': pysnmp.Integer(2),
             'cy': pysnmp.Integer(3)},
            cls.v3_transport
        )

        cls.event_loop = asyncio.new_event_loop()

    @mock.patch("pysnmp.hlapi.asyncio.getCmd")
    def test_get_outlet_state(self, mock_get_cmd):
        """
        tests getting outlet states
        Args:
            mock_get_cmd: mocking pysnmp.getCmd

        Returns:

        """
        # Mock successful command
        mock_get_cmd.return_value = (None, None, None, None)

        self.assertEqual(
            asyncio.run(self.v1v2_device.transport.outlet_state_get('001')),
            True
        )
        self.assertEqual(
            asyncio.run(self.v1v2_device.transport.outlet_state_get('002')),
            True
        )

        # Non-existent outlet
        self.assertRaises(
            KeyError,
            asyncio.run, self.v1v2_device.transport.outlet_state_get('004')
        )

        # Mock SNMP engine error
        mock_get_cmd.return_value = (True, None, None, None)
        self.assertEqual(
            asyncio.run(self.v1v2_device.transport.outlet_state_get('001')),
            False
        )
        self.assertEqual(
            asyncio.run(self.v1v2_device.transport.outlet_state_get('002')),
            False
        )

        # Non-existent outlet
        self.assertRaises(
            KeyError,
            asyncio.run, self.v1v2_device.transport.outlet_state_get('004')
        )

        # Mock SNMP PDU error
        mock_get_cmd.return_value = (None, True, None, None)
        self.assertEqual(
            asyncio.run(self.v1v2_device.transport.outlet_state_get('001')),
            False
        )
        self.assertEqual(
            asyncio.run(self.v1v2_device.transport.outlet_state_get('002')),
            False
        )

        # Non-existent outlet
        self.assertRaises(
            KeyError,
            asyncio.run, self.v1v2_device.transport.outlet_state_get('004')
        )

    @mock.patch("pysnmp.hlapi.asyncio.setCmd")
    def test_set_outlet_state(self, mock_set_cmd):
        """
        tests setting outlet states
        Args:
            mock_set_cmd: mocking pysnmp.setCmd

        Returns:

        """
        # Mock successful command
        mock_set_cmd.return_value = (None, None, None, None)

        self.assertEqual(
            asyncio.run(self.v1v2_device.transport.outlet_state_set('001', 'on')),
            True
        )
        self.assertEqual(
            asyncio.run(self.v1v2_device.transport.outlet_state_set('002', 'on')),
            True
        )

        # Non-existent outlet
        self.assertRaises(
            KeyError,
            asyncio.run, self.v1v2_device.transport.outlet_state_set('004', 'on')
        )

        # Mock SNMP engine error
        mock_set_cmd.return_value = (True, None, None, None)
        self.assertEqual(
            asyncio.run(self.v1v2_device.transport.outlet_state_set('001', 'on')),
            False
        )
        self.assertEqual(
            asyncio.run(self.v1v2_device.transport.outlet_state_set('002', 'on')),
            False
        )

        # Non-existent outlet
        self.assertRaises(
            KeyError,
            asyncio.run, self.v1v2_device.transport.outlet_state_set('004', 'on')
        )

        # Mock SNMP PDU error
        mock_set_cmd.return_value = (None, True, None, None)
        self.assertEqual(
            asyncio.run(self.v1v2_device.transport.outlet_state_set('001', 'on')),
            False
        )
        self.assertEqual(
            asyncio.run(self.v1v2_device.transport.outlet_state_set('002', 'on')),
            False
        )

        # Non-existent outlet
        self.assertRaises(
            KeyError,
            asyncio.run, self.v1v2_device.transport.outlet_state_set('004', 'on')
        )

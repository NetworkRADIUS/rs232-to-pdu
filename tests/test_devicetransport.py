import asyncio
import unittest
from unittest import mock


from rs232_to_tripplite.device import Device
from rs232_to_tripplite.transport.snmp import TransportSnmpV1V2, \
    TransportSnmpV3


class TestSnmpTransport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v1v2_transport = TransportSnmpV1V2(
            {'001':'1.1', '002':'1.2', '003':'1.3'}, 1,
            '127.0.0.1', 161, 'public', 'private'
        )
        cls.v1v2_device = Device(
            'v1v2', ['001', '002', '003'], cls.v1v2_transport
        )

        cls.v3_transport = TransportSnmpV3(
            {'001': '1.1', '002': '1.2', '003': '1.3'}, 3,
            '127.0.0.1', 161, 'username', 'SHA', '<PASSWORD>', 'AES',
            '<PASSWORD>', 'authPriv'
        )
        cls.v3_device = Device(
            'v3', ['001', '002', '003'], cls.v3_transport
        )

        cls.event_loop = asyncio.new_event_loop()

    @mock.patch("pysnmp.hlapi.asyncio.getCmd")
    def test_get_outlet_state(self, mock_getCmd):
        # Mock successful command
        mock_getCmd.return_value = (None, None, None, None)

        self.assertEqual(
            asyncio.run(self.v1v2_device.get_outlet_state('001')),
            (True, (None, None, None, None))
        )
        self.assertEqual(
            asyncio.run(self.v1v2_device.get_outlet_state('002')),
            (True, (None, None, None, None))
        )

        # Non-existent outlet
        self.assertRaises(
            KeyError,
            asyncio.run, self.v1v2_device.get_outlet_state('004')
        )

        # Mock SNMP engine error
        mock_getCmd.return_value = (True, None, None, None)
        self.assertEqual(
            asyncio.run(self.v1v2_device.get_outlet_state('001')),
            (False, (True, None, None, None))
        )
        self.assertEqual(
            asyncio.run(self.v1v2_device.get_outlet_state('002')),
            (False, (True, None, None, None))
        )

        # Non-existent outlet
        self.assertRaises(
            KeyError,
            asyncio.run, self.v1v2_device.get_outlet_state('004')
        )

        # Mock SNMP PDU error
        mock_getCmd.return_value = (None, True, None, None)
        self.assertEqual(
            asyncio.run(self.v1v2_device.get_outlet_state('001')),
            (False, (None, True, None, None))
        )
        self.assertEqual(
            asyncio.run(self.v1v2_device.get_outlet_state('002')),
            (False, (None, True, None, None))
        )

        # Non-existent outlet
        self.assertRaises(
            KeyError,
            asyncio.run, self.v1v2_device.get_outlet_state('004')
        )

    @mock.patch("pysnmp.hlapi.asyncio.setCmd")
    def test_set_outlet_state(self, mock_setCmd):
        # Mock successful command
        mock_setCmd.return_value = (None, None, None, None)

        self.assertEqual(
            asyncio.run(self.v1v2_device.set_outlet_state('001', 'on')),
            (True, (None, None, None, None))
        )
        self.assertEqual(
            asyncio.run(self.v1v2_device.set_outlet_state('002', 'on')),
            (True, (None, None, None, None))
        )

        # Non-existent outlet
        self.assertRaises(
            KeyError,
            asyncio.run, self.v1v2_device.set_outlet_state('004', 'on')
        )

        # Mock SNMP engine error
        mock_setCmd.return_value = (True, None, None, None)
        self.assertEqual(
            asyncio.run(self.v1v2_device.set_outlet_state('001', 'on')),
            (False, (True, None, None, None))
        )
        self.assertEqual(
            asyncio.run(self.v1v2_device.set_outlet_state('002', 'on')),
            (False, (True, None, None, None))
        )

        # Non-existent outlet
        self.assertRaises(
            KeyError,
            asyncio.run, self.v1v2_device.set_outlet_state('004', 'on')
        )

        # Mock SNMP PDU error
        mock_setCmd.return_value = (None, True, None, None)
        self.assertEqual(
            asyncio.run(self.v1v2_device.set_outlet_state('001', 'on')),
            (False, (None, True, None, None))
        )
        self.assertEqual(
            asyncio.run(self.v1v2_device.set_outlet_state('002', 'on')),
            (False, (None, True, None, None))
        )

        # Non-existent outlet
        self.assertRaises(
            KeyError,
            asyncio.run, self.v1v2_device.set_outlet_state('004', 'on')
        )


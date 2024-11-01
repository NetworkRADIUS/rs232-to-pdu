import yaml

#pylint: disable=missing-module-docstring

import unittest
from rs232_to_tripplite.device import create_device_from_config_dict, Device

from rs232_to_tripplite.device import FactoryDevice  # pylint: disable=import-error
from rs232_to_tripplite.transport.base import Transport  # pylint: disable=import-error


class TransportDummy(Transport):
    """
    Dummy Transport class for testing purposes
    """
    async def outlet_state_get(self, outlet):  # pylint: disable=missing-function-docstring,unused-argument
        return None

    async def outlet_state_set(self, outlet, state):  # pylint: disable=missing-function-docstring,unused-argument
        return None

class TestDevice(unittest.TestCase):
    """
    Contains test cases for the Device class and FactoryDevice class
    """
    def setUp(self):
        self.factory_device = FactoryDevice()
        self.device_config = {
            'snmp': {
                'v1': {
                    'public_community': 'public',
                    'private_community': 'private',
                },
                'ip_address': '127.0.0.1',
                'port': 161
            },
            'outlets': {
                '001': '1.1',
                '002': '1.2',
            }
        }

    def test_factory_device(self):
        """
        Tests the FactoryDevice class at instantiating Device objects
        Returns:

        """
        self.factory_device.transport_handlers = {
            'test_transport': lambda c, o: TransportDummy(o)
        }
        test_config = {
            'test_transport': {
                'devices': {
                    'custom': {
                        'test_device_2': {
                            '001': '1.1'
                        }
                    },
                    "path": "."}
            },
            'devices': {
                'device1': {
                    'test_transport': {},
                    'outlets': 'test_device',
                    'power_states': {
                        'on': 1,
                        'of': 2
                    }
                },
                'device2': {
                    'test_transport': {},
                    'outlets': 'test_device_2',
                    'power_states': {
                        'on': 1,
                        'of': 2
                    }
                }
            },
            'power_states': {
                'cy_delay': 5
            }
        }
        result = self.factory_device.devices_from_full_config(test_config)
        self.assertEqual(list(result.keys()), ['device1', 'device2'])
        self.assertEqual(result['device1'].name, 'device1')
        self.assertEqual(result['device2'].name, 'device2')

        self.assertEqual(result['device1'].transport.outlets['001'], '1.1.1')
        self.assertEqual(result['device2'].transport.outlets['001'], '1.1')


    def test_name_sanitization(self):
        """
        Tests the name sanitization function
        Returns:

        """
        func = self.factory_device._FactoryDevice__sanitized  # pylint: disable=protected-access

        self.assertTrue(func('aaaa'))
        self.assertTrue(func('aaaa-bbbb'))
        self.assertTrue(func('aaaa-BBBB'))
        self.assertTrue(func('a1B1'))
        self.assertTrue(func('a_b'))

        self.assertFalse(func('a.b'))
        self.assertFalse(func('a!'))
        self.assertFalse(func('#notB'))
        self.assertFalse(func('a_b_'))
        self.assertFalse(func('_a_b'))

    def test_device_instantiation(self):
        self.device_config['power_options'] = {'of':1, 'on':2, 'cy':3}
        self.assertIsInstance(
            create_device_from_config_dict('int_all', self.device_config),
            Device
        )

        self.device_config['power_options'] = {'of':1, 'on':2}
        self.assertIsInstance(
            create_device_from_config_dict('int_no_cy', self.device_config),
            Device
        )

        self.device_config['power_options'] = {'of':'1', 'on':'2', 'cy':'3'}
        self.assertIsInstance(
            create_device_from_config_dict('str_all', self.device_config),
            Device
        )

        self.device_config['power_options'] = {'of':'1', 'on':'2'}
        self.assertIsInstance(
            create_device_from_config_dict('str_no_cy', self.device_config),
            Device
        )

        self.device_config['power_options'] = {1:'1'}
        self.assertRaises(
            TypeError,
            create_device_from_config_dict, 'bad_type', self.device_config
        )

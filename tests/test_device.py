#pylint: disable=missing-module-docstring

import unittest

from rs232_to_tripplite.device import FactoryDevice  # pylint: disable=import-error
from rs232_to_tripplite.transport.base import Transport  # pylint: disable=import-error


class TransportDummy(Transport):
    """
    Dummy Transport class for testing purposes
    """
    async def get_outlet_state(self, outlet):  # pylint: disable=missing-function-docstring,unused-argument
        return None

    async def set_outlet_state(self, outlet, state):  # pylint: disable=missing-function-docstring,unused-argument
        return None

class TestDevice(unittest.TestCase):
    """
    Contains test cases for the Device class and FactoryDevice class
    """
    def setUp(self):
        self.factory_device = FactoryDevice()

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

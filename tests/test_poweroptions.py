# pylint: disable=missing-module-docstring
import unittest

from rs232_to_tripplite.device import Device, \
    FactoryDevice  # pylint: disable=import-error
from rs232_to_tripplite.transport.base import \
    Transport  # pylint: disable=import-error


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
    @classmethod
    def setUpClass(cls):
        cls.factory = FactoryDevice()

    def setUp(self):
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

    def test_power_states(self):
        """
        Tests instantiation of a device with various power options
        Returns:

        """
        self.factory.configs = {
            'snmp': {
                'retry': {
                    'timeout': 5,
                    'max_attempts': 5
                }
            }
        }

        self.device_config['power_states'] = {'of':1, 'on':2, 'cy':3}
        self.assertIsInstance(
            self.factory._FactoryDevice__device_from_device_config(  # pylint: disable=protected-access
                'int_all', self.device_config
            ),
            Device
        )

        self.device_config['power_states'] = {'of':1, 'on':2}
        self.assertIsInstance(
            self.factory._FactoryDevice__device_from_device_config(  # pylint: disable=protected-access
                'int_no_cy', self.device_config
            ),
            Device
        )

        self.device_config['power_states'] = {'of':'1', 'on':'2', 'cy':'3'}
        self.assertIsInstance(
            self.factory._FactoryDevice__device_from_device_config(  # pylint: disable=protected-access
                'str_all', self.device_config
            ),
            Device
        )

        self.device_config['power_states'] = {'of':'1', 'on':'2'}
        self.assertIsInstance(
            self.factory._FactoryDevice__device_from_device_config(  # pylint: disable=protected-access
                'str_no_cy', self.device_config
            ),
            Device
        )

        self.device_config['power_states'] = {1:'1'}
        self.assertRaises(
            TypeError,
            self.factory._FactoryDevice__device_from_device_config,  # pylint: disable=protected-access
            'bad_type', self.device_config
        )

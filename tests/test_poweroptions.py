# pylint: disable=missing-module-docstring
import unittest

from rs232_to_tripplite.device import FactoryDevice, Device # pylint: disable=import-error


class TestPowerOptions(unittest.TestCase):
    """
    Test cases pertaining to power options
    """
    def setUp(self):
        self.factory = FactoryDevice()
        self.configs = {
            'snmp': {
                'retry': {
                    'timeout': 5,
                    'max_attempts': 5
                }
            },
            'devices': {
                '001': {
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
            }
        }

    def test_device_instantiation(self):
        """
        Tests instantiation of a device with various power options
        Returns:

        """
        self.configs['devices']['001']['power_states'] = {'of':1, 'on':2, 'cy':3}
        self.assertIsInstance(
            self.factory.devices_from_configs(self.configs)['001'],
            Device
        )

        self.configs['devices']['001']['power_states'] = {'of':1, 'on':2}
        self.assertIsInstance(
            self.factory.devices_from_configs(self.configs)['001'],
            Device
        )

        self.configs['devices']['001']['power_states'] = {'of':'1', 'on':'2', 'cy':'3'}
        self.assertIsInstance(
            self.factory.devices_from_configs(self.configs)['001'],
            Device
        )

        self.configs['devices']['001']['power_states'] = {'of':'1', 'on':'2'}
        self.assertIsInstance(
            self.factory.devices_from_configs(self.configs)['001'],
            Device
        )

        self.configs['devices']['001']['power_states'] = {1:'1'}
        self.assertRaises(
            TypeError,
            self.factory.devices_from_configs, self.configs
        )

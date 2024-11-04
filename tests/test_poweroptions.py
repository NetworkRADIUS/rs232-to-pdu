# pylint: disable=missing-module-docstring
import unittest

from rs232_to_tripplite.device import device_from_config, Device # pylint: disable=import-error


class TestPowerOptions(unittest.TestCase):
    """
    Test cases pertaining to power options
    """
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

    def test_device_instantiation(self):
        """
        Tests instantiation of a device with various power options
        Returns:

        """
        self.device_config['power_states'] = {'of':1, 'on':2, 'cy':3}
        self.assertIsInstance(
            device_from_config('int_all', self.device_config),
            Device
        )

        self.device_config['power_states'] = {'of':1, 'on':2}
        self.assertIsInstance(
            device_from_config('int_no_cy', self.device_config),
            Device
        )

        self.device_config['power_states'] = {'of':'1', 'on':'2', 'cy':'3'}
        self.assertIsInstance(
            device_from_config('str_all', self.device_config),
            Device
        )

        self.device_config['power_states'] = {'of':'1', 'on':'2'}
        self.assertIsInstance(
            device_from_config('str_no_cy', self.device_config),
            Device
        )

        self.device_config['power_states'] = {1:'1'}
        self.assertRaises(
            TypeError,
            device_from_config, 'bad_type', self.device_config
        )

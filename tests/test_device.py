"""
rs232-to-pdu
Copyright (C) 2024 InkBridge Networks (legal@inkbridge.io)

rs232-to-pdu © 2024 by InkBridge is licensed under CC BY-NC 4.0. To view a copy
of this license, visit https://creativecommons.org/licenses/by-nc/4.0/
"""
import unittest

from rs232_to_pdu.device import FactoryDevice, Device # pylint: disable=import-error


class TestDevice(unittest.TestCase):
    """
    Test cases pertaining to the Device and FactoryDevice class
    """
    def setUp(self):
        self.factory = FactoryDevice()
        self.configs = {
            'snmp': {
                'retry': {
                    'timeout': 5,
                    'max_attempts': 5
                },
                'devices': {
                    'custom': {}
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
                    'device': {
                        'outlets': {
                            '001': '1.1',
                            '002': '1.2',
                        },
                        'power_states': {
                            'on': 1,
                            'of': 2
                        }
                    }
                }
            }
        }

    def test_power_options(self):
        """
        Tests instantiation of a device with various power options
        Returns:

        """
        self.configs['devices']['001']['device']['power_states'] = {'of':1, 'on':2, 'cy':3}
        self.assertIsInstance(
            self.factory.devices_from_configs(self.configs)['001'],
            Device
        )

        self.configs['devices']['001']['device']['power_states'] = {'of':1, 'on':2}
        self.assertIsInstance(
            self.factory.devices_from_configs(self.configs)['001'],
            Device
        )

        self.configs['devices']['001']['device']['power_states'] = {'of':'1', 'on':'2', 'cy':'3'}
        self.assertIsInstance(
            self.factory.devices_from_configs(self.configs)['001'],
            Device
        )

        self.configs['devices']['001']['device']['power_states'] = {'of':'1', 'on':'2'}
        self.assertIsInstance(
            self.factory.devices_from_configs(self.configs)['001'],
            Device
        )

        self.configs['devices']['001']['device']['power_states'] = {1:'1'}
        self.assertRaises(
            TypeError,
            self.factory.devices_from_configs, self.configs
        )

    def test_template_names(self):
        """
        Tests the template name sanitization feature
        """
        template = {
            '001': '1.3.6.1',
            '002': '1.3.6.2'
        }

        names_valid = ['baz/foo', 'baz/qux/foo_bar', 'baz/qux/foo-bar']
        for name in names_valid:
            with self.subTest(name=name):
                self.configs['devices']['001']['outlets'] = name
                self.configs['snmp']['devices']['custom'][name] = template
                self.assertIsInstance(
                    self.factory.devices_from_configs(self.configs)['001'],
                    Device
                )

        names_invalid = ['foo.bar', 'foo-', 'foo_', '-foo', '_foo', 'foo,bar',
                         'foo']
        for name in names_invalid:
            with self.subTest(name=name):
                self.configs['devices']['001']['device'] = name
                self.configs['snmp']['devices']['custom'][name] = template
                self.assertRaises(
                    ValueError,
                    self.factory.devices_from_configs, self.configs
                )

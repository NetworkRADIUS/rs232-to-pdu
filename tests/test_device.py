"""
Copyright (C) 2024 InkBridge Networks (legal@inkbridge.io)

This software may not be redistributed in any form without the prior
written consent of InkBridge Networks.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
SUCH DAMAGE.
"""
import unittest

from rs232_to_tripplite.device import FactoryDevice, Device # pylint: disable=import-error


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

        names_valid = ['foo', 'foo_bar', 'foo-bar']
        for name in names_valid:
            with self.subTest(name=name):
                self.configs['devices']['001']['outlets'] = name
                self.configs['snmp']['devices']['custom'][name] = template
                self.assertIsInstance(
                    self.factory.devices_from_configs(self.configs)['001'],
                    Device
                )

        names_invalid = ['foo.bar', 'foo-', 'foo_', '-foo', '_foo', 'foo,bar']
        for name in names_invalid:
            with self.subTest(name=name):
                self.configs['devices']['001']['device'] = name
                self.configs['snmp']['devices']['custom'][name] = template
                self.assertRaises(
                    ValueError,
                    self.factory.devices_from_configs, self.configs
                )

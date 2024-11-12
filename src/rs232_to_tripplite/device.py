"""
Contains Device class meant to model a target device.

Each device must have a name, a list of outlets, and a transport method
"""
import pathlib
import re
from dataclasses import dataclass

import pysnmp.hlapi.asyncio as pysnmp
import yaml

from rs232_to_tripplite.transport.base import Transport
from rs232_to_tripplite.transport.snmp import TransportSnmpV1V2, \
    TransportSnmpV3


@dataclass
class Device:
    """
    simple class containing the attributes needed to represent a device

    attrs:
        name: the name of the device (should be unique(
        outlets: list of outlet names that this device is able to control
        power_options: a dict mapping power options in string to their corresponding values
        transport: the transport used by the device to send commands
    """
    name: str
    outlets: list[str]
    power_states: dict[str: any]
    transport: Transport


class FactoryDevice:
    def __init__(self):
        self.transport_handlers = {
            'snmp': self.transport_snmp
        }

        self.templates = {}
        self.configs = None
        self.curr_transport = None

        self.template_name_pattern = re.compile(r'^[a-zA-Z0-9]+([-_][a-zA-Z0-9]+)*$')

    def transport_snmp(self, configs: dict, outlets):
        transport = None

        ip_address = configs['ip_address']
        port = configs['port']

        versions = {
            'v1': 1,
            'v2': 2,
            'v3': 3
        }
        for version, vnum in versions.items():
            if version not in configs:
                continue

            match version:
                # both v1 and v2 use communities, thus combine them
                case 'v1' | 'v2':
                    public_community = configs[version]['public_community']
                    private_community = configs[version][
                        'private_community']

                    transport = TransportSnmpV1V2(
                        outlets, vnum, ip_address, port,
                        public_community, private_community,
                        self.configs['snmp']['retry']['timeout'],
                        self.configs['snmp']['retry']['max_attempts']
                    )
                case 'v3':
                    user = configs['v3']['user']
                    auth_protocol = configs['v3']['auth_protocol']
                    auth_passphrase = configs['v3']['auth_passphrase']
                    priv_protocol = configs['v3']['priv_protocol']
                    priv_passphrase = configs['v3']['priv_passphrase']
                    security_level = configs['v3']['security_level']

                    transport = TransportSnmpV3(
                        outlets, vnum, ip_address, port,
                        user, auth_protocol, auth_passphrase,
                        priv_protocol, priv_passphrase,
                        security_level,
                        self.configs['snmp']['retry']['timeout'],
                        self.configs['snmp']['retry']['max_attempts']
                    )

        # either no version found or version not supported
        if transport is None:
            raise AttributeError('Unsupported SNMP authentication schemes')

        return transport

    def devices_from_configs(self, configs: dict):
        self.configs = configs

        devices = {}
        for device, config in configs['devices'].items():
            self.curr_transport = None

            power_states = configs['devices'][device]['power_states']
            for option, value in power_states.items():
                if not isinstance(option, str):
                    raise TypeError('Power option must be a string')
                power_states[option] = pysnmp.Integer(value)

            for transport in self.transport_handlers:
                if transport in configs['devices'][device]:
                    self.curr_transport = transport

            outlets = configs['devices'][device]['outlets']
            if isinstance(outlets, str):
                if not bool(self.template_name_pattern.match(outlets)):
                    raise ValueError(f'Invalid template name detected for '
                                     f'device {device}')

                if outlets in self.configs[self.curr_transport]['devices']['custom']:
                    self.templates[outlets] = self.configs[self.curr_transport]['devices']['custom'][outlets]
                else:
                    device_path = pathlib.Path(
                        self.configs[self.curr_transport]['devices']['path'],
                        f'{outlets}.yaml'
                    )
                    with open(device_path, 'r', encoding='utf-8') as fileopen:
                        self.templates[outlets] = yaml.load(fileopen,
                                                           Loader=yaml.FullLoader)

                # read from cached templates
                outlets = self.templates[outlets]
            devices[device] = Device(
                device, list(outlets.keys()), power_states,
                self.transport_handlers[self.curr_transport](
                    configs['devices'][device][self.curr_transport], outlets
                )
            )
        return devices

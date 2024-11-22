"""
rs232-to-pdu
Copyright (C) 2024 InkBridge Networks (legal@inkbridge.io)

rs232-to-pdu © 2024 by InkBridge is licensed under CC BY-NC 4.0. To view a copy
of this license, visit https://creativecommons.org/licenses/by-nc/4.0/

Contains Device class meant to model a target device.

Each device must have a name, a list of outlets, and a transport method
"""
import pathlib
import re
from dataclasses import dataclass

import pysnmp.hlapi.asyncio as pysnmp
import yaml

from rs232_to_pdu.transport.base import Transport
from rs232_to_pdu.transport.snmp import TransportSnmpV1V2, \
    TransportSnmpV3, TransportSnmp


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
    """
    Factory class to create devices
    """

    def __init__(self):
        self.transport_handlers = {
            'snmp': self.transport_snmp
        }

        self.templates = {}
        self.configs = None

        self.template_name_pattern = re.compile(
            r'^([a-zA-Z0-9]+/)+[a-zA-Z0-9]+([-_][a-zA-Z0-9]+)*$'
        )

    def transport_snmp(  # pylint: disable=too-many-locals
            self, configs: dict, outlets: dict[str: any]
    ) -> TransportSnmp:
        """
        creates snmp transport from config

        Args:
            configs: dict containing transport configs
            outlets: dict containing outlet configs

        Returns:
            SNMP transport
        """
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

    def devices_from_configs(self, configs: dict) -> dict[str: Device]:
        """
        creates list of devices from configs
        Args:
            configs: entire config containing devices and relevant details

        Returns:

        """
        self.configs = configs

        devices = {}
        for name, config in configs['devices'].items():
            transport_type = None

            for transport in self.transport_handlers:
                if transport in config:
                    transport_type = transport

            if transport_type is None:
                raise ValueError(f'Missing or unsupported transport for '
                                 f'device {name}')

            device = config['device']
            if isinstance(device, str):
                if not bool(self.template_name_pattern.match(device)):
                    raise ValueError(f'Invalid template name detected for '
                                     f'device {device}')

                # load template if not already cached
                if device not in self.templates:
                    # load from internal config.yaml
                    if 'custom' in self.configs[transport_type]['devices']:
                        if device in self.configs[transport_type]['devices'][
                            'custom']:  # pylint: disable=line-too-long
                            self.templates[device] = \
                            self.configs[transport_type]['devices']['custom'][
                                device]  # pylint: disable=line-too-long

                        # load from external file
                    else:
                        template_path = pathlib.Path(
                            self.configs[transport_type]['devices']['path'],
                            f'{device}.yaml'
                        )
                        with open(template_path, 'r',
                                  encoding='utf-8') as fileopen:
                            self.templates[device] = yaml.load(
                                fileopen, Loader=yaml.FullLoader
                            )

                device = self.templates[device]

            power_states = device['power_states']
            for option, value in power_states.items():
                if not isinstance(option, str):
                    raise TypeError('Power option must be a string')
                power_states[option] = pysnmp.Integer(value)

            devices[name] = Device(
                name, list(device['outlets'].keys()), power_states,
                self.transport_handlers[transport_type](
                    config[transport_type], device['outlets']
                )
            )
        return devices

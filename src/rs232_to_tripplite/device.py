"""
Contains Device class meant to model a target device.

Each device must have a name, a list of outlets, and a transport method
"""
import os
import pathlib
import re

import pysnmp.hlapi.asyncio as pysnmp
import yaml


from rs232_to_tripplite.transport.base import Transport
from rs232_to_tripplite.transport.snmp import TransportSnmpV1V2, \
    TransportSnmpV3, TransportSnmp


class Device:
    """
    Class representing a Device with controllable outlets
    """

    def __init__(
            self,
            name: str, outlets: list[str], power_states: dict[str: any],
            transport: Transport
    ):
        """

        Args:
            name: device name
            outlets: list of outlet names
            power_states: mappings of power options to values
            transport: object for sending requests
        """
        self.name = name
        self.outlets = outlets
        self.power_states = power_states
        self.transport = transport

    async def outlet_state_get(self, outlet: str) -> tuple[bool, any]:
        """
        method for retrieving an outlet's state using the transport
        Args:
            outlet: string representation of outlet

        Returns:
            outlet state
        """
        return await self.transport.outlet_state_get(outlet)

    async def outlet_state_set(self, outlet: str, state: str) -> tuple[
        bool, any]:
        """
        method for setting an outlet's state using the transport'
        Args:
            outlet: string representation of outlet
            state: desired outlet state

        Returns:
            outlet state after sending the request
        """
        if state not in self.power_states:
            raise AttributeError(f'Attempting to set device {self.name} '
                                 f'outlet {outlet} to unknown state {state}.')

        return await self.transport.outlet_state_set(outlet,
                                                     self.power_states[state])


def snmp_transport_from_dict(configs: dict, outlets: dict) -> TransportSnmp:  # pylint: disable=too-many-locals
    """
    creates TransportSnmp object from dictionary

    Args:
        configs: config dict
        outlets: mapping of outlet name to OID

    Returns:
        TransportSnmp object
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
        if version in configs:
            # if transport has already been over-writen, multiple schemes have
            # been listed
            if transport is not None:
                raise ValueError('Multiple SNMP authentication schemes found')

            match version:
                # both v1 and v2 use communities, thus combine them
                case 'v1' | 'v2':
                    public_community = configs[version]['public_community']
                    private_community = configs[version]['private_community']

                    transport = TransportSnmpV1V2(
                        outlets, vnum, ip_address, port,
                        public_community, private_community
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
                        security_level
                    )

    # either no version found or version not supported
    if transport is None:
        raise AttributeError('Unsupported SNMP authentication schemes')

    return transport

class FactoryDevice:  # pylint: disable=too-few-public-methods
    """
    Factory class for creating Device objects
    """
    def __init__(self):
        self.transport_handlers = {
            'snmp': snmp_transport_from_dict
        }

        self.name_pattern = re.compile(r'^[a-zA-Z0-9]+([-,_][a-zA-Z0-9]+)*$')

        self.configs = None

        # attribute holding the current device's transport
        # used when iterating through all the devices in the config
        self.curr_device_transport = None

    def __template_from_config(self, device: str) -> dict:
        """
        finds template for given device name

        Args:
            device: device name in string

        Returns:
            dictionary containing template outlets
        """
        if device in self.configs[self.curr_device_transport]['devices']['custom']:
            return self.configs[self.curr_device_transport]['devices']['custom'][device]

        template_path = pathlib.Path(
            self.configs[self.curr_device_transport]['devices']['path'], f'{device}.yaml'
        )
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as file:
                return yaml.load(file, Loader=yaml.FullLoader)

        raise ValueError(
            f'No template found for device {device} with transport '
            f'{self.curr_device_transport}')

    def devices_from_full_config(self, configs: dict) -> dict[str: Device]:
        """
        creates dict of Device objects from config

        Args:
            configs: dict containing configs

        Returns:
            mapping of name (str) to Device objects
        """
        self.configs = configs

        devices = {}
        for name, device in configs['devices'].items():
            devices[name] = self.__device_from_device_config(name, device)

        return devices

    def __sanitized(self, name):
        return self.name_pattern.match(name)

    def __device_from_device_config(self, name: str , configs: dict) -> Device:
        """
        creates a single Device object from config
        Args:
            name: name of device
            configs: config for single device

        Returns:
            Device object
        """
        self.curr_device_transport = None

        power_states = configs['power_states']
        for option, value in power_states.items():
            power_states[option] = pysnmp.Integer(value)

        # read and store the transport for the device
        for transport in self.transport_handlers:
            if transport in configs:
                self.curr_device_transport = transport
        if self.curr_device_transport is None:
            raise ValueError(f'Missing or unsupported transport is device '
                             f'{name}')

        outlets = configs['outlets']

        # get template if needed
        if isinstance(outlets, str):
            if not self.__sanitized(outlets):
                raise ValueError(f'Illegal device template name for device '
                                 f'{name}')
            outlets = self.__template_from_config(outlets)

        return Device(
            name, list(outlets.keys()),
            power_states,
            self.transport_handlers[self.curr_device_transport](
                configs[self.curr_device_transport], outlets
            )
        )

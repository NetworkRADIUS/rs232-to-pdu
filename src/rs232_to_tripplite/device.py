"""
Contains Device class meant to model a target device.

Each device must have a name, a list of outlets, and a transport method
"""
from dataclasses import dataclass

import pysnmp.hlapi.asyncio as pysnmp

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


def device_from_config(  # pylint: disable=too-many-locals
        name: str, config: dict, timeout: int, retry: int
) -> Device:
    """
    Factory function for creating a Device instance from a config dict

    Args:
        name: string representation of device name
        config: dictionary containing configs for a device

    Returns:
        Device instance
    """
    outlets = config['outlets']
    transport = None  # should be over-writen or exception thrown

    power_states = config['power_states']
    for option, value in power_states.items():
        if not isinstance(option, str):
            raise TypeError('Power option must be a string')
        power_states[option] = pysnmp.Integer(value)

    if 'snmp' in config:
        ip_address = config['snmp']['ip_address']
        port = config['snmp']['port']

        if 'v1' in config['snmp']:
            # ensure only 1 SNMP version is present
            if 'v2' in config['snmp'] or 'v3' in config['snmp']:
                raise AttributeError(f'Device {name} contains multiple SNMP '
                                     f'authentication schemes')
            public_community = config['snmp']['v1']['public_community']
            private_community = config['snmp']['v1']['private_community']

            transport = TransportSnmpV1V2(
                outlets, 1, ip_address, port,
                public_community, private_community,
                timeout, retry
            )

        elif 'v2' in config['snmp']:
            # ensure only 1 SNMP version is present
            if 'v1' in config['snmp'] or 'v3' in config['snmp']:
                raise AttributeError(f'Device {name} contains multiple SNMP '
                                     f'authentication schemes')
            public_community = config['snmp']['v2']['public_community']
            private_community = config['snmp']['v2']['private_community']

            transport = TransportSnmpV1V2(
                outlets, 2, ip_address, port,
                public_community, private_community,
                timeout, retry
            )

        elif 'v3' in config['snmp']:
            # ensure only 1 SNMP version is present
            if 'v1' in config['snmp'] or 'v2' in config['snmp']:
                raise AttributeError(f'Device {name} contains multiple SNMP '
                                     f'authentication schemes')

            user = config['snmp']['v3']['user']
            auth_protocol = config['snmp']['v3']['auth_protocol']
            auth_passphrase = config['snmp']['v3']['auth_passphrase']
            priv_protocol = config['snmp']['v3']['priv_protocol']
            priv_passphrase = config['snmp']['v3']['priv_passphrase']
            security_level = config['snmp']['v3']['security_level']

            transport = TransportSnmpV3(
                outlets, 3, ip_address, port,
                user, auth_protocol, auth_passphrase,
                priv_protocol, priv_passphrase,
                security_level,
                timeout, retry
            )

    if transport is None:
        # raise error if transport is not supported
        raise TypeError(f'Unsupported transport for device {name}')

    return Device(name, list(outlets.keys()), power_states, transport)

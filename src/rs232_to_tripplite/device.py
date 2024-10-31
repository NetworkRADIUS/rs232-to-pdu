from rs232_to_tripplite.transport.base import Transport
from rs232_to_tripplite.transport.snmp import TransportSnmpV1V2, TransportSnmpV3


class Device:
    """
    Class representing a Device with controllable outlets
    """
    def __init__(
            self,
            name: str, outlets: list[str], transport: Transport
    ):
        """

        Args:
            name: device name
            outlets: list of outlet names
            transport: object for sending requests
        """
        self.name = name
        self.outlets = outlets
        self.transport = transport

    def get_outlet_state(self, outlet: str) -> any:
        """
        method for retrieving an outlet's state using the transport
        Args:
            outlet: string representation of outlet

        Returns:
            outlet state
        """
        return self.transport.get_outlet_state(outlet)

    def set_outlet_state(self, outlet: str, state: any) -> any:
        """
        method for setting an outlet's state using the transport'
        Args:
            outlet: string representation of outlet
            state: desired outlet state

        Returns:
            outlet state after sending the request
        """
        self.transport.set_outlet_state(outlet, state)

def create_device_from_config_dict(name: str, config_dict: dict) -> Device:
    """
    Factory function for creating a Device instance from a config dict

    Args:
        name: string representation of device name
        config_dict: dictionary containing configs for a device

    Returns:
        Device instance
    """
    outlets = config_dict['outlets']
    transport = None  # should be over-writen or exception thrown

    if 'snmp' in config_dict:
        ip_address = config_dict['snmp']['ip_address']
        port = config_dict['snmp']['port']

        if 'v1' in config_dict['snmp']:
            # ensure only 1 SNMP version is present
            if 'v2' in config_dict['snmp'] or 'v3' in config_dict['snmp']:
                raise AttributeError(f'Device {name} contains multiple SNMP '
                                     f'authentication schemes')
            public_community = config_dict['snmp']['v1']['public_community']
            private_community = config_dict['snmp']['v1']['private_community']

            transport = TransportSnmpV1V2(
                outlets, 1, ip_address, port,
                public_community, private_community
            )

        elif 'v2' in config_dict['snmp']:
            # ensure only 1 SNMP version is present
            if 'v1' in config_dict['snmp'] or 'v3' in config_dict['snmp']:
                raise AttributeError(f'Device {name} contains multiple SNMP '
                                     f'authentication schemes')
            public_community = config_dict['snmp']['v2']['public_community']
            private_community = config_dict['snmp']['v2']['private_community']

            transport = TransportSnmpV1V2(
                outlets, 2, ip_address, port,
                public_community, private_community
            )

        elif 'v3' in config_dict['snmp']:
            # ensure only 1 SNMP version is present
            if 'v1' in config_dict['snmp'] or 'v2' in config_dict['snmp']:
                raise AttributeError(f'Device {name} contains multiple SNMP '
                                     f'authentication schemes')

            user = config_dict['snmp']['v3']['user']
            auth_protocol = config_dict['snmp']['v3']['auth_protocol']
            auth_passphrase = config_dict['snmp']['v3']['auth_passphrase']
            priv_protocol = config_dict['snmp']['v3']['priv_protocol']
            priv_passphrase = config_dict['snmp']['v3']['priv_passphrase']
            security_level = config_dict['snmp']['v3']['security_level']

            transport = TransportSnmpV3(
                outlets, 3, ip_address, port,
                user, auth_protocol, auth_passphrase,
                priv_protocol, priv_passphrase,
                security_level
            )

    if transport is None:
        # raise error if transport is not supported
        raise TypeError(f'Unsupported transport for device {name}')

    return Device(name, outlets.keys(), transport)

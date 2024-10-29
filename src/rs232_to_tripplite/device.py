from abc import ABC, abstractmethod

import pysnmp.hlapi.asyncio as pysnmp


class Device(ABC):
    """
    Abstract device class
    """

    def __init__(
            self,
            name: str, snmp_version: int, ip_address: str, port: int,
            outlet_oids: dict[str: str], **kwargs
    ):
        self.name = name
        self.snmp_version = snmp_version
        self.ip_address = ip_address
        self.port = port
        self.outlet_oids = outlet_oids

    @abstractmethod
    def get_outlet_state(self, outlet: str) -> any:
        """
        Abstract method for getting current state of an outlet

        Args:
            outlet: string representation of outlet

        Returns:
            state of the outlet
        """
        ...

    @abstractmethod
    def set_outlet_state(self, outlet: str, state: any) -> any:
        """
        Abstract method for setting the state of an outlet

        Args:
            outlet: string representation of outlet
            state: new state of the outlet

        Returns:
            return data from setting the outlet
        """
        ...


class SnmpDeviceV1V2(Device):
    """
    Device class for SNMP devices using v1 or v2 authentication schemes
    """
    def __init__(
            self,
            name: str, snmp_version: int, ip_address: str, port: int,
            outlet_oids: dict[str: str],
            public_community: str, private_community: str,
            **kwargs
    ):
        super().__init__(
            name, snmp_version, ip_address, port, outlet_oids, **kwargs
        )

        self.public_community = public_community
        self.private_community = private_community

    async def get_outlet_state(self, outlet: str) -> any:
        """
        Sends SNMP GET command to get state of outlet

        Args:
            outlet: string representation of outlet

        Returns:
            current state of the outlet
        """
        results = await pysnmp.getCmd(
            pysnmp.SnmpEngine(),
            pysnmp.CommunityData(self.public_community,
                                 # use correct model based on v1 or v2
                                 mpModel = 0 if self.snmp_version == 1 else 1),
            pysnmp.UdpTransportTarget((self.ip_address, self.port)),
            pysnmp.ContextData(),
            pysnmp.ObjectType(pysnmp.ObjectIdentity(self.outlet_oids[outlet]),)
        )

        return results

    async def set_outlet_state(self, outlet: str, state: any) -> any:
        """
        Sends SNMP SET command to set state of an outlet
        Args:
            outlet: string representation of outlet
            state: desired state of outlet, already in a pysnmp datatype

        Returns:
            current state of the outlet
        """
        results = await pysnmp.setCmd(
            pysnmp.SnmpEngine(),
            pysnmp.CommunityData(self.public_community,
                                 mpModel = 0 if self.snmp_version == 1 else 1),
            pysnmp.UdpTransportTarget((self.ip_address, self.port)),
            pysnmp.ContextData(),
            pysnmp.ObjectType(pysnmp.ObjectIdentity(self.outlet_oids[outlet]),
                              state)
        )

        return results

class SnmpDeviceV3(Device):
    """
    Device class for SNMP devices using v3 authentication scheme
    """
    def __init__(
            self,
            name: str, snmp_version: int, ip_address: str, port: int,
            outlet_oids: dict[str: str],
            user: str, auth_protocol: str, auth_passphrase: str,
            priv_protocol: str, priv_passphrase: str,
            **kwargs
    ):
        super().__init__(
            name, snmp_version, ip_address, port, outlet_oids, **kwargs
        )

        self.user = user
        if auth_protocol == 'SHA':
            self.auth_protocol = pysnmp.usmHMACSHAAuthProtocol
        self.auth_passphrase = auth_passphrase
        if priv_protocol == 'AES':
            self.priv_protocol = pysnmp.usmAesCfb128Protocol
        self.priv_passphrase = priv_passphrase

    async def get_outlet_state(self, outlet):
        """
        Sends SNMP GET command to get state of outlet

        Args:
            outlet: string representation of outlet

        Returns:
            current state of the outlet
        """
        results = await pysnmp.getCmd(
            pysnmp.SnmpEngine(),
            pysnmp.UsmUserData(
                self.user,
                authProtocol = self.auth_protocol,
                authKey = self.auth_passphrase,
                privProtocol = self.priv_protocol,
                privKey = self.priv_passphrase,
            ),
            pysnmp.UdpTransportTarget((self.ip_address, self.port)),
            pysnmp.ContextData(),
            pysnmp.ObjectType(pysnmp.ObjectIdentity(self.outlet_oids[outlet]),)
        )

        return results

    async def set_outlet_state(self, outlet, state):
        """
        Sends SNMP SET command to set state of an outlet
        Args:
            outlet: string representation of outlet
            state: desired state of outlet, already in a pysnmp datatype

        Returns:
            current state of the outlet
        """
        results = await pysnmp.setCmd(
            pysnmp.SnmpEngine(),
            pysnmp.UsmUserData(
                self.user,
                authProtocol = self.auth_protocol,
                authKey = self.auth_passphrase,
                privProtocol = self.priv_protocol,
                privKey = self.priv_passphrase,
            ),
            pysnmp.UdpTransportTarget((self.ip_address, self.port)),
            pysnmp.ContextData(),
            pysnmp.ObjectType(pysnmp.ObjectIdentity(self.outlet_oids[outlet]),
                              state)
        )

        return results


def create_device_from_config_dict(name: str, config_dict: dict) -> Device:
    """
    Factory function for creating a Device instance from a config dict

    Args:
        name: string representation of device name
        config_dict: dictionary containing configs for a device

    Returns:
        Device instance
    """
    if 'snmp' in config_dict:
        ip_address = config_dict['snmp']['ip_address']
        port = config_dict['snmp']['port']
        outlet_oids = config_dict['snmp']['outlets']

        if 'v1' in config_dict['snmp']:
            public_community = config_dict['snmp']['v1']['public_community']
            private_community = config_dict['snmp']['v1']['private_community']
            return SnmpDeviceV1V2(
                name, 1, ip_address, port, outlet_oids,
                public_community, private_community
            )
        elif 'v2' in config_dict['snmp']:
            public_community = config_dict['snmp']['v2']['public_community']
            private_community = config_dict['snmp']['v2']['private_community']
            return SnmpDeviceV1V2(
                name, 1, ip_address, port, outlet_oids,
                public_community, private_community
            )
        elif 'v3' in config_dict['snmp']:
            user = config_dict['snmp']['v3']['user']
            auth_protocol = config_dict['snmp']['v3']['auth_protocol']
            auth_passphrase = config_dict['snmp']['v3']['auth_passphrase']
            priv_protocol = config_dict['snmp']['v3']['priv_protocol']
            priv_passphrase = config_dict['snmp']['v3']['priv_passphrase']
            return SnmpDeviceV3(
                name, 1, ip_address, port, outlet_oids,
                user, auth_protocol, auth_passphrase,
                priv_protocol, priv_passphrase
            )

    # code reaches here if no devices matched above
    raise TypeError(f'Unsupported device type for device {name}')

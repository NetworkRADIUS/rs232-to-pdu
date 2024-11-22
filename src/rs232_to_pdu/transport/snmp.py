"""
rs232-to-pdu
Copyright (C) 2024 InkBridge Networks (legal@inkbridge.io)

rs232-to-pdu © 2024 by InkBridge is licensed under CC BY-NC 4.0. To view a copy
of this license, visit https://creativecommons.org/licenses/by-nc/4.0/

Contains the transport subclasses for SNMP and the different versions
"""
import logging

import pysnmp.hlapi.asyncio as pysnmp
from pysnmp.hlapi.asyncio import CommunityData, UsmUserData

from rs232_to_pdu.transport.base import Transport

logger = logging.getLogger(__name__)


class TransportSnmp(Transport):
    """
    Concrete class representing the use of SNMP to send cmds for state changes
    and retrievals
    """

    def __init__(self, oids: dict[str: str], version: int,
                 # pylint: disable=too-many-arguments
                 read_auth: CommunityData | UsmUserData,
                 write_auth: CommunityData | UsmUserData,
                 ip_address: str, port: int,
                 timeout: int, retries: int):
        """

        Args:
            oids: mappings between outlet names and OIDs
            version: SNMP version
            read_auth: session data for sending a read-only command
            write_auth: session data for sending a read-write command
            ip_address: SNMP agent's IP address
            port: SNMP agent's port
        """
        super().__init__(oids.keys())

        # convert string representation of OIDs to pysnmp data structures
        self.oids = {}
        for outlet, oid in oids.items():
            self.oids[outlet] = pysnmp.ObjectIdentity(oid)

        self.version = version

        # sets up session data
        self.engine = pysnmp.SnmpEngine()
        self.read_auth = read_auth
        self.write_auth = write_auth
        self.target = pysnmp.UdpTransportTarget((ip_address, port),
                                                timeout=timeout,
                                                retries=retries)
        self.context = pysnmp.ContextData()

    def __oid_from_outlet(self, outlet):
        if outlet not in self.oids:
            logger.warning(f'Outlet {outlet} not found!')
        return self.oids[outlet]

    async def outlet_state_get(self, outlet: str) -> bool:
        """
        Sends GET command to get outlet state
        Args:
            outlet: string representation of outlet

        Returns:
            outlet state
        """
        oid = self.__oid_from_outlet(outlet)

        # Uses read-only authentication to perform GET commands
        err_indicator, err_status, err_index, var_binds = await pysnmp.getCmd(
            self.engine,
            self.read_auth,
            self.target,
            self.context,
            pysnmp.ObjectType(oid)
        )

        if err_indicator or err_status:
            logger.error(f'SNMP get command failed. Status: '
                         f'{err_indicator, err_status, err_index, var_binds}')

        return not (err_indicator or err_status)

    async def outlet_state_set(
            self, outlet: str, state: any
    ) -> bool:
        """
        Sends SET command to change outlet state
        Args:
            outlet: string representation of outlet
            state: desired state of outlet (in pysnmp data structure)

        Returns:
            outlet state after state change
        """
        oid = self.__oid_from_outlet(outlet)
        # Uses read-write authentication to perform SET commands
        err_indicator, err_status, err_index, var_binds = await pysnmp.setCmd(
            self.engine,
            self.write_auth,
            self.target,
            self.context,
            pysnmp.ObjectType(oid, state)
        )
        if err_indicator or err_status:
            logger.error(
                f'SNMP set command failed. Status: '
                f'{err_indicator, err_status, err_index, var_binds}')

        return not (err_indicator or err_status)


class TransportSnmpV1V2(TransportSnmp):
    """
    Class representing the use of SNMP v1 or v2 as transport
    """

    def __init__(self, oids: dict[str: any], version: int,
                 # pylint: disable=too-many-arguments
                 ip_address: str, port: int,
                 public: str, private: str,
                 timeout: int, retries: int):
        """

        Args:
            oids: mappings between outlet names and OIDs
            version: SNMP version
            ip_address: SNMP agent's IP address
            port: SNMP agent's port
            public: name of read-only community
            private: name of read-write community
        """

        # uses public and private communities as read-only and read-write
        super().__init__(
            oids, version,
            pysnmp.CommunityData(public,
                                 mpModel=0 if version == 1 else 1),
            pysnmp.CommunityData(private,
                                 mpModel=0 if version == 1 else 1),
            ip_address, port,
            timeout, retries
        )


class TransportSnmpV3(TransportSnmp):
    """
    class representing the use of SNMP v3 as transport
    """

    def __init__(self, oids: dict[str: str], version: int,
                 # pylint: disable=too-many-arguments
                 ip_address: str, port: int,
                 user: str, auth_protocol: str, auth_passphrase: str,
                 priv_protocol: str, priv_passphrase: str,
                 security_level: str,
                 timeout: int, retries: int):
        """

        Args:
            oids: mappings between outlet names and OIDs
            version: SNMP version
            ip_address: SNMP agent's IP address
            port: SNMP agent's port
            user: username
            auth_protocol: authentication protocol
            auth_passphrase: authentication password
            priv_protocol: privacy protocol
            priv_passphrase: privacy password
            security_level: security level (authentication and/or privacy)
        """

        # converting protocols from string to pysnmp datatypes
        match auth_protocol:
            case 'SHA':
                auth_protocol = pysnmp.usmHMACSHAAuthProtocol
        match priv_protocol:
            case 'AES':
                priv_protocol = pysnmp.usmAesCfb128Protocol

        # perform masking based on security level
        match security_level:
            case 'noAuthNoPriv':
                auth_protocol = None
                auth_passphrase = None
                priv_protocol = None
                priv_passphrase = None
            case 'authNoPriv':
                priv_protocol = None
                priv_passphrase = None

        # create user model
        user_auth_obj = pysnmp.UsmUserData(
            user,
            authProtocol=auth_protocol,
            authKey=auth_passphrase,
            privProtocol=priv_protocol,
            privKey=priv_passphrase,
        )

        # use user model as both read-only and read-write access
        super().__init__(
            oids, version,
            user_auth_obj, user_auth_obj,
            ip_address, port,
            timeout, retries
        )

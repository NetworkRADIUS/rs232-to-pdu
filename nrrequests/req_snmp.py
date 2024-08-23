"""
Contains class that will send set commands to PDU agent to change current power
settings for specific bank/ports

Author: Patrick Guo
Date: 2024-08-13
"""

import asyncio
import configparser
import enum
import pathlib

import pysnmp.hlapi.asyncio as snmp

import nrlogging.loggingfactory as nrlogfac

# Read and setup configs
CONFIG_FILE = pathlib.Path('config.ini')
CONFIG = configparser.ConfigParser()
CONFIG.read(CONFIG_FILE)

logger = nrlogfac.create_logger(__name__)

class PowerbarValues(enum.Enum):
    """Possible power values for powerbar ports
    """
    OFF = 1
    ON = 2
    CYCLE = 3


class SnmpCommandIssuer:
    """ 
    Simple wrapper class to create and send SET commands to turn specific
    ports on the power bars on and off
    """

    def __init__(self):
        """
        """

    @staticmethod
    async def send_set_command(oid: str, value: int, target_ip: str,
                               port: int = 161) -> None:
        """Create and sends SET command with given parameters

        Args:
          oid (str):
            String representing the device name or OID
          value (int):
            New value for the device
          target_ip (str):
            IP address of where device is located
          community (str):
            Name of SNMP community device is in
          port (int):
            Port on which device is expecting SNMP commands
        
        Returns:
          None
        
        Raises:
          None
        """

        # Sets up auth and priv protocols
        auth_protocol = snmp.usmHMACSHAAuthProtocol if CONFIG['PDU_AUTH']['AUTH'] == 'SHA' else None
        priv_protocol = snmp.usmAesCfb128Protocol if CONFIG['PDU_AUTH']['PRIV'] == 'AES' else None

        await snmp.setCmd(snmp.SnmpEngine(),
                          snmp.UsmUserData(CONFIG['PDU_AUTH']['USER'],
                                           authKey=CONFIG['PDU_AUTH']['AUTH_PASSPHRASE'],
                                           privKey=CONFIG['PDU_AUTH']['PRIV_PASSPHRASE'],
                                           authProtocol=auth_protocol,
                                           privProtocol=priv_protocol),
                          snmp.UdpTransportTarget((target_ip, port)),
                          snmp.ContextData(),
                          snmp.ObjectType(snmp.ObjectIdentity(oid),
                                          snmp.Integer(value)))

    def set_port_on(self, oid: str, target_ip: str, port: int) -> None:
        """
        Set bank port to ON state

        Args:
            oid (str): OID of bank power outlet command
            target_ip (str): IP address of SNMP agent
            port (str): Port of SNMP agent
        
        Returns:
            None
        """
        curr_loop = asyncio.get_running_loop()
        curr_loop.create_task(self.send_set_command(oid,
                                                    PowerbarValues.ON.value,
                                                    target_ip, port))

    def set_port_off(self, oid, target_ip, port):
        """
        Set bank port to OFF state

        Args:
            oid (str): OID of bank power outlet command
            target_ip (str): IP address of SNMP agent
            port (str): Port of SNMP agent
        
        Returns:
            None
        """
        curr_loop = asyncio.get_running_loop()
        curr_loop.create_task(self.send_set_command(oid,
                                                    PowerbarValues.OFF.value,
                                                    target_ip, port))

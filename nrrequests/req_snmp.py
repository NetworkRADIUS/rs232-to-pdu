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
    def get_bank_port_oid(bank: str, port: str) -> str:
        """
        Retrieves OID for specific bank/port from config file

        Args:
            bank (str): bank number as a string
            port (str): port number as a string

        Returns:
            String conatining full OID of bank/port outlet command
        """
        return CONFIG[f'BANK{bank:03d}'][f'PORT{port:03d}']

    async def send_set_command(self,
                               bank: int, port: int, value: int,
                               target_ip: str, ip_port: int = 161,
                               timeout: int = 5,
                               retry_delay: int = 3,
                               max_retry: int = 3) -> None:
        """Create and sends SET command with given parameters

        Args:
            bank (int):
                Numerical value of the bank
            port (int):
                Numerical value of the outlet port
            value (int):
                New value for the device
            target_ip (str):
                IP address of where device is located
            community (str):
                Name of SNMP community device is in
            ip_port (int):
                Network port on which device is expecting SNMP commands
            timeout (int):
                Number in seconds after which the command is considered dead
            retry_delay (int):
                Number in seconds after which to resend the command after the
                previous attempt failed or timed-out
            max_retry (int):
                Maximum number of times to retry the command
        
        Returns:
            None
        """
        # Retrieve OID using bank and port from sequence
        oid = self.get_bank_port_oid(bank, port)

        # Sets up auth and priv protocols
        auth_protocol = snmp.usmHMACSHAAuthProtocol if CONFIG['PDU_AUTH']['AUTH'] == 'SHA' else None
        priv_protocol = snmp.usmAesCfb128Protocol if CONFIG['PDU_AUTH']['PRIV'] == 'AES' else None

        for attempt in range(max_retry):
            try:
                async with asyncio.timeout(timeout):
                    results = await snmp.setCmd(snmp.SnmpEngine(),
                                                snmp.UsmUserData(CONFIG['PDU_AUTH']['USER'],
                                                                authKey=CONFIG['PDU_AUTH']['AUTH_PASSPHRASE'],
                                                                privKey=CONFIG['PDU_AUTH']['PRIV_PASSPHRASE'],
                                                                authProtocol=auth_protocol,
                                                                privProtocol=priv_protocol),
                                                snmp.UdpTransportTarget((target_ip, ip_port)),
                                                snmp.ContextData(),
                                                snmp.ObjectType(snmp.ObjectIdentity(oid),
                                                                snmp.Integer(value)))
                
                err_indict, err_status, err_index, var_binds = results

                if err_indict:
                    logger.error(('Error has occured when attempting to set '
                                  'bank %s port %s to state %s: %s'),
                                  bank, port, value, err_indict)
                    asyncio.sleep(retry_delay)
                else:
                    logger.info('Successfully set bank %s port %s to state %s',
                                bank, port, value)
                    return

            except TimeoutError:
                logger.error(('Timeout Error when attempting to set bank %s '
                              'port %s to state %s'),
                              bank, port, value)
        logger.error(('Maximum attempts reached when attempting to set bank '
                      '%s port %s to state %s'),
                      bank, port, value)



    def set_port_on(self, bank: int, port: int, target_ip: str, ip_port: int) -> None:
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
        curr_loop.create_task(self.send_set_command(bank, port,
                                                    PowerbarValues.ON.value,
                                                    target_ip, ip_port))

    def set_port_off(self, bank: int, port: int, target_ip: str, ip_port: int) -> None:
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
        curr_loop.create_task(self.send_set_command(bank, port,
                                                    PowerbarValues.OFF.value,
                                                    target_ip, ip_port))

    async def send_healthcheck_command(self, target_ip: str, ip_port: int,
                                       timeout:int) -> None:
        """
        Creates and sends GET command to perform a power bank healthcheck

        Args:
            target_ip: IP address of the agent
            ip_port: Listening port of the agent
            timeout: timeout value for SNMP command
        
        Return:
            None
        
        """
        auth_protocol = snmp.usmHMACSHAAuthProtocol if CONFIG['PDU_AUTH']['AUTH'] == 'SHA' else None
        priv_protocol = snmp.usmAesCfb128Protocol if CONFIG['PDU_AUTH']['PRIV'] == 'AES' else None

        try:
            async with asyncio.timeout(timeout):
                results = await snmp.getCmd(snmp.SnmpEngine(),
                                            snmp.UsmUserData(CONFIG['PDU_AUTH']['USER'],
                                                            authKey=CONFIG['PDU_AUTH']['AUTH_PASSPHRASE'],
                                                            privKey=CONFIG['PDU_AUTH']['PRIV_PASSPHRASE'],
                                                            authProtocol=auth_protocol,
                                                            privProtocol=priv_protocol),
                                            snmp.UdpTransportTarget((target_ip, ip_port)),
                                            snmp.ContextData(),
                                            snmp.ObjectType(snmp.ObjectIdentity('SNMPv2-MIB', 'sysName', 0)))

            err_indict, err_status, err_index, var_binds = results

            if not err_indict:
                logger.info('Power bank in good health...')
            else:
                logger.error('Power bank healthcheck failed... %s', err_indict)
        except TimeoutError:
            logger.error('Power bank healthcheck timed out...')
    
    def run_healthcheck(self, target_ip: str, ip_port: int, timeout: int):
        """
        Wrapper function to run healthcheck as an async coroutine

        Args:
            target_ip: IP address of the agent
            ip_port: Listening port of the agent
            timeout: timeout value for SNMP command
        
        Return:
            None
        """
        asyncio.run(self.send_healthcheck_command(target_ip, ip_port, timeout))

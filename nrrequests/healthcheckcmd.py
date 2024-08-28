"""
Class for creating and sending a GET command to perform a health check of the
PDU SNMP agent

Contains logic for timeout and retries on failures.

Author: Patrick Guo
Date: 2024-08-28
"""
import asyncio

import pysnmp.hlapi.asyncio as pysnmp
from pysnmp.proto.errind import ErrorIndication

import nrlogging.loggingfactory as nrlogfac
from nrrequests.basesnmpcmd import BaseSnmpCmd

logger = nrlogfac.create_logger(__name__)


class HealthcheckCmd(BaseSnmpCmd):
    """
    Clas for creating and sending GET commands to PDU
    """
    def __init__(self,
                 agent_ip: str, agent_port: int,
                 user: str, auth: str, priv: str,
                 auth_protocol: tuple, priv_protocol: tuple,
                 timeout: int, max_attempts: int, retry_delay: int,
                 ) -> None:
        """
                Initialization of attributes

        Args:
            agent_ip (str): IP address agent is located at
            agent_port (int): network port agent is listening on
            user (str): username of SNMP user
            auth (str): authentication passphrase for user
            priv (str): privacy passphrase for user
            auth_protocol (tuple): authentication protocol used
            priv_protocol (tuple): privacy protocol used
            timeout (int): time in seconds before timing-out command
            max_attempts (int): maximum number of attempts for a command
            retry_delay (int): time in seconds before retrying a failed command
        """

        # Call parent class to initiate attributes
        super().__init__(agent_ip, agent_port,
                         user, auth, priv, auth_protocol, priv_protocol,
                         timeout, max_attempts, retry_delay,
                         None, ['SNMPv2-MIB', 'sysName', 0])

    async def invoke_cmd(self) -> tuple[ErrorIndication,
                                        str,
                                        int,
                                        tuple[pysnmp.ObjectType,...]]:
        """
        Invokes pysnmp.getCmd() to send GET command

        Args:
            None

        Returns:
            errorIndication (ErrorIndication): Engine error indicator. Has
                                               value of None if no errors
            errorStatus (str): PDU (protocol data unit) error indicator. Has
                               value of None if no errors
            errorIndex (int): index for varBinds for object causing error
            varBinds (tuple[pysnmp.ObjectType,...]): sequence of ObjectTypes
                                                     representing MIBs
        """
        # Creates required objects and sends GET command
        results = await pysnmp.getCmd(
            pysnmp.SnmpEngine(),
            pysnmp.UsmUserData(
                userName=self.user.username,
                authKey=self.user.auth,
                privKey=self.user.priv,
                authProtocol=self.user.auth_protocol,
                privProtocol=self.user.priv_procotol
            ),
            pysnmp.UdpTransportTarget(
                (self.agent_loc.agent_ip,
                 self.agent_loc.agent_port)
            ),
            pysnmp.ContextData(),
            pysnmp.ObjectType(
                pysnmp.ObjectIdentity(*self.pdu_object.object_identities)
            )
        )

        return results

    async def run_cmd(self) -> None:
        """
        Contains logic for logging and when to invoke SNMP commands

        Args:
            None
        
        Returns:
            None
        """

        try:
            # Uses timeouts
            async with asyncio.timeout(self.timeout):
                result = await self.invoke_cmd()
                err_indicator, err_status, err_index, var_binds = result

            # If no errors, return to quit function
            if not err_indicator:
                logger.info('PDU health check passed')
                return

            # If error, log error in entirety
            logger.error(
                ('Error when performing health check.'
                 'Engine status: %s. PDU status: %s. MIB status: %s'),
                err_indicator, err_status, var_binds[err_index]
            )

        # On catching timeout, log the error
        except TimeoutError:
            logger.error('Timeout Error on health check')

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

import ser2snmp.logging.loggingfactory as nrlogfac
from ser2snmp.requests.basesnmpcmd import BaseSnmpCmd

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
                 cmd_id: int, target_obj = None, bank_num: int = None
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
            cmd_id (int): int representing ID of current command
        """

        if target_obj is None:
            target_obj = ('SNMPv2-MIB', 'sysName', 0)

        # Call parent class to initiate attributes
        super().__init__(agent_ip, agent_port,
                         user, auth, priv, auth_protocol, priv_protocol,
                         timeout, max_attempts, retry_delay,
                         None, target_obj,
                         cmd_id)
    
        self.bank_num = bank_num

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

    def handler_cmd_success(self):
        """
        Handler for SNMP CMD success that logs the result

        Args:
            cmd_id (int): ID of the current command
        """
        logger.info('Command #%d: PDU health check passed for bank %s', 
                    self.cmd_id, self.bank_num)

    def handler_cmd_error(self, err_indicator, err_status, err_index,
                          var_binds):
        """
        Handler for SNMP CMD failure that logs the failure

        Args:
            cmd_id (int): ID of the current command

        """
        logger.error(
            ('Command #%d: Error when performing health check for bank %s.'
                'Engine status: %s. PDU status: %s. MIB status: %s'),
                self.cmd_id, self.bank_num,
                err_indicator, err_status, var_binds
        )

    def handler_timeout_error(self):
        """
        Handler for SNMP timeout failure that logs the failure

        Args:
            cmd_id (int): ID of the current command

        """
        logger.error('Command #%d: Timed-out on health check for bank %s', 
                     self.cmd_id, self.bank_num)

    def handler_max_attempts_error(self):
        """
        Handler for max attempts failure that logs the failure

        Args:
            cmd_id (int): ID of the current command

        """
        # Healthchecks don't do retries so no error logging for this
        return

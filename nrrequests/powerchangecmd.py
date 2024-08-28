"""
Class for creating and sending a SET command to change the power options for a 
power outlet.

Contains logic for timeout and retries on failures.

Author: Patrick Guo
Date: 2024-08-28
"""
import asyncio
import pysnmp.hlapi.asyncio as pysnmp
from pysnmp.proto.errind import ErrorIndication

from nrrequests.basesnmpcmd import BaseSnmpCmd
import nrlogging.loggingfactory as nrlogfac


logger = nrlogfac.create_logger(__name__)


class PowerChangeCmd(BaseSnmpCmd):
    """
    Class for creating and sending SET command to PDU
    """
    def __init__(self,
                 agent_ip: str, agent_port: int,
                 user: str, auth: str, priv: str,
                 auth_protocol: tuple, priv_protocol: tuple,
                 timeout: int, max_attempts: int, retry_delay: int,
                 object_value: any, object_identities: tuple[any,...],
                 outlet_bank: int, outlet_port: int
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
            object_value (any): desired new value of object
            object_identities (tuple[any,...]): object identifiers
            outlet_bank (int): power outlet bank number
            outlet_port (int): power outlet port number
        """

        # Call parent class to initiate attributes
        super().__init__(agent_ip, agent_port,
                         user, auth, priv, auth_protocol, priv_protocol,
                         timeout, max_attempts, retry_delay,
                         object_value, object_identities)

        # Initialize the bank and port numbers. These values are only used
        # for logging purposes. OID for outlet is already passed in
        self.outlet_bank = outlet_bank
        self.outlet_port = outlet_port

    async def invoke_cmd(self) -> tuple[ErrorIndication,
                                        str,
                                        int,
                                        tuple[pysnmp.ObjectType,...]]:
        """
        Invokes pysnmp.setCmd() to send SET command

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
        # Creates required objects and sends SET command
        results = await pysnmp.setCmd(
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
                pysnmp.ObjectIdentity(*self.pdu_object.object_identities),
                pysnmp.Integer(self.pdu_object.object_value)
            )
        )

        return results

    async def run_cmd(self, cmd_id) -> bool:
        """
        Contains logic for logging and when to invoke SNMP commands

        Args:
            cmd_id (int): a numerical ID of the command
        
        Returns:
            boolean representing success/failure. True = success.
        """
        # for loop to go through max attempts
        for attempt in range(self.max_attempts):
            try:

                # Uses timeouts
                async with asyncio.timeout(self.timeout):
                    result = await self.invoke_cmd()
                    err_indicator, err_status, err_index, var_binds = result

                # If no errors, return to quit function
                if not err_indicator and not err_status:
                    logger.info(
                        'Command #%d: Successfully set bank %s port %s to %s',
                        cmd_id, self.outlet_bank, self.outlet_port,
                        self.pdu_object.object_value
                    )
                    return True

                # If error, log error in entirety
                logger.error(
                    ('Command #%d Error when setting bank %s port %s to %s.'
                     'Engine status: %s. PDU status: %s. MIB status: %s'),
                    cmd_id, self.outlet_bank, self.outlet_port,
                    self.pdu_object.object_value,
                    err_indicator, err_status, var_binds[err_index]
                )

            # On catching timeout, log the error
            except TimeoutError:
                logger.error(
                    'Command #%d: Timed-out setting bank %s port %s to %s',
                    cmd_id, self.outlet_bank, self.outlet_port,
                    self.pdu_object.object_value
                )

            # On retry, first wait for retry delay
            await asyncio.sleep(self.retry_delay)

        # If app reaches this line, max attempts have been attempted, thus
        # log the error
        logger.error(
            'Command #%d: Max retry attempts setting bank %s port %s to %s',
             cmd_id, self.outlet_bank, self.outlet_port,
             self.pdu_object.object_value
        )

        return False

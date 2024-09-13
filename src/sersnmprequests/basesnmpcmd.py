"""
Base class for a SNMP Command sender. Also contains dataclasses representing
entities needed to send a command

We wrap sending a SNMP command inside a class so that we can have a queue/list
of Child classes. This way, we have a unified way of invoking snmp commands
while still being able to customize aspects such as logging and command type
(get, set, trap, etc.)

Author: Patrick Guo
Date: 2024-08-28
"""
from dataclasses import dataclass
import asyncio

import pysnmp.hlapi.asyncio as pysnmp
from pysnmp.proto.errind import ErrorIndication

@dataclass
class AgentLocator:
    """
    Entity class representing an SNMP agent

    Contains the agent IP and port.

    Attributes:
        agent_ip (str): the IP address where the agent is located
        agent_port (int): the network port where the agent is listening
    """
    agent_ip: str
    agent_port: int


@dataclass
class SnmpUser:
    """
    Entity class representing an SNMP user

    Contains the authentication credentials for a user

    Attributes:
        username (str): username of user
        auth (str): authentication passphrase
        priv (str): privacy passphrase
        auth_protocol (tuple): authentication protocol used. Represented in a
                               tuple of numbers (for pysnmp)
        priv_protocol (tuple): privacy protocol used. Represented in a
                               tuple of numbers (for pysnmp)
    """
    username: str
    auth: str
    priv: str
    auth_protocol: tuple
    priv_procotol: tuple

@dataclass
class PduObject:
    """
    Entity class representing an SNMP PDU object

    Attributes:
        object_value (any): the desired new value of the object
        object_identities (tuple): a tuple of identifiers for the object
    """
    object_value: any
    object_identities: tuple


class BaseSnmpCmd:
    """
    Abstract SNMP cmd class

    
    """
    def __init__(self,
                 agent_ip: str, agent_port: int,
                 user: str, auth: str, priv: str,
                 auth_protocol: tuple, priv_protocol: tuple,
                 timeout: int, max_attempts: int, retry_delay: int,
                 object_value: any, object_identities: tuple[any,...],
                 cmd_id: int
                 ) -> None:
        """
        Initializes attributes

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
            cmd_id (int): int representing ID of current command
        """

        # Initiate our entity objects
        self.agent_loc = AgentLocator(agent_ip, agent_port)
        self.user = SnmpUser(user, auth, priv, auth_protocol, priv_protocol)
        self.pdu_object = PduObject(object_value, object_identities)

        # Initiate failure conditions
        self.timeout = timeout
        self.max_attempts = max_attempts
        self.retry_delay = retry_delay

        self.cmd_id = cmd_id

    async def invoke_cmd(self) -> tuple[ErrorIndication,
                                        str,
                                        int,
                                        tuple[pysnmp.ObjectType,...]]:
        """
        Abstract method to call the pysnmp commands (getCmd, setCmd, etc.)

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
        raise NotImplementedError('Must be implemented in child class')

    async def run_cmd(self) -> bool:
        """
        Control flow method that calls invoke_cmd and error/success handlers

        Args:
            None
        
        Returns:
            boolean representing success/failure. True = success.
        """
        for _attempt in range(self.max_attempts):
            try:
                async with asyncio.timeout(self.timeout):
                    result = await self.invoke_cmd()
                    err_indicator, err_status, err_index, var_binds = result

                if not err_indicator or err_status:
                    self.handler_cmd_success()
                    return var_binds

                self.handler_cmd_error(err_indicator, err_status, err_index, var_binds)
            except TimeoutError:
                self.handler_timeout_error()
            await asyncio.sleep(self.retry_delay)

        # If for loop is exited, max retry attempts have been reached, thus
        # max attemp error has occured
        self.handler_max_attempts_error()
        return False

    def handler_cmd_success(self) -> None:
        """
        Abstract method reprsenting handler for SNMP CMD success

        Args:
            None
        """
        raise NotImplementedError('Must be implemented in child class')

    def handler_cmd_error(self, err_indicator, err_status, err_index,
                          var_binds):
        """
        Abstract method reprsenting handler for SNMP CMD failure

        Args:
            None
        """
        raise NotImplementedError('Must be implemented in child class')

    def handler_timeout_error(self):
        """
        Abstract method reprsenting handler for timeout failures

        Args:
            None
        """
        raise NotImplementedError('Must be implemented in child class')

    def handler_max_attempts_error(self):
        """
        Abstract method reprsenting handler for max attempts reached failures

        Args:
            None
        """
        raise NotImplementedError('Must be implemented in child class')

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
                 object_value: any, object_identities: tuple[any,...]
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
        """

        # Initiate our entity objects
        self.agent_loc = AgentLocator(agent_ip, agent_port)
        self.user = SnmpUser(user, auth, priv, auth_protocol, priv_protocol)
        self.pdu_object = PduObject(object_value, object_identities)

        # Initiate failure conditions
        self.timeout = timeout
        self.max_attempts = max_attempts
        self.retry_delay = retry_delay

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

    async def run_cmd(self, cmd_id: int) -> bool:
        """
        Abstract method that contains logic for when to call the pysnmp
        commands.

        Should not actually invoke these functions here.

        Args:
            cmd_id (int): a numerical ID of the command
        
        Returns:
            boolean representing success/failure. True = success.
        """
        raise NotImplementedError('Must be implemented in child class')

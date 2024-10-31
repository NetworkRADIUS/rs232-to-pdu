from abc import ABC, abstractmethod

import pysnmp.hlapi.asyncio as pysnmp
from pysnmp.hlapi.asyncio import UsmUserData, CommunityData


class Transport(ABC):
    """
    Abstract class representing a method of transporting outlet state changes
    or retrievals
    """
    def __init__(self, outlets: list[str]):
        """

        Args:
            outlets: list of strings representing controllable outlets
        """
        self.outlets = outlets

    @abstractmethod
    async def get_outlet_state(self, outlet: str) -> any:
        """
        Abstract method for retrieving the state of an outlet
        Args:
            outlet: string representation of the outlet

        Returns:
            state of the outlet
        """
        ...

    @abstractmethod
    async def set_outlet_state(self, outlet: str, state: any) -> any:
        """
        Abstract method for setting the state of an outlet
        Args:
            outlet: string representation of the outlet
            state: desired state

        Returns:
            state of the outlet after sending request
        """
        ...




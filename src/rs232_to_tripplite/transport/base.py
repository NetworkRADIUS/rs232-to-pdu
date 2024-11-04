"""
Abstract base class for a command transport
"""

from abc import ABC, abstractmethod


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
    async def outlet_state_get(self, outlet: str) -> tuple[bool, any]:
        """
        Abstract method for retrieving the state of an outlet
        Args:
            outlet: string representation of the outlet

        Returns:
            success bool, state of the outlet
        """

    @abstractmethod
    async def outlet_state_set(self, outlet: str, state: any) -> tuple[
        bool, any]:
        """
        Abstract method for setting the state of an outlet
        Args:
            outlet: string representation of the outlet
            state: desired state

        Returns:
            success bool, state of the outlet after sending request
        """

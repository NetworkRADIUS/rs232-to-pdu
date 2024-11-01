from abc import ABC, abstractmethod

from rs232_to_tripplite.device import Device


class BaseDeviceCommand(ABC):
    """
    Abstract class to represent a device command sender
    """

    def __init__(self, device: Device, outlet: str, _id: int):
        """

        Args:
            device: Device object to interact with
            outlet: string representation of outlet
            _id: command number (UUID)
        """
        self.device = device
        self.outlet = outlet

        self._id = _id

    @abstractmethod
    async def _invoke_device_command(self) -> tuple[bool, any]:
        """
        Protected method to invoke the device's command

        Returns:
            success, outlet state
        """
        ...

    @abstractmethod
    def send_command(self):
        """
        Outward facing interface to run command

        Returns:

        """
        ...

"""
Base class for a Device Command sender.

We wrap sending a device command inside a class so that we can have a queue/list
of Child classes. This way, we have a unified way of invoking commands
while still being able to customize aspects such as logging

Author: Patrick Guo
Date: 2024-08-28
"""
import asyncio
from abc import ABC, abstractmethod

from rs232_to_tripplite.device import Device
import rs232_to_tripplite.logfactory as nrlogfac

logger = nrlogfac.create_logger(__name__)


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
    async def _invoke_device_command(self):
        """
        Protected method to invoke the device's command

        Returns:

        """
        ...

    @abstractmethod
    def send_command(self):
        """
        Outward facing interface to run command

        Returns:

        """
        ...


class UdpCommand(BaseDeviceCommand, ABC):
    """
    class representing a command used on UDP, which is unreliable and may want
    to use retries
    """
    def __init__(self,
                 device: Device, outlet: str,
                 timeout: int, max_attempts: int, delay: int,
                 _id: int):
        """

        Args:
            device: Device object to interact with
            outlet: string representation of outlet
            timeout: timeout in seconds
            max_attempts: maximum number of attempts
            delay: delay inbetween attempts
            _id: command number (UUID)
        """
        super().__init__(device, outlet, _id)

        self.timeout = timeout
        self.max_attempts = max_attempts
        self.delay = delay

    async def send_command(self):
        """
        outward facing interface to run command

        Returns:

        """
        for __attempt in range(self.max_attempts):
            try:
                async with asyncio.timeout(self.timeout):
                    success, result = await self._invoke_device_command()

                if success:
                    self.cmd_success_handler(result)
                else:
                    self.cmd_failure_handler(result)

            except TimeoutError:
                self.cmd_timeout_handler()

        self.max_attempts_reached_handler()

    @abstractmethod
    def cmd_success_handler(self, result):
        ...

    @abstractmethod
    def cmd_failure_handler(self, result):
        ...

    @abstractmethod
    def cmd_timeout_handler(self):
        ...

    @abstractmethod
    def max_attempts_reached_handler(self):
        ...

class UdpGetOutletCommand(UdpCommand):
    """
    class representing a UDP command that is retrieving the state of an outlet
    """
    def __init__(self,
                 device: Device, outlet: str,
                 timeout: int, max_attempts:int, delay: int,
                 _id: int):
        """

        Args:
            device: Device object to interact with
            outlet: string representation of outlet
            timeout: timeout in seconds
            max_attempts: maximum number of attempts
            delay: delay inbetween attempts
            _id: command number (UUID)
        """
        super().__init__(device, outlet, timeout, max_attempts, delay, _id)

    async def _invoke_device_command(self):
        self.device.get_outlet_state(self.outlet)

    def cmd_success_handler(self, result):
        logger.error(f'Command #{self._id} passed when sending GET command to '
                     f'outlet {self.outlet} on device {self.device.name}. '
                     f'Command results: {result}')

    def cmd_failure_handler(self, result):
        logger.error(f'Command #{self._id} failed when attempting to send GET'
                     f'command to outlet {self.outlet} on device '
                     f'{self.device.name}. Command result: {result}')

    def cmd_timeout_handler(self):
        logger.error(f'Command #{self._id} timed out when attempting to send '
                     f'GET command to outlet {self.outlet} on device '
                     f'{self.device.name}.')

    def max_attempts_reached_handler(self):
        logger.error(f'Command #{self._id} has reached maximum number of '
                     f'retries when attempting to send GET command to outlet '
                     f'{self.outlet} on device {self.device.name}.')

class UdpSetOutletCommand(UdpCommand):
    """
    class representing a UDP command that is setting the state of an outlet
    """
    def __init__(self,
                 device: Device, outlet: str, state: any,
                 timeout: int, max_attempts:int, delay: int,
                 _id: int):
        """

        Args:
            device: Device object to interact with
            outlet: string representation of outlet
            state: desired state of outlet (pysnmp datatype)
            timeout: timeout in seconds
            max_attempts: maximum number of attempts
            delay: delay inbetween attempts
            _id: command number (UUID)
        """
        super().__init__(device, outlet, timeout, max_attempts, delay, _id)

        self.state = state

    async def _invoke_device_command(self):
        self.device.get_outlet_state(self.outlet)

    def cmd_success_handler(self, result):
        logger.error(f'Command #{self._id} passed when sending SET command to '
                     f'outlet {self.outlet} on device {self.device.name} with '
                     f'state of {self.state}. Command results: {result}')

    def cmd_failure_handler(self, result):
        logger.error(f'Command #{self._id} failed when attempting to send SET'
                     f'command to outlet {self.outlet} on device '
                     f'{self.device.name} with state {self.state}. Command '
                     f'result: {result}')

    def cmd_timeout_handler(self):
        logger.error(f'Command #{self._id} timed out when attempting to send '
                     f'SET command to outlet {self.outlet} on device '
                     f'{self.device.name} with state {self.state}.')

    def max_attempts_reached_handler(self):
        logger.error(f'Command #{self._id} has reached maximum number of '
                     f'retries when attempting to send SET command to outlet '
                     f'{self.outlet} on device {self.device.name} with state '
                     f'{self.state}.')

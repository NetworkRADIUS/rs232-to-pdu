"""
Contains device commands for unreliable transmission that may want to use
retries on command failures
"""

import asyncio
from abc import ABC, abstractmethod

import rs232_to_tripplite.logfactory as logfac
from rs232_to_tripplite.commands.base import BaseDeviceCommand
from rs232_to_tripplite.device import Device

logger = logfac.create_logger(__name__)


class CommandWithRetry(BaseDeviceCommand, ABC): # pylint: disable=(too-many-arguments
    """
    class representing a command used on UDP, which is unreliable and may want
    to use retries
    """
    def __init__(self, # pylint: disable=too-many-arguments
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
                    return True
                self.cmd_failure_handler(result)

            except TimeoutError:
                self.cmd_timeout_handler()

        self.max_attempts_reached_handler()
        return False

    @abstractmethod
    def cmd_success_handler(self, result): # pylint: disable=missing-function-docstring
        ...

    @abstractmethod
    def cmd_failure_handler(self, result): # pylint: disable=missing-function-docstring
        ...

    @abstractmethod
    def cmd_timeout_handler(self): # pylint: disable=missing-function-docstring
        ...

    @abstractmethod
    def max_attempts_reached_handler(self): # pylint: disable=missing-function-docstring
        ...


class GetCommandWithRetry(CommandWithRetry):
    """
    class representing a UDP command that is retrieving the state of an outlet
    """

    async def _invoke_device_command(self) -> tuple[bool, any]:
        return await self.device.get_outlet_state(self.outlet)

    def cmd_success_handler(self, result):
        logger.info(f'Command #{self._id} passed when sending GET command to '
                    f'outlet {self.outlet} on device {self.device.name}.')

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


class SetCommandWithRetry(CommandWithRetry):
    """
    class representing a UDP command that is setting the state of an outlet
    """

    def __init__(self, # pylint: disable=too-many-arguments
                 device: Device, outlet: str, state: any,
                 timeout: int, max_attempts: int, delay: int,
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

    async def _invoke_device_command(self) -> tuple[bool, any]:
        return await self.device.set_outlet_state(self.outlet, self.state)

    def cmd_success_handler(self, result):
        logger.info(f'Command #{self._id} passed when sending SET command to '
                    f'outlet {self.outlet} on device {self.device.name} with '
                    f'state of {self.state}.')

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

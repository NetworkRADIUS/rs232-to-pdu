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


class BaseDeviceCmd(ABC):
    """
    Abstract SNMP cmd class
    """

    def __init__(
            self,
            device: Device, target_outlet: str,
            max_attempts: int, delay: int, timeout: int,
            cmd_id: int
    ) -> None:

        self.device = device
        self.target_outlet = target_outlet

        self.max_attempts = max_attempts
        self.delay = delay
        self.timeout = timeout

        self.cmd_id = cmd_id

    @abstractmethod
    async def invoke_cmd(self) -> any:
        """
        Abstract method for running Device methods.

        This extra layer of abstraction is useful for dealing with get VS set
        functions, where set functions take in an extra state argument.

        Returns:
            current state of the outlet (after the cmd)
        """
        ...

    async def run_cmd(self) -> bool:
        """
        Control flow method that calls invoke_cmd and error/success handlers
        
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
                    return True

                self.handler_cmd_error(err_indicator, err_status, err_index,
                                       var_binds)
            except TimeoutError:
                self.handler_timeout_error()
            await asyncio.sleep(self.delay)

        # If for loop is exited, max retry attempts have been reached, thus
        # max attempt error has occurred
        self.handler_max_attempts_error()
        return False

    @abstractmethod
    def handler_cmd_success(self) -> None:
        ...

    @abstractmethod
    def handler_cmd_error(self, err_indicator, err_status, err_index,
                          var_binds):
        ...

    @abstractmethod
    def handler_timeout_error(self):
        ...

    @abstractmethod
    def handler_max_attempts_error(self):
        ...

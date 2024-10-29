"""
Class for creating and sending a SET command to change the power options for a 
power outlet.

Contains logic for timeout and retries on failures.

Author: Patrick Guo
Date: 2024-08-28
"""

import rs232_to_tripplite.logging.loggingfactory as nrlogfac
from rs232_to_tripplite.device import Device
from rs232_to_tripplite.requests.basedevicecmd import BaseDeviceCmd

logger = nrlogfac.create_logger(__name__)


class TrippliteDevicePowerChangeCmd(BaseDeviceCmd):
    """
    DeviceCmd class for setting power change cmds to Tripplite products
    """
    def __init__(
            self,
            device: Device, target_outlet: str, outlet_state: any,
            max_attempts: int, delay: int, timeout: int,
            cmd_id: int
    ) -> None:
        """

        Args:
            device: Device object
            target_outlet: outlet to set
            outlet_state: desired power state (in pysnmp datatype)
            timeout: timeout is seconds
            cmd_id: command ID
        """

        # Call parent class to initiate attributes
        super().__init__(
            device, target_outlet, max_attempts, delay, timeout, cmd_id
        )

        self.outlet_state = outlet_state

    async def invoke_cmd(self) -> any:
        return self.device.set_outlet_state(self.target_outlet,
                                            self.outlet_state)

    def handler_cmd_success(self):
        logger.info((f'Command #{self.cmd_id}: Successfully set device '
                     f'{self.device.name} outlet {self.target_outlet} to '
                     f'{self.outlet_state}')
                    )

    def handler_cmd_error(self, err_indicator, err_status, err_index,
                          var_binds):
        logger.error((f'Command #{self.cmd_id} Error when setting device '
                      f'{self.device.name} outlet {self.target_outlet} to '
                      f'{self.outlet_state}. Engine status: '
                      f'{err_indicator}. PDU status: {err_status}. MIB '
                      f'status: {var_binds[err_index] if var_binds else None}'
                      )
                     )

    def handler_timeout_error(self):
        logger.error((f'Command #{self.cmd_id}: Timed-out setting device '
                      f'{self.device.name} outlet {self.target_outlet} to '
                      f'{self.outlet_state}')
                     )

    def handler_max_attempts_error(self):
        logger.error((f'Command #{self.cmd_id}: Max retry attempts setting '
                      f'device {self.device.name} outlet {self.target_outlet} '
                      f'to {self.outlet_state}')
                     )

"""
Class for creating and sending a GET command to perform a health check of the
PDU SNMP agent

Contains logic for timeout and retries on failures.

Author: Patrick Guo
Date: 2024-08-28
"""

import rs232_to_tripplite.logging.loggingfactory as nrlogfac
from rs232_to_tripplite.device import Device
from rs232_to_tripplite.requests.basedevicecmd import BaseDeviceCmd

logger = nrlogfac.create_logger(__name__)


class TrippliteDeviceHealthcheckCmd(BaseDeviceCmd):
    """
    DeviceCmd class for sending healthcheck to Tripplite products
    """
    def __init__(
            self,
            device: Device, target_outlet: str, timeout: int,
            cmd_id: int
    ) -> None:
        """

        Args:
            device: Device object
            target_outlet: outlet to check
            timeout: timeout in seconds
            cmd_id: command ID
        """

        # Call parent class to initiate attributes
        super().__init__(device, target_outlet, 0, 0, timeout, cmd_id)

    async def invoke_cmd(self) -> any:
        return self.device.get_outlet_state(self.target_outlet)

    def handler_cmd_success(self):
        logger.info((f'Command #{self.cmd_id}: PDU health check passed for '
                     f'device {self.device.name}')
                    )

    def handler_cmd_error(self, err_indicator, err_status, err_index,
                          var_binds):
        logger.error((f'Command #{self.cmd_id}: Error when performing health '
                      f'check for device {self.device.name}. Engine status: '
                      f'{err_indicator}. PDU status: {err_status}. MIB '
                      f'status: {var_binds[err_index] if var_binds else None}')
                     )

    def handler_timeout_error(self):
        logger.error((f'Command #{self.cmd_id}: Timed-out on health check for '
                      f'device {self.device.name}')
                     )

    def handler_max_attempts_error(self):
        # Healthcheck don't do retries so no error logging for this
        return

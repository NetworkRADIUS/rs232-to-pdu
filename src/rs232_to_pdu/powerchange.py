"""
rs232-to-pdu
Copyright (C) 2024 InkBridge Networks (legal@inkbridge.io)

rs232-to-pdu © 2024 by InkBridge is licensed under CC BY-NC 4.0. To view a copy
of this license, visit https://creativecommons.org/licenses/by-nc/4.0/
"""
import asyncio
import functools
import logging

logger = logging.getLogger(__name__)


class Powerchange:  # pylint: disable=too-few-public-methods
    """
    object to push task onto the queue to perform power change
    """
    def __init__(  # pylint: disable=too-many-arguments
            self, event_loop, task_queue, device, outlet, state, cy_delay
    ):
        self.__device = device
        self.__outlet = outlet

        # checks if manual cy toggle is needed
        if state == 'cy' and 'cy' not in device.power_states:
            action = functools.partial(self.__cy, cy_delay)
        else:
            action = functools.partial(self.__send, state)

        event_loop.create_task(task_queue.enqueue(action))

    async def __send(self, state):
        logger.info(f'Power check setting outlet {self.__outlet} of '
                    f'device {self.__device.name} to state {state}.')
        success = await self.__device.transport.outlet_state_set(
            self.__outlet, self.__device.power_states[state]
        )
        logger.info(f'Power check {"passed" if success else "failed"}.')

    async def __cy(self, delay):
        # manual cy toggle
        await self.__send('of')
        await asyncio.sleep(delay)
        await self.__send('on')

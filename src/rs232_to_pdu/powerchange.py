import asyncio
import logging
import functools

logger = logging.getLogger(__name__)

class Powerchange:
    def __init__(self,
                 event_loop, task_queue, device, outlet, state, cy_delay):
        self.__device = device
        self.__outlet = outlet

        if state == 'cy' and 'cy' not in device.power_states:
            action = functools.partial(self.__cy, cy_delay)
        else:
            action = functools.partial(self.__send, state)

        event_loop.event_loop.create_task(task_queue.enqueue(action))

    async def __send(self, state):
        logger.info(f'Power check setting outlet {self.__outlet} of '
                    f'device {self.__device.name} to state {state}.')
        success = await self.__device.transport.outlet_state_set(
            self.__outlet, self.__device.power_states[state]
        )
        logger.info(f'Power check {"passed" if success else "failed"}.')

    async def __cy(self, delay):
        await self.__send('of')
        await asyncio.sleep(delay)
        await self.__send('on')

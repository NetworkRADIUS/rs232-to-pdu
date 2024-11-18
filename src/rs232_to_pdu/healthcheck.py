import functools
import logging

from rs232_to_pdu.eventloop import EventLoop

logger = logging.getLogger(__name__)

class Healthcheck:
    def __init__(self, event_loop: EventLoop, task_queue, device, frequency):
        self.event_loop = event_loop
        self.task_queue = task_queue
        self.device = device
        self.frequency = frequency

        self.__timer()

    def __timer(self):
        self.event_loop.event_loop.create_task(
            self.task_queue.enqueue(functools.partial(self.__send))
        )

    async def __send(self):
        logger.info(f'Healthcheck retrieving outlet '
                    f'{self.device.outlets[0]} of device {self.device.name}')
        success = await self.device.transport.outlet_state_get(
            self.device.outlets[0]
        )
        logger.info(f'Healthcheck {"passed" if success else "failed"}')
        self.event_loop.event_loop.call_later(self.frequency, self.__timer)

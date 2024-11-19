"""
Copyright (C) 2024 InkBridge Networks (legal@inkbridge.io)

This software may not be redistributed in any form without the prior
written consent of InkBridge Networks.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
SUCH DAMAGE.
"""
import functools
import logging
from asyncio import BaseEventLoop

from rs232_to_pdu.device import Device
from rs232_to_pdu.taskqueue import TaskQueue

logger = logging.getLogger(__name__)


class Healthcheck:  # pylint: disable=too-few-public-methods
    """
    object that queues partials (closures) onto a queue on a regular timer
    """
    def __init__(
            self, event_loop: BaseEventLoop, task_queue: TaskQueue,
            device: Device, frequency: int
    ):
        self.event_loop = event_loop
        self.task_queue = task_queue
        self.device = device
        self.frequency = frequency

        # starts the queueing process
        self.__timer()

    def __timer(self):
        self.event_loop.create_task(
            self.task_queue.enqueue(functools.partial(self.__send))
        )

    async def __send(self):
        logger.info(f'Healthcheck retrieving outlet '
                    f'{self.device.outlets[0]} of device {self.device.name}')
        success = await self.device.transport.outlet_state_get(
            self.device.outlets[0]
        )
        logger.info(f'Healthcheck {"passed" if success else "failed"}')
        # after receiving response, queue new task after pre configured delay
        self.event_loop.call_later(self.frequency, self.__timer)

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
import asyncio
import functools
import logging

logger = logging.getLogger(__name__)


class Powerchange:
    """
    object to push task onto the queue to perform power change
    """
    def __init__(self,
                 event_loop, task_queue, device, outlet, state, cy_delay):
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

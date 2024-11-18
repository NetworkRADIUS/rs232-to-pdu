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

Entry point for rs-232 to SNMP converter script

Author: Patrick Guo
Date: 2024-08-13
"""
import asyncio
import logging
import pathlib
from asyncio import SelectorEventLoop

import systemd_watchdog

import serial
import yaml
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from rs232_to_pdu import eventloop
from rs232_to_pdu.healthcheck import Healthcheck
from rs232_to_pdu.parsers.base import ParseError
from rs232_to_pdu.parsers.kvmseq import ParserKvmSequence
from rs232_to_pdu.powerchange import Powerchange
from rs232_to_pdu.taskqueue import TaskQueue
from rs232_to_pdu.device import FactoryDevice
from rs232_to_pdu.serialconn import SerialConn


logger = logging.getLogger(__name__)

class CmdBuffer:
    def __init__(self):
        self.data = ''
        # cmd_counter
        self.counter = 0

if __name__ == '__main__':
    # Read and setup configs
    config_path = pathlib.Path('config.yaml')
    with open(config_path, 'r', encoding='utf-8') as fileopen:
        config = yaml.load(fileopen, Loader=yaml.FullLoader)
    devices = FactoryDevice().devices_from_configs(config)

    event_loop = eventloop.EventLoop()
    task_queue = TaskQueue(event_loop)
    scheduler = AsyncIOScheduler(event_loop=event_loop.event_loop)

    systemd_wd = systemd_watchdog.watchdog()
    scheduler.add_job(
        systemd_wd.notify, 'interval', seconds=systemd_wd.timeout / 2e6
    )

    buffer = CmdBuffer()
    parser = ParserKvmSequence()

    def serial_reader(_conn: serial.Serial):
        buffer.data += _conn.read(_conn.in_waiting).decode('utf-8')

        chars_read = 0
        for cursor, char in enumerate(buffer.data):
            if char != '\r':
                continue

            try:
                tokens = parser.parse(''.join(buffer.data[chars_read:cursor + 1]))
            except ParseError:
                logger.warning(f'Parser failed to parse {"".join(buffer.data)}')
            else:
                if tokens[0] == 'quit' or tokens[0] == '':
                    logger.info('Quite or empty sequence detected')
                else:
                    device = devices[f'{int(tokens[1]):03d}']
                    Powerchange(
                        event_loop.event_loop, task_queue, device,
                        f'{int(tokens[2]):03d}', tokens[0],
                        config['power_states']['cy_delay']
                    )

                chars_read = cursor + 1

        buffer.data = buffer.data[:chars_read]

    conn = SerialConn(event_loop, config['serial']['device'], serial_reader)
    conn.open()

    task_queue.create_task()
    scheduler.start()

    for device in devices.values():
        Healthcheck(
            event_loop, task_queue, device, config['healthcheck']['frequency']
        )
        break

    try:
        event_loop.event_loop.run_forever()
    except KeyboardInterrupt:
        conn.close()
        scheduler.shutdown()
        event_loop.event_loop.stop()
        event_loop.event_loop.close()

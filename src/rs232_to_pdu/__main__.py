"""
rs232-to-pdu
Copyright (C) 2024 InkBridge Networks (legal@inkbridge.io)

rs232-to-pdu © 2024 by InkBridge is licensed under CC BY-NC 4.0. To view a copy
of this license, visit https://creativecommons.org/licenses/by-nc/4.0/

Entry point for rs-232 to SNMP converter script
"""
import logging
import pathlib

import serial
import systemd_watchdog
import yaml
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from rs232_to_pdu.eventloop import EventLoop
from rs232_to_pdu.device import FactoryDevice
from rs232_to_pdu.healthcheck import Healthcheck
from rs232_to_pdu.parsers.base import ParseError
from rs232_to_pdu.parsers.kvmseq import ParserKvmSequence
from rs232_to_pdu.powerchange import Powerchange
from rs232_to_pdu.serialconn import SerialConn
from rs232_to_pdu.taskqueue import TaskQueue

logger = logging.getLogger(__name__)

class CmdBuffer:  # pylint: disable=too-few-public-methods
    """
    class to store a buffer

    Used because strings do not play nicely in closures.
    By wrapping the string as an attribute in the class, the string becomes
    mutable. (closures seem to pass variables by reference in python, and
    strings are immutable)
    """
    def __init__(self):
        self.data = ''

class Main:  # pylint: disable=too-few-public-methods
    """
    main class containing logic flow
    """
    def __init__(self):
        # Read and setup configs
        config_path = pathlib.Path('etc', 'rs232-to-pdu', 'config.yaml')
        with open(config_path, 'r', encoding='utf-8') as fileopen:
            config = yaml.load(fileopen, Loader=yaml.FullLoader)
        devices = FactoryDevice().devices_from_configs(config)

        # initializes event-loop and objects requiring it
        event_loop = EventLoop()
        task_queue = TaskQueue(event_loop.loop)
        scheduler = AsyncIOScheduler(event_loop=event_loop.loop)

        # initializes systemd watchdog and setups the notification scheduler
        systemd_wd = systemd_watchdog.watchdog()
        scheduler.add_job(
            systemd_wd.notify, 'interval', seconds=systemd_wd.timeout / 2e6
        )

        # initializes buffer and parser objects
        buffer = CmdBuffer()
        parser = ParserKvmSequence()

        # closure function for serial connection upon reading new contents
        def serial_reader(_conn: serial.Serial):
            """
            reads the serial connection when data is in waiting
            Args:
                _conn: serial connection

            Returns:

            """
            buffer.data += _conn.read(_conn.in_waiting).decode('utf-8')

            # variable representing number of chars read from buffer
            chars_read = 0
            for cursor, char in enumerate(buffer.data):
                # skips char if not a sequence terminating string char
                if char != '\r':
                    continue

                try:
                    tokens = parser.parse(
                        ''.join(buffer.data[chars_read:cursor + 1]))
                except ParseError:
                    logger.warning(
                        f'Parser failed to parse {"".join(buffer.data)}')
                else:
                    if tokens[0] == 'quit' or tokens[0] == '':
                        logger.info('Quite or empty sequence detected')
                    else:
                        device = devices[f'{int(tokens[1]):03d}']
                        Powerchange(
                            event_loop.loop, task_queue, device,
                            f'{int(tokens[2]):03d}', tokens[0],
                            config['power_states']['cy_delay']
                        )

                    chars_read = cursor + 1

            # removes read and parsed portion of buffer
            buffer.data = buffer.data[chars_read:]

        # initializes the serial connection and opens it
        conn = SerialConn(event_loop, config['serial']['device'],
                          serial_reader)
        conn.open()

        # starts the dequeue-ing task and the scheduler (healthcheck and
        # systemd notifies)
        task_queue.create_task()
        scheduler.start()

        # creates healthcheck object for each device
        for _device in devices.values():
            Healthcheck(
                event_loop.loop, task_queue, _device,
                config['healthcheck']['frequency']
            )
            break

        # runs loop forever until a keyboard interrupt
        try:
            # this line of code is blocking :(
            event_loop.loop.run_forever()
        except KeyboardInterrupt:
            conn.close()
            scheduler.shutdown()
            event_loop.loop.stop()
            event_loop.loop.close()

if __name__ == '__main__':
    Main()

"""
Contains class that acts as the queue of commands to send.

Class is needed to prevent overloading SNMP agent with too many commands at
once. This can cause commands to be timed-out.

Uses priority queue to prioritize health check commands

Author: Patrick Guo
Date: 2024-08-26
"""
import asyncio

from sersnmprequests.basesnmpcmd import BaseSnmpCmd


class SnmpCmdRunner:
    """
    Class that places commands in a queue and runs them one after another
    """
    def __init__(self) -> None:
        # Initializes an priority queue with no size limit
        self.queue = asyncio.PriorityQueue()

        # Initializes the priority counter to 0. To be used when setting
        # priority of new items
        self.prio_counter = 0


    async def put_into_queue(self,
                             snmp_cmd: BaseSnmpCmd,
                             high_prio: bool = False) -> None:
        """
        Puts an command item into the queue.

        Can set priority to be high or low.
        New high priority items have highest priority (run first)
        New low priority items have lowest priority (run last)

        Args:
            snmp_cmd (BaseSnmpCmd): command object to be stored in queue
            high_prio (bool): whether the command should be run first or last
        """
        # priority is either positive or negative depending on high/low prio
        priority = -self.prio_counter if high_prio else self.prio_counter
        self.prio_counter += 1

        # puts item into queue
        await self.queue.put((priority, snmp_cmd))

    async def queue_processor(self, event_loop: asyncio.BaseEventLoop):
        """
        Gets top priority item from queue and runs the command

        Args:
            event_loop (BaseEventLoop): event loop that is expected to keep
                                        producing commands
        """

        # as long as the event loop is running, we should be expecting new
        # items to be put into the queue
        while event_loop.is_running():

            # retrieve next item from queue and run the command
            # Will not grab next item until the previous command has been
            # completed
            priority, snmp_cmd = await self.queue.get()
            success = await snmp_cmd.run_cmd()

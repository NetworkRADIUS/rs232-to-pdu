import unittest
import asyncio

from sersnmprequests.snmpcmdrunner import SnmpCmdRunner
from sersnmprequests.basesnmpcmd import BaseSnmpCmd


class DummySnmpCmd(BaseSnmpCmd):
    """
    Dummy SNMP Cmd class for testing purposes

    Doesn't send any requests
    """
    async def run_cmd(self):
        await asyncio.sleep(0)


class TestCmdRunner(unittest.TestCase):
    """
    Test cases for the command runner (priority queue)
    """
    @classmethod
    def setUp(cls):
        """
        Setups the event loop and cmd_runner object
        """
        cls.event_loop = asyncio.new_event_loop()
        cls.cmd_runner = SnmpCmdRunner()

    @classmethod
    def tearDown(cls):
        """
        Closes the event loop as tear down
        """
        cls.event_loop.close()

    def create_dummy_cmd(self):
        """
        Helper function to create a dummy SNMP cmd
        """
        return DummySnmpCmd(
            None, None, None, None, None, None,
            None, None, None, None, None, None, None
        )

    def test_add_to_queue(self):
        """
        Test case to test that queue size is increased after placing item in it
        """
        pre_queue_size = self.cmd_runner.queue.qsize()

        dummy_cmd = self.create_dummy_cmd()
        self.event_loop.run_until_complete(
            self.cmd_runner.put_into_queue(dummy_cmd)
        )

        # assert that queue size has increased by exactly 1
        self.assertEqual(self.cmd_runner.queue.qsize(), pre_queue_size + 1)
    
    def test_add_high_prio_to_queue(self):
        """
        Test case to ensure that high priority items are run first
        """
        high_prio_dummy_cmd = self.create_dummy_cmd()
        low_prio_dummy_cmd = self.create_dummy_cmd()

        # place low priority item first
        self.event_loop.run_until_complete(self.cmd_runner.put_into_queue(low_prio_dummy_cmd, False))
        self.event_loop.run_until_complete(self.cmd_runner.put_into_queue(high_prio_dummy_cmd, True))

        # .get() returns (priority, item), thus the [1] at the end
        next_cmd_in_queue = self.event_loop.run_until_complete(self.cmd_runner.queue.get())[1]

        # assert that the item we got was the high priority item
        self.assertIs(next_cmd_in_queue, high_prio_dummy_cmd)
    
    def test_add_low_prio_to_queue(self):
        """
        Test case to ensure that low priority items are not run first
        """
        high_prio_dummy_cmd = self.create_dummy_cmd()
        low_prio_dummy_cmd = self.create_dummy_cmd()

        # place high priority item first
        self.event_loop.run_until_complete(self.cmd_runner.put_into_queue(high_prio_dummy_cmd, True))
        self.event_loop.run_until_complete(self.cmd_runner.put_into_queue(low_prio_dummy_cmd, False))

        next_cmd_in_queue = self.event_loop.run_until_complete(self.cmd_runner.queue.get())[1]

        # assert that the item we got was not the low priority item
        self.assertIsNot(next_cmd_in_queue, low_prio_dummy_cmd)

    def test_process_queue(self):
        """
        Test case to ensure that the queue will consume items when they appear
        """
        pre_queue_size = self.cmd_runner.queue.qsize()

        dummy_cmd = self.create_dummy_cmd()

        # begin listening for new items in queue
        self.event_loop.create_task(self.cmd_runner.queue_processor(self.event_loop))

        # put new item into queue
        self.event_loop.run_until_complete(self.cmd_runner.put_into_queue(dummy_cmd))

        # item in queue should be instantly consumed
        post_queue_size = self.cmd_runner.queue.qsize()

        # assert that the queue size has not changed (item added and consumed)
        self.assertEqual(post_queue_size, pre_queue_size)

"""
Contains tests for the DeviceCmdRunner class
"""

import unittest
import asyncio
from rs232_to_tripplite.rs232tripplite import QueueRunner # pylint: disable=import-error


async def dummy_sleep(timeout):
    """
    Helper func to use async sleep
    Args:
        timeout: timeout in seconds

    Returns:

    """
    await asyncio.sleep(timeout)


class TestCmdRunner(unittest.TestCase):
    """
    Test cases for the command runner (priority queue)
    """
    def setUp(self):
        """
        Setups the event loop and cmd_runner object
        """
        self.event_loop = asyncio.new_event_loop()
        self.cmd_runner = QueueRunner()

    def tearDown(self):
        """
        Closes the event loop as tear down
        """
        self.event_loop.close()


    def test_add_to_queue(self):
        """
        Test case to test that queue size is increased after placing item in it
        """
        pre_queue_size = self.cmd_runner.queue.qsize()

        self.event_loop.run_until_complete(
            self.cmd_runner.enqueue(lambda: None)
        )

        # assert that queue size has increased by exactly 1
        self.assertEqual(self.cmd_runner.queue.qsize(), pre_queue_size + 1)

    def test_add_high_prio_to_queue(self):
        """
        Test case to ensure that high priority items are run first
        """
        high_prio_lambda = lambda: None
        low_prio_lambda = lambda: None

        # place low priority item first
        self.event_loop.run_until_complete(
            self.cmd_runner.enqueue(low_prio_lambda, False)
        )
        self.event_loop.run_until_complete(
            self.cmd_runner.enqueue(high_prio_lambda, True)
        )

        # .get() returns (priority, item), thus the [1] at the end
        next_cmd_in_queue = self.event_loop.run_until_complete(
            self.cmd_runner.queue.get()
        )[1]

        # assert that the item we got was the high priority item
        self.assertIs(next_cmd_in_queue, high_prio_lambda)

    def test_add_low_prio_to_queue(self):
        """
        Test case to ensure that low priority items are not run first
        """
        high_prio_lambda = lambda: None
        low_prio_lambda = lambda: None

        # place high priority item first
        self.event_loop.run_until_complete(
            self.cmd_runner.enqueue(high_prio_lambda, True)
        )
        self.event_loop.run_until_complete(
            self.cmd_runner.enqueue(low_prio_lambda, False)
        )

        next_cmd_in_queue = self.event_loop.run_until_complete(
            self.cmd_runner.queue.get()
        )[1]

        # assert that the item we got was not the low priority item
        self.assertIsNot(next_cmd_in_queue, low_prio_lambda)

    def test_process_queue(self):
        """
        Test case to ensure that the queue will consume items when they appear
        """
        pre_queue_size = self.cmd_runner.queue.qsize()

        # begin listening for new items in queue
        self.event_loop.create_task(
            self.cmd_runner.dequeue(self.event_loop)
        )

        # put new item into queue
        self.event_loop.run_until_complete(
            self.cmd_runner.enqueue(lambda: None, )
        )

        self.event_loop.run_until_complete(dummy_sleep(5))

        # item in queue should be instantly consumed
        post_queue_size = self.cmd_runner.queue.qsize()

        # assert that the queue size has not changed (item added and consumed)
        self.assertEqual(post_queue_size, pre_queue_size)

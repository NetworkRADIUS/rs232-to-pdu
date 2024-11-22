"""
rs232-to-pdu
Copyright (C) 2024 InkBridge Networks (legal@inkbridge.io)

rs232-to-pdu © 2024 by InkBridge is licensed under CC BY-NC 4.0. To view a copy
of this license, visit https://creativecommons.org/licenses/by-nc/4.0/

Contains tests for the DeviceCmdRunner class
"""

import unittest
import asyncio
from rs232_to_pdu.taskqueue import TaskQueue # pylint: disable=import-error


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
        self.task_queue = TaskQueue(self.event_loop)

    def tearDown(self):
        """
        Closes the event loop as tear down
        """
        self.event_loop.close()


    def test_add_to_queue(self):
        """
        Test case to test that queue size is increased after placing item in it
        """
        pre_queue_size = self.task_queue.queue.qsize()

        self.event_loop.run_until_complete(
            self.task_queue.enqueue(lambda: None)
        )

        # assert that queue size has increased by exactly 1
        self.assertEqual(self.task_queue.queue.qsize(), pre_queue_size + 1)

    def test_add_high_prio_to_queue(self):
        """
        Test case to ensure that high priority items are run first
        """
        high_prio_lambda = lambda: None  #pylint: disable=unnecessary-lambda-assignment
        low_prio_lambda = lambda: None  #pylint: disable=unnecessary-lambda-assignment

        # place low priority item first
        self.event_loop.run_until_complete(
            self.task_queue.enqueue(low_prio_lambda, False)
        )
        self.event_loop.run_until_complete(
            self.task_queue.enqueue(high_prio_lambda, True)
        )

        # .get() returns (priority, item), thus the [1] at the end
        next_cmd_in_queue = self.event_loop.run_until_complete(
            self.task_queue.queue.get()
        )[1]

        # assert that the item we got was the high priority item
        self.assertIs(next_cmd_in_queue, high_prio_lambda)

    def test_add_low_prio_to_queue(self):
        """
        Test case to ensure that low priority items are not run first
        """
        high_prio_lambda = lambda: None  #pylint: disable=unnecessary-lambda-assignment
        low_prio_lambda = lambda: None  #pylint: disable=unnecessary-lambda-assignment

        # place high priority item first
        self.event_loop.run_until_complete(
            self.task_queue.enqueue(high_prio_lambda, True)
        )
        self.event_loop.run_until_complete(
            self.task_queue.enqueue(low_prio_lambda, False)
        )

        next_cmd_in_queue = self.event_loop.run_until_complete(
            self.task_queue.queue.get()
        )[1]

        # assert that the item we got was not the low priority item
        self.assertIsNot(next_cmd_in_queue, low_prio_lambda)

    def test_process_queue(self):
        """
        Test case to ensure that the queue will consume items when they appear
        """
        pre_queue_size = self.task_queue.queue.qsize()

        # begin listening for new items in queue
        self.task_queue.create_task()

        # put new item into queue
        self.event_loop.run_until_complete(
            self.task_queue.enqueue(lambda: None, )
        )

        self.event_loop.run_until_complete(dummy_sleep(5))

        # item in queue should be instantly consumed
        post_queue_size = self.task_queue.queue.qsize()

        # assert that the queue size has not changed (item added and consumed)
        self.assertEqual(post_queue_size, pre_queue_size)

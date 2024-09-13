import unittest
import asyncio

from sersnmprequests.snmpcmdrunner import SnmpCmdRunner
from sersnmprequests.basesnmpcmd import BaseSnmpCmd


class DummySnmpCmd(BaseSnmpCmd):
    async def run_cmd(self):
        await asyncio.sleep(0)


class TestCmdRunner(unittest.TestCase):
    
    @classmethod
    def setUp(cls):
        cls.event_loop = asyncio.new_event_loop()
        cls.cmd_runner = SnmpCmdRunner()

    @classmethod
    def tearDown(cls):
        cls.event_loop.close()

    def create_dummy_cmd(self):
        return DummySnmpCmd(
            None, None, None, None, None, None,
            None, None, None, None, None, None, None
        )

    def test_add_to_queue(self):
        pre_queue_size = self.cmd_runner.queue.qsize()

        dummy_cmd = self.create_dummy_cmd()
        self.event_loop.run_until_complete(self.cmd_runner.put_into_queue(dummy_cmd))
        self.assertEqual(self.cmd_runner.queue.qsize(), pre_queue_size + 1)
    
    def test_add_high_prio_to_queue(self):
        high_prio_dummy_cmd = self.create_dummy_cmd()
        low_prio_dummy_cmd = self.create_dummy_cmd()

        self.event_loop.run_until_complete(self.cmd_runner.put_into_queue(low_prio_dummy_cmd, False))
        self.event_loop.run_until_complete(self.cmd_runner.put_into_queue(high_prio_dummy_cmd, True))

        next_cmd_in_queue = self.event_loop.run_until_complete(self.cmd_runner.queue.get())[1]

        self.assertEqual(next_cmd_in_queue, high_prio_dummy_cmd)
    
    def test_add_low_prio_to_queue(self):
        high_prio_dummy_cmd = self.create_dummy_cmd()
        low_prio_dummy_cmd = self.create_dummy_cmd()

        self.event_loop.run_until_complete(self.cmd_runner.put_into_queue(high_prio_dummy_cmd, True))
        self.event_loop.run_until_complete(self.cmd_runner.put_into_queue(low_prio_dummy_cmd, False))

        next_cmd_in_queue = self.event_loop.run_until_complete(self.cmd_runner.queue.get())[1]

        self.assertNotEqual(next_cmd_in_queue, low_prio_dummy_cmd)

    def test_process_queue(self):
        pre_queue_size = self.cmd_runner.queue.qsize()

        dummy_cmd = self.create_dummy_cmd()
        self.event_loop.create_task(self.cmd_runner.queue_processor(self.event_loop))
        self.event_loop.run_until_complete(self.cmd_runner.put_into_queue(dummy_cmd))

        post_queue_size = self.cmd_runner.queue.qsize()
        self.assertEqual(post_queue_size, pre_queue_size)

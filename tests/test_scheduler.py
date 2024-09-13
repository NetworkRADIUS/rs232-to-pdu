import unittest
import asyncio


from sersnmpscheduler.sersnmpscheduler import ListenerScheduler


class TestScheduler(unittest.TestCase):
    @classmethod
    def setUp(cls):
        cls.event_loop = asyncio.new_event_loop()
        cls.scheduler = ListenerScheduler(cls.event_loop)
        cls.scheduler.start()

    @classmethod
    def tearDown(cls):
        cls.scheduler.shutdown()

    def dummy_func(self):
        self.assertTrue(True)
    
    async def dummy_wait(self, wait_time):
        await asyncio.sleep(wait_time)

    def test_start_healthcheck_job(self):
        self.scheduler.start_healthcheck_job(self.dummy_func)
        self.assertIn(self.scheduler.jobs['healthcheck'], self.scheduler.scheduler.get_jobs())

    def test_start_reconnect_job(self):
        self.scheduler.start_reconnect_job(self.dummy_func)
        self.assertIn(self.scheduler.jobs['reconnect'], self.scheduler.scheduler.get_jobs())

    def test_remove_reconnect_job(self):
        self.scheduler.start_reconnect_job(self.dummy_func)
        self.scheduler.remove_reconnect_job()
        self.assertNotIn(self.scheduler.jobs['reconnect'], self.scheduler.scheduler.get_jobs())
    
    def test_start_systemd_wd_job(self):
        self.scheduler.start_systemd_notify(self.dummy_func, 5)
        self.assertIn(self.scheduler.jobs['systemd_notify'], self.scheduler.scheduler.get_jobs())
    
    def test_scheduler_job_called(self):
        self.scheduler.start_healthcheck_job(self.dummy_func, 5)
        self.event_loop.run_until_complete(self.dummy_wait(5))

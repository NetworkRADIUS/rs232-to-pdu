import unittest
import asyncio


from sersnmpscheduler.sersnmpscheduler import ListenerScheduler


class TestScheduler(unittest.TestCase):
    """
    Test cases for testing the scheduler
    """
    @classmethod
    def setUp(cls):
        """
        Initiates the event loop and scheduler as setup
        """
        cls.event_loop = asyncio.new_event_loop()
        cls.scheduler = ListenerScheduler(cls.event_loop)
        cls.scheduler.start()

        # variable for checking if scheduled function ran
        cls.changed = False

    @classmethod
    def tearDown(cls):
        """
        Stops the event loop and scheduler as tear down
        """
        cls.event_loop.stop()
        cls.scheduler.shutdown()

    def dummy_func(self):
        """
        Dummy function that should be triggered by the scheduler
        """
        self.changed = True

    async def dummy_wait(self, wait_time):
        """
        Helpder function to asynchronously wait
        """
        await asyncio.sleep(wait_time)

    def test_start_healthcheck_job(self):
        """
        check that the function to start adding healthcheck jobs is functional
        """
        # start the healthcheck job
        self.scheduler.start_healthcheck_job(self.dummy_func)

        # check that the job is in the scheduler's list of jobs
        self.assertIn(self.scheduler.jobs['healthcheck'],
                      self.scheduler.scheduler.get_jobs())

    def test_start_reconnect_job(self):
        """
        check that the function to start adding reconnect jobs is functional
        """
        # start the reconnect job
        self.scheduler.start_reconnect_job(self.dummy_func)

        # check that the job is in the scheduler's list of jobs
        self.assertIn(self.scheduler.jobs['reconnect'],
                      self.scheduler.scheduler.get_jobs())

    def test_remove_reconnect_job(self):
        """
        Check that the function to remove reconnect jobs is functional
        """
        # start and remove the reconnect job
        self.scheduler.start_reconnect_job(self.dummy_func)
        self.scheduler.remove_reconnect_job()

        # check that job is not in the scheduler's list of jobs
        self.assertNotIn(self.scheduler.jobs['reconnect'],
                         self.scheduler.scheduler.get_jobs())

    def test_start_systemd_wd_job(self):
        """
        Check that the function to start adding systemd wd notifications is
        functional
        """
        self.scheduler.start_systemd_notify(self.dummy_func, 5)
        self.assertIn(self.scheduler.jobs['systemd_notify'],
                      self.scheduler.scheduler.get_jobs())

    def test_scheduler_job_called(self):
        """
        Check that the scheduler actually calls the scheduled function
        """
        # Start the job
        self.scheduler.start_healthcheck_job(self.dummy_func, 5)

        # wait for the scheduler to call the function
        self.event_loop.run_until_complete(self.dummy_wait(5))

        # check that the function has been called (variable has been changed)
        self.assertTrue(self.changed)

from apscheduler.schedulers.asyncio import AsyncIOScheduler

class ListenerScheduler:
    def __init__(self, event_loop):
        self.scheduler = AsyncIOScheduler(event_loop=event_loop)

        self.jobs = {}
    
    def start_healthcheck_job(self, add_hc_to_queue_func, frequency=5):
        self.jobs['healthcheck'] = self.scheduler.add_job(
            add_hc_to_queue_func, 'interval', seconds=frequency
        )
    
    def start_reconnect_job(self, reconnect_func, frequency=5):
        self.jobs['reconnect'] = self.scheduler.add_job(
            reconnect_func, 'interval', seconds=frequency
        )
    
    def start_systemd_notify(self, notify_func, frequency):
        self.jobs['systemd_notify'] = self.scheduler.add_job(
            notify_func, 'interval', seconds=frequency
        )
    
    def remove_reconnect_job(self):
        self.jobs['reconnect'].remove()

    def start(self):
        self.scheduler.start()
    
    def shutdown(self, wait=False):
        self.scheduler.shutdown(wait)
        
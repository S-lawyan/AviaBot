from apscheduler.schedulers.async_ import AsyncScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from scheduler.direction_update import DirectionUpdate
from scheduler.direction_update import reset_sent_posts
import asyncio

class ServiceScheduler:
    def __init__(self, scheduler: AsyncScheduler, direction_update: DirectionUpdate):
        self.direction_update = direction_update
        self.scheduler = scheduler
        self.scheduler_update_directions = None


    async def start(self):
        await self.scheduler.start_in_background()
        await self._schedule_direction_updater()
        await self.scheduler.add_schedule(
            reset_sent_posts, CronTrigger(hour=11, minute=30) # On ubuntu as 8:30 pm MSK
        )

    async def _schedule_direction_updater(self):
        while True:
            await self.direction_update.update()

        # if self.scheduler_update_directions:
        #     await self.scheduler.remove_schedule(self.scheduler_update_directions)
        # trigger_interval  = 10
        # db_interval = "seconds"  # "minutes" or "seconds"
        # if db_interval == "minutes":
        #     trigger = IntervalTrigger(minutes=trigger_interval)
        # else:
        #     trigger = IntervalTrigger(seconds=trigger_interval)
        # self.scheduler_update_directions = await self.scheduler.add_schedule(
        #     self.direction_update.update, trigger
        # )

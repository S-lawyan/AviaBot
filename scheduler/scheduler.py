import asyncio
import random
from datetime import datetime
from datetime import timedelta
from apscheduler.schedulers.async_ import AsyncScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from database.mysqldb import database
from avia_api.models import Ticket
from avia_api.adapter import TicketsApi
from scheduler.direction_update import DirectionUpdate
from scheduler.direction_update import reset_sent_posts



class ServiceScheduler:
    def __init__(
            self,
            scheduler: AsyncScheduler,
            direction_update: DirectionUpdate
    ):
        self.direction_update = direction_update
        self.scheduler = scheduler
        self.scheduler_update_directions = None

    async def start(self):
        await self.scheduler.start_in_background()
        await self._schedule_direction_updater()
        await self.scheduler.add_schedule(
            reset_sent_posts, CronTrigger(hour=0, minute=1)
        )
        # asyncio.create_task(self._monitor_settings_change())

    async def _schedule_direction_updater(self):
        if self.scheduler_update_directions:
            await self.scheduler.remove_schedule(self.scheduler_update_directions)
        db_trigger = 10
        db_interval = "minutes" # "minutes" or "seconds"
        if db_interval == "minutes":
            trigger = IntervalTrigger(minutes=db_trigger)
        else:
            trigger = IntervalTrigger(seconds=db_trigger)
            # trigger = DateTrigger(run_time=datetime.now() + timedelta(seconds=5))
        self.scheduler_update_directions = await self.scheduler.add_schedule(
            self.direction_update.update,
            trigger)
        pass

    # async def _monitor_settings_change(self):
    #     while True:
    #         await self.settings_changed.wait()
    #         await self._schedule_direction_updater()
    #         self.settings_changed.clear()


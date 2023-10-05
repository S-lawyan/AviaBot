import asyncio

from loguru import logger
from avia_bot.service import BotService
from avia_bot.config import config
from database.mysqldb import database
from scheduler.scheduler import ServiceScheduler
from apscheduler.schedulers.async_ import AsyncScheduler
from avia_api.http_session import HttpSessionMaker
from scheduler.direction_update import DirectionUpdate


async def _start_scheduler(direction_update):
    async with AsyncScheduler() as scheduler:
        service_scheduler = ServiceScheduler(
            scheduler,
            direction_update,
        )
        await service_scheduler.start()
        while True:
            await asyncio.sleep(1)

async def main():
    logger.add(
            "logs/avia_bot_{time:YYYY-MM-DD}.log",
            rotation="1 day",
            retention="7 days",
            compression="zip",
            level="DEBUG",
        )
    try:
        http_session_maker = HttpSessionMaker()
        # api = TicketsApi(http_session_maker)
        bot = BotService(config, http_session_maker)
        direction_update = DirectionUpdate(bot, http_session_maker)
        await database.create_pool()
        asyncio.create_task(_start_scheduler(direction_update))
        # asyncio.create_task(bot.start_bot())
        await bot.start_bot()
    finally:
        await bot.stop_bot()
        await database.close()



if __name__ == "__main__":
    asyncio.run(main())




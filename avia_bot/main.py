import asyncio

from loguru import logger
from avia_bot.service import BotService
from avia_bot.config import config

async def main():
    logger.add(
            "logs/avia_bot_{time:YYYY-MM-DD}.log",
            rotation="1 day",
            retention="7 days",
            compression="zip",
            level="DEBUG",
        )
    bot = BotService(config)
    await bot.start_bot()

if __name__ == "__main__":
    asyncio.run(main())




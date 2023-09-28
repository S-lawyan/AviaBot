import asyncio
import os.path

from loguru import logger
from avia_bot.service import BotService
from avia_bot.config import Settings
from avia_bot.config import load_config



    # await bot.start()

if __name__ == "__main__":
    logger.add(
        "logs/avia_bot_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="7 days",
        compression="zip",
        level="DEBUG",
    )
    # Получаю рабочие директории проекта
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    ROOT_DIR = os.path.dirname(CURRENT_DIR)
    # Подгружаю конфиги и запускаю бота
    config: Settings = load_config(config_path=os.path.join("","config.yaml"))
    bot = BotService(config)
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())

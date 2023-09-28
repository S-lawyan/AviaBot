
from aiogram.dispatcher import Dispatcher
from aiogram import Bot, types
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from loguru import logger
from avia_bot.config import Settings
# from graceful_shutdown.service import ServiceWithGracefulShutdown


class BotService(): #ServiceWithGracefulShutdown
    def __init__(self, config: Settings):
        super().__init__()
        self.bot = Bot(token=config.bot.bot_token.get_secret_value(), parse_mode=types.ParseMode.HTML)  # "html"
        self.dp = Dispatcher(self.bot, storage=MemoryStorage())
        # Запуск бота
        # asyncio.create_task(self.start())
        self.start_bot()

    # async def start(self) -> None:
    #     asyncio.create_task(self.start_bot())

    # async def stop(self) -> None:
    #     pass

    def start_bot(self):
        # await
        executor.start_polling(
            self.dp,
            skip_updates=True,
            on_startup=on_startup,
            on_shutdown=on_shutdown
        )

    async def send_alerts_to_group(self, group_id: int):
        pass


async def on_startup(dp):
    logger.info("The bot is running!")


async def on_shutdown(dp):
    logger.info("The bot is stopping!")


from aiogram import Dispatcher
from aiogram import Bot, types
# from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from loguru import logger
from avia_bot.config import Settings
from avia_bot.handlers import *
# from graceful_shutdown.service import ServiceWithGracefulShutdown


class BotService: #ServiceWithGracefulShutdown
    def __init__(self, config: Settings):
        super().__init__()
        self.bot = Bot(token=config.bot.bot_token.get_secret_value(), parse_mode=types.ParseMode.HTML)  # "html"
        self.dp = Dispatcher(self.bot, storage=MemoryStorage())
        client.register_handlers_client(self.dp)

    # async def start(self) -> None:
    #     asyncio.create_task(self.start_bot())

    # async def stop(self) -> None:
    #     pass

    async def start_bot(self) -> None:
        await self.dp.skip_updates() # Отключение ответ на команды из очереди пока был выключен
        try:
            logger.info("The bot is running!")
            await self.dp.start_polling(self.bot)
        except:
            pass
        # executor.start_polling(
        #     self.dp,
        #     skip_updates=True,
        #     on_startup=on_startup,
        #     on_shutdown=on_shutdown
        # )

    async def send_alerts_to_group(self, group_id: int) -> None:
        pass


# async def on_startup(dp) -> None:
#     logger.info("The bot is running!")
#
#
# async def on_shutdown(dp) -> None:
#     logger.info("The bot is stopping!")

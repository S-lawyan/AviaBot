from aiogram import Bot
from aiogram import Dispatcher
from aiogram import types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiohttp import ClientSession
from loguru import logger

from avia_api.http_session import HttpSessionMaker
from avia_bot.config import Settings
from avia_bot.handlers import *

# from aiogram.utils import executor


class BotService:
    def __init__(self, config: Settings, http_session_maker: HttpSessionMaker):
        super().__init__()
        self.config = config
        self.http_session_maker = http_session_maker
        self.session: ClientSession | None = None
        self.bot = Bot(
            token=config.bot.bot_token.get_secret_value(),
            parse_mode=types.ParseMode.HTML,
        )  # "html"
        self.dp = Dispatcher(self.bot, storage=MemoryStorage())
        client.register_handlers_client(self.dp)

    async def start_bot(self) -> None:
        await self.dp.skip_updates()
        logger.info("The bot is running!")
        await self.dp.start_polling(self.bot)

    async def stop_bot(self) -> None:
        self.dp.stop_polling()

    async def send_alerts_to_group(self, msg: str) -> None:
        channel_id: int = self.config.bot.channel_id
        # TODO отправка в канал по channel_id шаблонного сообщения про билетик
        await self.bot.send_message(
            chat_id=channel_id,
            text=msg,
            disable_web_page_preview=True,
            parse_mode="html",
        )

import os
import random

from aiogram import Dispatcher
from aiogram import Bot, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from loguru import logger
from avia_bot.config import Settings, PICTURES_DIR
from avia_bot.handlers import *
from avia_api.http_session import HttpSessionMaker
from aiohttp import ClientSession
from avia_bot.keyboards import kb


async def get_picture(IATA: str):
    try:
        IATA_dir = os.path.join(PICTURES_DIR, IATA)
        files = os.listdir(IATA_dir)
        images = [file for file in files if file.endswith(('.jpg', '.jpeg', '.png'))]
        if len(images) == 0:
            raise FileNotFoundError()
    except FileNotFoundError:
        IATA_dir = os.path.join(PICTURES_DIR, "ALL")
        files = os.listdir(IATA_dir)
        images = [file for file in files if file.endswith(('.jpg', '.jpeg', '.png'))]
    random_image = random.choice(images)
    file_path = os.path.join(IATA_dir, random_image)
    read_file = open(file=file_path, mode="rb").read()
    return read_file


class BotService:
    def __init__(
            self,
            config: Settings,
            http_session_maker: HttpSessionMaker
    ):
        super().__init__()
        self.config = config
        self.http_session_maker = http_session_maker
        self.session: ClientSession | None = None
        self.bot = Bot(token=config.bot.bot_token.get_secret_value(), parse_mode=types.ParseMode.HTML)  # "html"
        self.dp = Dispatcher(self.bot, storage=MemoryStorage())
        client.register_handlers_client(self.dp)

    async def start_bot(self) -> None:
        await self.dp.skip_updates()
        logger.info("The bot is running!")
        await self.dp.start_polling(self.bot)

    async def stop_bot(self) -> None:
        self.dp.stop_polling()

    async def send_alerts_to_group(self, text: str, ulr: str, IATA: str) -> None:
        channel_id: int = self.config.bot.channel_id
        # TODO отправка в канал по channel_id шаблонного сообщения про билетик
        picture = await get_picture(IATA=IATA)
        await self.bot.send_photo(chat_id=channel_id, caption=text, photo=picture, reply_markup=await kb.pay_kb(url=ulr), parse_mode="html")
        # await self.bot.send_message(chat_id=channel_id, text=text, disable_web_page_preview=True, parse_mode="html")




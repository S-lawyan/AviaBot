
from aiogram import Dispatcher
from aiogram import Bot, types
# from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from loguru import logger
from avia_bot.config import Settings
from avia_bot.handlers import *
from avia_api.http_session import HttpSessionMaker
from avia_api.adapter import TicketsApi
from avia_api.models import Ticket
from avia_api.models import Direction
from aiohttp import ClientSession

# from graceful_shutdown.service import ServiceWithGracefulShutdown


class BotService: #ServiceWithGracefulShutdown
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
        await self.dp.skip_updates() # Отключение ответ на команды из очереди пока был выключен
        logger.info("The bot is running!")
        await self.dp.start_polling(self.bot)

    async def stop_bot(self) -> None:
        self.dp.stop_polling()

    async def first_notify_group(self, new_ticket: Ticket, direction: Direction) -> None:
        channel_id: int = self.config.bot.channel_id
        msg = f"""
        Добавлено новое направление!
        {direction.origin} ➡️ {direction.destination} 
        🛫 {new_ticket.departure_at}
        💳 {int(new_ticket.price)} ₽ | <a href="{new_ticket.link}">купить билет</a>
        """
        await self.bot.send_message(chat_id=channel_id, text=msg)

    async def send_alerts_to_group(self, new_ticket: Ticket, direction: Direction) -> None:
        channel_id: int = self.config.bot.channel_id
        # TODO отправка в канал по channel_id шаблонного сообщения про билетик
        msg = f"""
        {direction.origin} ➡️ {direction.destination} 
        🛫 {new_ticket.departure_at}
        💳 {int(new_ticket.price)} ₽ | <a href="{new_ticket.link}">купить билет</a>
        """
        await self.bot.send_message(chat_id=channel_id, text=msg)



# async def on_startup(dp) -> None:
#     logger.info("The bot is running!")
#
#
# async def on_shutdown(dp) -> None:
#     logger.info("The bot is stopping!")

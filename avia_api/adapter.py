import asyncio

from .http_session import HttpSessionMaker
from aiohttp import ClientSession, ClientConnectionError
from async_timeout import timeout
from avia_bot.config import config
from loguru import logger

class TicketsApi:
    def __init__(self):
        http_session_maker = HttpSessionMaker()
        self.session: ClientSession = http_session_maker()
        self.api_token = config.bot.api_token
        self.currency = "ru"
        self.locale = config.bot.language

    async def get_tickets(self, origin: str, destination: str) -> list:
        try:
            async with timeout(10):
                responce = await get_tickets_response(
                self.session,
                origin,
                destination,
                locale=self.locale,
                currency=self.currency,
                # airline, # TODO сделать так, чтобы если будет указана авиакомпания, то присваивать, иначе None
                # market, # TODO какой-то маркет источника данных, по умолчанию стоит RU
                token=self.api_token.get_secret_value()
                )
        except asyncio.TimeoutError:
            logger.error(f"Запрос билетов вылетел по таймауту")
        except ClientConnectionError as e:
            logger.error(f"Ошибка получения билетов: {e}")




async def get_tickets_response(
        session: ClientSession,
        origin,
        destination,
        locale,
        currency,
        airline,
        market,
        token):
    requests_url = "https://api.travelpayouts.com/aviasales/v3/get_special_offers"
    params = {

    }
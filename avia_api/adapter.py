import asyncio
import json

from aiohttp import ClientSession, ClientConnectionError
from async_timeout import timeout
from avia_bot.config import config
from loguru import logger
from datetime import datetime
from avia_api.models import Ticket
from avia_api.exceptions import (
    TicketApiConnectionError,
    TicketsAPIError,
    TicketsParsingError
)

class TicketsApi:
    def __init__(self, http_session_maker):
        # self.http_session_maker = HttpSessionMaker()
        self.session: ClientSession = http_session_maker()
        self.api_token = config.bot.api_token
        self.currency = "rub"
        self.locale = config.bot.language

    async def get_ticket(self, origin: str, destination: str) -> Ticket:
        try:
            async with timeout(10):
                response = await get_ticket_response(
                    self.session,
                    origin,
                    destination,
                    locale=self.locale,
                    currency=self.currency,
                    token=self.api_token.get_secret_value()
                )
        except asyncio.TimeoutError:
            logger.error(f"Запрос билетов вылетел по таймауту")
            raise TicketApiConnectionError()
        except ClientConnectionError as e:
            logger.error(f"Ошибка получения билетов: {e}")
            raise TicketApiConnectionError()
        json_response = json.loads(response)
        if "error" in response:
            logger.error(
                f'Ошибка при получении билета: ошибка {json_response["error"]}, направление: из {origin} в {destination}'
            )
            raise TicketsAPIError()
        return parse_ticket(json_response)


async def get_ticket_response(
    session: ClientSession,
    origin,
    destination,
    locale,
    currency,
    token
) -> str:
    requests_url = "https://api.travelpayouts.com/aviasales/v3/get_special_offers"
    params = {
    "origin": origin,
    "destination": destination,
    "locale": locale,
    "currency": currency,
    "token": token
    }

    async with session.get(requests_url, params=params) as response:
        return await response.text()


def parse_ticket(json_response) -> Ticket:
    if "data" not in json_response:
        logger.error(f"Непонятный ответ от Aviasales: {json_response}")
        raise TicketsParsingError
    json_ticket = json_response["data"][0]
    # Получение информации о билете
    price: float = float(json_ticket["price"])
    origin_name: str = json_ticket["origin_name"]
    destination_name: str = json_ticket["destination_name"]
    link: str = json_ticket["link"]
    departure_at: datetime = datetime_from_ticket(json_ticket["departure_at"]) #2023-10-11 08:45:00
    return Ticket(
        price=price,
        origin_name=origin_name,
        destination_name=destination_name,
        link=link,
        departure_at=departure_at,
        last_update=None
    )


def datetime_from_ticket(datetime_str: str) -> datetime:
    """Конвертация даты и времени из API ответа в читаемый формат"""
    return datetime.strptime(
        str(datetime_str)[: len(datetime_str) - 9], "%Y-%m-%dT%H:%M"
    )

# aviasales_api = TicketsApi()
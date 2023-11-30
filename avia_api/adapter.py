import asyncio
import json

from aiohttp import ClientSession, ClientConnectionError
from async_timeout import timeout
from avia_bot.config import config
from avia_bot.glossaries.glossary import glossary
from loguru import logger
from datetime import datetime
from avia_api.models import Ticket
from avia_api.exceptions import (
    TicketApiConnectionError,
    TicketsAPIError,
    TicketsParsingError,
    MissingTicketsError
)


class TicketsApi:
    def __init__(self, http_session_maker):
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
                    self.locale,
                    self.currency,
                    self.api_token.get_secret_value()
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
                f'Ошибка при получении билета: ошибка {json_response["error"]}, направление: из {origin} в {destination}')
            raise TicketsAPIError()
        elif json_response["data"] == []:
            logger.error(f"Нет билетов на {origin} - {destination} : {json_response}")
            raise MissingTicketsError()
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
        raise TicketsParsingError()
    json_ticket = json_response["data"][0]
    # Получение информации о билете
    price: float = float(json_ticket["price"])
    origin_name: str = json_ticket["origin_name_declined"]  # origin_name
    destination_name: str = json_ticket["destination_name"]  # destination_name_declined
    destination_code: str = json_ticket["destination"]
    link: str = "https://www.aviasales.ru" + json_ticket["link"] + "&marker=491628"
    departure_at: str = datetime_from_ticket(json_ticket["departure_at"])
    return Ticket(
        price=price,
        origin_name=origin_name,
        destination_name=destination_name,
        destination_code=destination_code,
        link=link,
        departure_at=departure_at,
        last_update=None
    )


def datetime_from_ticket(datetime_str: str) -> str:
    """Конвертация даты и времени из API ответа в читаемый формат"""
    input_datetime = datetime.strptime(datetime_str[:19], "%Y-%m-%dT%H:%M:%S")
    day_of_week_index = input_datetime.weekday()
    days = glossary.get_phrase(key="days_of_week")
    day_of_week = days[day_of_week_index]
    formatted_datetime = input_datetime.strftime("%d.%m.%Y • %H:%M")
    return f"{formatted_datetime} • {day_of_week}"

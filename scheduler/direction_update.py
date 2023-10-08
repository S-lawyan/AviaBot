import asyncio

from avia_bot.service import BotService
from avia_api.http_session import HttpSessionMaker
from database.mysqldb import database
from avia_api.adapter import TicketsApi
from avia_api.models import Direction
from avia_api.models import Ticket
from avia_api.models import PriceSettings
from loguru import logger
from avia_api.exceptions import DatabaseUpdateTicketError

class DirectionUpdate:
    def __init__(
            self,
            bot: BotService,
            http_session_maker: HttpSessionMaker
    ):
        self.bot = bot
        self.http_session_maker = http_session_maker

    async def update(self):
        logger.info("Выполняется проверка цены по расписанию")
        # await asyncio.sleep(15)
        api = TicketsApi(self.http_session_maker)
        _directions: tuple = await database.get_directions()
        if len(_directions) == 0:
            logger.info("Позиции не заданы, проверка не была выполнена.")
            return
        # Все направления
        all_directions: list = await split_on_subdirection(_directions)
        settings: PriceSettings = await database.get_settings()
        # Проход по каждому направлению отдельно
        for _subdirections in all_directions:
            updated_tickets = []
            # Проход по поднаправлениями
            for subdirection in _subdirections:
                direction: Direction = await parse_direction(subdirection)
                new_ticket = await get_tickets_api(api, direction)
                old_ticket: Ticket = await get_ticket_db(direction=direction, new_ticket=new_ticket)
                status = await checking_update(
                    new_ticket=new_ticket,
                    old_ticket=old_ticket,
                    direction=direction,
                    settings=settings,
                )
                if status:
                    updated_tickets.append(new_ticket)
                else:
                    continue
            if len(updated_tickets) != 0:
                await create_notification(
                    updated_tickets=updated_tickets,
                    direction=await parse_direction(_subdirections[0]),
                    bot=self.bot
                )
        logger.info(f"Проверка всех направлений завершена ({len(all_directions)})")

async def parse_direction(direction: tuple):
    id_direction: id = int(direction[0])
    direction_from: str = direction[1]
    direction_to: str = direction[2]
    origin_code: str = direction[3]
    destination_code: str = direction[4]
    max_price: int = direction[5]
    count_posts: int = direction[6]
    return Direction(
        id_direction=id_direction,
        direction_from=direction_from,
        direction_to=direction_to,
        origin_code=origin_code,
        destination_code=destination_code,
        max_price=max_price,
        count_posts=count_posts
    )


async def split_on_subdirection(directions: tuple) -> list:
    result = {}
    for item in directions:
        key = item[0]
        if key not in result:
            result[key] = []
        result[key].append(item)
    return list(result.values())


async def get_tickets_api(api: TicketsApi, direction: Direction) -> Ticket:
    await asyncio.sleep(1)
    new_ticket: Ticket = await api.get_ticket(origin=direction.origin_code, destination=direction.destination_code)
    return new_ticket


async def get_ticket_db(direction: Direction, new_ticket: Ticket) -> Ticket | None:
    old_ticket: Ticket | None = await database.get_ticket_(direction=direction)
    if not old_ticket:
        # Первое занесение
        await database.save_ticket(ticket=new_ticket, direction=direction)
        logger.info(f"Добавлен новый билет по направлению: {direction.direction_from} {direction.origin_code} - {direction.direction_to} {direction.destination_code}) new_ticket.destination_code = {new_ticket.destination_code}")
        return None
    return old_ticket


async def checking_update(
        new_ticket: Ticket,
        old_ticket: Ticket,
        direction: Direction,
        settings: PriceSettings
):
    """ Проверка факта обновления цены и в какую сторону >< """
    new_price = new_ticket.price
    old_price = old_ticket.price
    new_departure_at = new_ticket.departure_at
    old_departure_at = old_ticket.departure_at

    # Изменения не произошли
    if new_price == old_price and new_departure_at == old_departure_at:
        # ничего не делаю
        return None

    # Цена билета превышает указанный порог
    elif new_price >= direction.max_price:
        try:
            # Обновление данных билета
            await database.update_ticket(ticket=new_ticket, direction=direction)
            logger.info(f"Превышение максимальной цена билета, обновление БД {direction.id_direction} - {direction.destination_code}")
            # НЕ отправляю в группу
            return None
        except DatabaseUpdateTicketError:
            return None


    # Цена осталась прежней
    elif new_price == old_price:
        if new_departure_at != old_departure_at:
            # TODO ЧЕРЕЗ ЛИМИТ
            try:
                # Обновление данных билета
                await database.update_ticket(ticket=new_ticket, direction=direction)
                logger.info(f"Обновление даты билета {direction.id_direction} - {direction.destination_code}")
                # Отправляю в группу
                return True
            except DatabaseUpdateTicketError:
                return None
        else:
            # НЕ отправляю в группу
            return None


    # Цена уменьшилась
    if new_price < old_price:

        # Цена уменьшилась БОЛЕЕ, чем на 20%, время не важно
        if (old_price - new_price)/old_price * 100 >= settings.critical_difference:
            try:
                # Обновление данных билета
                await database.update_ticket(ticket=new_ticket, direction=direction)
                logger.info(f"Критическое уменьшение цены билета {direction.id_direction} - {direction.destination_code}")
                # Отправляю в группу
                return True
            except DatabaseUpdateTicketError:
                return None


        # Цена уменьшилась БОЛЕЕ, чем на 10%, время не важно
        elif (old_price - new_price) / old_price * 100 >= settings.difference:
            # TODO ЧЕРЕЗ ЛИМИТ
            try:
                # Обновление данных билета
                await database.update_ticket(ticket=new_ticket, direction=direction)
                logger.info(f"Значительное уменьшение цены билета {direction.id_direction} - {direction.destination_code} Оповещение отправлено")
                # Отправляю в группу
                return True
            except DatabaseUpdateTicketError:
                return None


        # Цена уменьшилась МЕНЕЕ, чем на 10%
        elif (old_price - new_price) / old_price * 100 <= settings.difference:
            # Дата не изменилась, или изменилась
            if new_departure_at == old_departure_at:
                try:
                    # Обновление данных билета
                    await database.update_ticket(ticket=new_ticket, direction=direction)
                    logger.info(f"Незначительное уменьшение цены билета {direction.id_direction} - {direction.destination_code}")
                    # НЕ отправляю в группу
                    return None
                except DatabaseUpdateTicketError:
                    return None
            else:
                # TODO ЧЕРЕЗ ЛИМИТ
                try:
                    # Обновление данных билета
                    await database.update_ticket(ticket=new_ticket, direction=direction)
                    logger.info(f"Незначительное уменьшение цены и новая дата билета {direction.id_direction} - {direction.destination_code} Оповещение отправлено")
                    # Отправляю в группу
                    return True
                except DatabaseUpdateTicketError:
                    return None


    # Цена увеличилась
    elif new_price > old_price:

        # Цена увеличилась МЕНЕЕ, чем на 10%
        if (old_price - new_price)/old_price * 100 <= settings.difference:
            # Дата не изменилась
            if new_departure_at == old_departure_at:
                try:
                    # Обновление данных билета
                    await database.update_ticket(ticket=new_ticket, direction=direction)
                    logger.info(f"Незначительное увеличение цены билета {direction.id_direction} - {direction.destination_code}")
                    # НЕ отправляю в группу
                    return None
                except DatabaseUpdateTicketError:
                    return None
            else:
                # TODO ЧЕРЕЗ ЛИМИТ
                try:
                    # Обновление данных билета
                    await database.update_ticket(ticket=new_ticket, direction=direction)
                    logger.info(f"Незначительное увеличение цены и новая дата билета {direction.id_direction} - {direction.destination_code} Оповещение отправлено")
                    # Отправляю в группу
                    return True
                except DatabaseUpdateTicketError:
                    return None


        # Цена увеличилась БОЛЕЕ, чем на 10%, дату не учитываем
        elif (old_price - new_price) / old_price * 100 >= settings.difference:
            try:
                # Обновление данных билета
                await database.update_ticket(ticket=new_ticket, direction=direction)
                logger.info(f"Значительное увеличение цены билета {direction.id_direction} - {direction.destination_code}")
                # НЕ отправляю в группу
                return None
            except DatabaseUpdateTicketError:
                return None

    else:
        # Произошло то, что в условиях не учлось
        logger.error(f" !!! ПРОИЗОШЛА не предусмотренная ситуация с изменениями в билетах! {dir(new_ticket)}\n\n{dir(old_ticket)}\n\n{dir(direction)}")
        return None

# async def checking_notification_limit(
#         new_ticket: Ticket,
#         old_ticket: Ticket,
#         direction: Direction,
#         settings: Settings,
#         bot: BotService
# ):
#     """ Проверка лимита отправки сообщения """
#     # TODO пока не придумал как
#     pass

async def create_notification(updated_tickets: list[Ticket], direction: Direction, bot: BotService):
    msg_head = f"{direction.direction_from} ➡️ {direction.direction_to}"
    msg_body = ""
    for ticket in updated_tickets:
        msg_body += (
        f"<b>{ticket.destination_name} ({ticket.destination_code})</b>\n" #direction.destination_code
        f"🛫 {ticket.departure_at}\n"
        f"💳 {int(ticket.price)} ₽ | <a href='{ticket.link}'>купить билет</a>\n\n"
        )
    msg = (
        f"{msg_head}\n\n"
        f"{msg_body}"
    )
    await notify_group(msg=msg, bot=bot)

async def notify_group(msg: str, bot: BotService):
    """ Отправка сообщения в канал """
    await bot.send_alerts_to_group(msg=msg)
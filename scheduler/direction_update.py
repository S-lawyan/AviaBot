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
        print("Выполняется проверка цены по расписанию")
        # await asyncio.sleep(15)
        api = TicketsApi(self.http_session_maker)
        directions = await database.get_directions()
        if len(directions) == 0:
            logger.info("Позиции не заданы, проверка не была выполнена.")
            return
        for _direction in directions:
            direction: Direction = await parse_direction(_direction)
            await get_tickets_api(api, direction, self.bot)
        logger.info(f"Проверка всех направлений завершена ({len(directions)})")

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

async def get_tickets_api(api: TicketsApi, direction: Direction, bot: BotService):
    await asyncio.sleep(1)
    new_ticket: Ticket = await api.get_ticket(origin=direction.origin_code, destination=direction.destination_code)
    await get_ticket_db(direction=direction, bot=bot, new_ticket=new_ticket)
    # TODO Проверки на порог цен и так далее.

async def get_ticket_db(direction: Direction, bot: BotService, new_ticket: Ticket):
    # TODO ГДЕ-ТО ТУТ ОШИБКА ИЗ-ЗА КОТОРОЙ ДОБАВЛЯЮТСЯ НОВЫЕ БИЛЕТЫ ПО КРУГУ
    old_ticket: Ticket | None = await database.get_ticket_(direction=direction)
    if not old_ticket:
        # Первое занесение
        await database.save_ticket(ticket=new_ticket, direction=direction)
        logger.info(f"Добавлен новый билет по направлению: {direction.direction_from} {direction.origin_code} - {direction.direction_to} {direction.destination_code}) new_ticket.destination_code = {new_ticket.destination_code}")
        # await bot.first_notify_group(ticket=new_ticket, direction=direction)
        return
    settings: PriceSettings = await database.get_settings()
    '''
        На данном этапе у меня есть информация о старом и новом билетах,
        которую нужно сравнить, а также у меня есть информация о направлении,
        которую я тоже использую для создания шапки выходного сообщения.
    '''

    # TODO Проверка на то, обновилась ли цена и время билета
    # TODO Проверка насколько % цена упала по сравнению со значениями из Settings
    # TODO Проверка на лимит сообщений
    # TODO Отправка оповещения в канал

    await checking_update(
        new_ticket=new_ticket,
        old_ticket=old_ticket,
        direction=direction,
        settings=settings,
        bot=bot
    )

async def checking_update(
        new_ticket: Ticket,
        old_ticket: Ticket,
        direction: Direction,
        settings: PriceSettings,
        bot: BotService
):
    """ Проверка факта обновления цены и в какую сторону >< """
    new_price = new_ticket.price
    old_price = old_ticket.price
    new_departure_at = new_ticket.departure_at
    old_departure_at = old_ticket.departure_at


    # Цена билета превышает указанный порог
    if new_price >= direction.max_price:
        # TODO обновить данные
        try:
            # Обновление данных билета
            await database.update_ticket(ticket=new_ticket, direction=direction)
            logger.info(f"Данные билета {direction.id_direction} - {direction.destination_code} обновлены")
        except DatabaseUpdateTicketError:
            return


    # Изменения не произошли
    elif new_price == old_price and new_departure_at == old_departure_at:
        # ничего не делаю
        return


    # Цена осталась прежней, дата изменилась
    elif new_price == old_price and new_departure_at != old_departure_at:
        # TODO Обновляю дату, отправляю в группу ЧЕРЕЗ ЛИМИТ
        try:
            # Обновление данных билета
            await database.update_ticket(ticket=new_ticket, direction=direction)
            logger.info(f"Данные билета {direction.id_direction} - {direction.destination_code} обновлены")
        except DatabaseUpdateTicketError:
            return
        # Отправляю в группу
        await notify_group(new_ticket=new_ticket, direction=direction, bot=bot)


    # Цена уменьшилась БОЛЕЕ, чем на 20%, время не важно
    elif (old_price - new_price)/old_price*100 >= settings.critical_difference:
        # TODO Обновить цену, Отправить сообщение в группу БЕЗ ЛИМИТА
        try:
            # Обновление данных билета
            await database.update_ticket(ticket=new_ticket, direction=direction)
            logger.info(f"Данные билета {direction.id_direction} - {direction.destination_code} обновлены")
        except DatabaseUpdateTicketError:
            return
        # Отправляю в группу
        await notify_group(new_ticket=new_ticket, direction=direction, bot=bot)


    # Цена уменьшилась БОЛЕЕ, чем на 10%, время не важно
    elif (old_price - new_price)/old_price*100 >= settings.difference:
        # TODO обновить цену и дату, отправить в группу ЧЕРЕЗ ЛИМИТ
        try:
            # Обновление данных билета
            await database.update_ticket(ticket=new_ticket, direction=direction)
            logger.info(f"Данные билета {direction.id_direction} - {direction.destination_code} обновлены")
        except DatabaseUpdateTicketError:
            return
        # Отправляю в группу
        await notify_group(new_ticket=new_ticket, direction=direction, bot=bot)


    # Цена уменьшилась МЕНЕЕ, чем на 10%
    elif (old_price - new_price) / old_price * 100 <= settings.difference:
        # Дата не изменилась, или изменилась
        if new_departure_at == old_departure_at:
            # TODO обновляю цену и дату
            try:
                # Обновление данных билета
                await database.update_ticket(ticket=new_ticket, direction=direction)
                logger.info(f"Данные билета {direction.id_direction} - {direction.destination_code} обновлены")
            except DatabaseUpdateTicketError:
                return
        else:
            # TODO обновляю цену и дату, отправляю в группу ЧЕРЕЗ ЛИМИТ
            try:
                # Обновление данных билета
                await database.update_ticket(ticket=new_ticket, direction=direction)
                logger.info(f"Данные билета {direction.id_direction} - {direction.destination_code} обновлены")
            except DatabaseUpdateTicketError:
                return
            # Отправляю в группу
            await notify_group(new_ticket=new_ticket, direction=direction, bot=bot)


    # Цена увеличилась МЕНЕЕ, чем на 10%
    elif (old_price - new_price) / old_price * 100 <= settings.difference:
        # Дата не изменилась, или изменилась
        if new_departure_at == old_departure_at:
            # TODO обновить данные
            try:
                # Обновление данных билета
                await database.update_ticket(ticket=new_ticket, direction=direction)
                logger.info(f"Данные билета {direction.id_direction} - {direction.destination_code} обновлены")
            except DatabaseUpdateTicketError:
                return
        else:
            # TODO обновить данные, отправить в группу ЧЕРЕЗ ЛИМИТ
            try:
                # Обновление данных билета
                await database.update_ticket(ticket=new_ticket, direction=direction)
                logger.info(f"Данные билета {direction.id_direction} - {direction.destination_code} обновлены")
            except DatabaseUpdateTicketError:
                return
            # Отправляю в группу
            await notify_group(new_ticket=new_ticket, direction=direction, bot=bot)


    # Цена увеличилась более, чем на 10%, дата не важна
    elif (old_price - new_price) / old_price * 100 >= settings.difference:
        # TODO обновить данные
        try:
            # Обновление данных билета
            await database.update_ticket(ticket=new_ticket, direction=direction)
            logger.info(f"Данные билета {direction.id_direction} - {direction.destination_code} обновлены")
        except DatabaseUpdateTicketError:
            return

    else:
        # Произошло то, что в условиях не учлось
        logger.error(f" !!! ПРОИЗОШЛА не предусмотренная ситуация с изменениями в билетах! {dir(new_ticket)}\n\n{dir(old_ticket)}\n\n{dir(direction)}")
        return
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

async def notify_group(
        new_ticket: Ticket,
        # old_ticket: Ticket,
        direction: Direction,
        # settings: PriceSettings,
        bot: BotService
):
    """ Отправка сообщения в канал """
    await bot.send_alerts_to_group(ticket=new_ticket, direction=direction)
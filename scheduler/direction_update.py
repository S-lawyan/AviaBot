import asyncio

from loguru import logger

from avia_api.adapter import TicketsApi
from avia_api.exceptions import AddNewTicket
from avia_api.exceptions import DatabaseAddTicketError
from avia_api.exceptions import DatabaseGetTicketError
from avia_api.exceptions import DatabaseUpdateDirectionSentPostsError
from avia_api.exceptions import DatabaseUpdateTicketError
from avia_api.exceptions import MissingTicketsError
from avia_api.exceptions import TicketApiConnectionError
from avia_api.exceptions import TicketsAPIError
from avia_api.exceptions import TicketsParsingError
from avia_api.http_session import HttpSessionMaker
from avia_api.models import Direction
from avia_api.models import PriceSettings
from avia_api.models import Ticket
from avia_bot.service import BotService
from database.mysqldb import database


class DirectionUpdate:
    def __init__(self, bot: BotService, http_session_maker: HttpSessionMaker):
        self.bot = bot
        self.http_session_maker = http_session_maker

    async def update(self):
        logger.info("Старт проверки цен")
        api = TicketsApi(self.http_session_maker)
        settings: PriceSettings = await database.get_settings()
        _directions: list = await database.get_directions()
        if not _directions:
            logger.info("Направления не заданы, проверка закончена.")
            return
        for direction in _directions:
            await update_direction(
                direction=direction, api=api, bot=self.bot, settings=settings
            )
        logger.info(f"Проверка всех направлений завершена ({len(_directions)})")


async def update_direction(
    direction: Direction, api: TicketsApi, bot: BotService, settings: PriceSettings
):
    # Получение нового билета через API
    try:
        new_ticket = await get_tickets_api(api=api, direction=direction)
    except (
        MissingTicketsError,
        TicketsAPIError,
        TicketsParsingError,
        TicketApiConnectionError,
    ):
        return
    # Получение старого билета из БД
    try:
        old_ticket: Ticket = await get_ticket_db(
            direction=direction, new_ticket=new_ticket
        )
    except (DatabaseGetTicketError, AddNewTicket):
        return
    # Проверка обновления данных билетов
    await checking_update(
        new_ticket=new_ticket,
        old_ticket=old_ticket,
        direction=direction,
        settings=settings,
        bot=bot,
    )


async def get_tickets_api(api: TicketsApi, direction: Direction) -> Ticket:
    await asyncio.sleep(1)
    new_ticket: Ticket = await api.get_ticket(
        origin=direction.origin_code, destination=direction.destination_code
    )
    return new_ticket


async def get_ticket_db(direction: Direction, new_ticket: Ticket) -> Ticket | None:
    old_ticket: Ticket | None = await database.get_ticket_(direction=direction)
    if not old_ticket:
        # Первое занесение
        try:
            await database.save_ticket(ticket=new_ticket, direction=direction)
            logger.info(
                f"Добавлен билет: {direction.direction_from} {direction.origin_code} - {direction.direction_to} {direction.destination_code} new_ticket.destination_code = {new_ticket.destination_code}"
            )
            raise AddNewTicket()
        except DatabaseAddTicketError:
            return
    return old_ticket


async def checking_update(
    new_ticket: Ticket,
    old_ticket: Ticket,
    direction: Direction,
    settings: PriceSettings,
    bot: BotService,
):
    new_price = new_ticket.price
    old_price = old_ticket.price
    new_departure_at = new_ticket.departure_at[:10]  # только дата
    old_departure_at = old_ticket.departure_at[:10]  # только дата

    # Изменения не произошли
    if new_price == old_price and new_departure_at == old_departure_at:
        # ничего не делаю
        return

    # Цена билета превышает указанный порог
    elif new_price >= direction.max_price:
        try:
            # Обновление данных билета
            await database.update_ticket(ticket=new_ticket, direction=direction)
            logger.info(
                f"Превышение максимальной цена, обновление БД {direction.id_direction} - {direction.destination_code} : {new_price} >= {direction.max_price}"
            )
            # НЕ отправляю в группу
            return
        except DatabaseUpdateTicketError:
            return

    # Цена осталась прежней
    elif new_price == old_price:
        if new_departure_at != old_departure_at:
            try:
                # Обновление данных билета
                await database.update_ticket(ticket=new_ticket, direction=direction)
                logger.info(
                    f"Обновление даты билета {direction.id_direction} - {direction.destination_code} : {new_price} == {old_price} and {new_departure_at} != {old_departure_at}"
                )
                # Отправляю в группу через проверку лимита
                if await checking_notification_limit(direction=direction):
                    # return True
                    await notify_group(ticket=new_ticket, direction=direction, bot=bot)
                else:
                    return
            except DatabaseUpdateTicketError:
                return
        else:
            # НЕ отправляю в группу
            return

    # Цена уменьшилась
    if new_price < old_price:
        # Цена уменьшилась БОЛЕЕ, чем на 20%, время не важно
        if (old_price - new_price) / old_price * 100 >= settings.critical_difference:
            try:
                # Обновление данных билета
                await database.update_ticket(ticket=new_ticket, direction=direction)
                logger.info(
                    f"Критическое уменьшение цены билета {direction.id_direction} - {direction.destination_code} : {new_price} < {old_price} and {(old_price - new_price) / old_price * 100} >= {settings.critical_difference}"
                )
                # Отправляю в группу
                # return True
                await notify_group(ticket=new_ticket, direction=direction, bot=bot)
            except DatabaseUpdateTicketError:
                return

        # Цена уменьшилась БОЛЕЕ, чем на 10%, время не важно
        elif (old_price - new_price) / old_price * 100 >= settings.difference:
            try:
                # Обновление данных билета
                await database.update_ticket(ticket=new_ticket, direction=direction)
                logger.info(
                    f"Значительное уменьшение цены билета {direction.id_direction} - {direction.destination_code} Оповещение отправлено : {(old_price - new_price) / old_price * 100} >= {settings.difference}"
                )
                # Отправляю в группу через проверку лимита
                if await checking_notification_limit(direction=direction):
                    # return True
                    await notify_group(ticket=new_ticket, direction=direction, bot=bot)
                else:
                    return
            except DatabaseUpdateTicketError:
                return

        # Цена уменьшилась МЕНЕЕ, чем на 10%
        elif (old_price - new_price) / old_price * 100 <= settings.difference:
            # Дата не изменилась, или изменилась
            if new_departure_at == old_departure_at:
                try:
                    # Обновление данных билета
                    await database.update_ticket(ticket=new_ticket, direction=direction)
                    logger.info(
                        f"Незначительное уменьшение цены билета {direction.id_direction} - {direction.destination_code} : {(old_price - new_price) / old_price * 100} <= {settings.difference} and {new_departure_at} == {old_departure_at}"
                    )
                    # НЕ отправляю в группу
                    return
                except DatabaseUpdateTicketError:
                    return
            else:
                try:
                    # Обновление данных билета
                    await database.update_ticket(ticket=new_ticket, direction=direction)
                    logger.info(
                        f"Незначительное уменьшение цены и новая дата билета {direction.id_direction} - {direction.destination_code} Оповещение отправлено  : {(old_price - new_price) / old_price * 100} <= {settings.difference} and {new_departure_at} != {old_departure_at}"
                    )
                    # Отправляю в группу через проверку лимита
                    if await checking_notification_limit(direction=direction):
                        # return True
                        await notify_group(
                            ticket=new_ticket, direction=direction, bot=bot
                        )
                    else:
                        return
                except DatabaseUpdateTicketError:
                    return

    # Цена увеличилась
    elif new_price > old_price:
        # Цена увеличилась МЕНЕЕ, чем на 10%
        if (new_price - old_price) / new_price * 100 <= settings.difference:
            # Дата не изменилась
            if new_departure_at == old_departure_at:
                try:
                    # Обновление данных билета
                    await database.update_ticket(ticket=new_ticket, direction=direction)
                    logger.info(
                        f"Незначительное увеличение цены билета {direction.id_direction} - {direction.destination_code} : {new_price} > {old_price} and {(new_price - old_price)/new_price * 100} <= {settings.difference} and {new_departure_at} == {old_departure_at}"
                    )
                    # НЕ отправляю в группу
                    return
                except DatabaseUpdateTicketError:
                    return
            else:
                try:
                    # Обновление данных билета
                    await database.update_ticket(ticket=new_ticket, direction=direction)
                    logger.info(
                        f"Незначительное увеличение цены и новая дата билета {direction.id_direction} - {direction.destination_code} Оповещение отправлено : {new_price} > {old_price} and {(old_price - new_price) / old_price * 100} <= {settings.difference} and {new_departure_at} != {old_departure_at}"
                    )
                    # Отправляю в группу через проверку лимита
                    if await checking_notification_limit(direction=direction):
                        # return True
                        await notify_group(
                            ticket=new_ticket, direction=direction, bot=bot
                        )
                    else:
                        return
                except DatabaseUpdateTicketError:
                    return

        # Цена увеличилась БОЛЕЕ, чем на 10%, дату не учитываем
        elif (new_price - old_price) / new_price * 100 >= settings.difference:
            try:
                # Обновление данных билета
                await database.update_ticket(ticket=new_ticket, direction=direction)
                logger.info(
                    f"Значительное увеличение цены билета {direction.id_direction} - {direction.destination_code} : {new_price} > {old_price} and {(new_price - old_price)/new_price * 100} >= {settings.difference}"
                )
                # НЕ отправляю в группу
                return
            except DatabaseUpdateTicketError:
                return

    else:
        # Произошло то, что в условиях не учлось
        logger.error(
            f" !!! ПРОИЗОШЛА не предусмотренная ситуация с изменениями в билетах! \n Направление: {direction.id_direction} - {direction.destination_code} \n Новая цена - {new_price} Старая цена - {old_price} \n Новая дата {new_departure_at} Старая дата {old_departure_at}"
        )
        return


async def checking_notification_limit(
    direction: Direction,
):
    """Проверка лимита отправки сообщения"""
    count_posts = direction.count_posts
    sent_posts = direction.sent_posts
    if sent_posts >= count_posts:
        # Не отправлять и не обновлять БД
        return None
    elif sent_posts < count_posts:
        try:
            await database.update_limit(sent_posts=sent_posts + 1, direction=direction)
        except DatabaseUpdateDirectionSentPostsError:
            return None
        return True


async def notify_group(ticket: Ticket, direction: Direction, bot: BotService) -> None:
    """Отправка сообщения в канал"""
    msg = (
        f"{direction.smail} {direction.direction_to} из {ticket.origin_name}\n\n"
        f"<b>{ticket.destination_name} ({ticket.destination_code})</b>\n"  # direction.destination_code
        f"🛫 {ticket.departure_at}\n"
        f"💳 {int(ticket.price)} ₽ | <a href='{ticket.link}'>купить билет</a>\n\n"
    )
    await bot.send_alerts_to_group(msg=msg)


async def reset_sent_posts() -> None:
    try:
        await database.reset_limit()
        logger.info("Значения sent_posts сброшены")
    except DatabaseUpdateDirectionSentPostsError:
        pass


# ДАННЫЕ ЗАКОММЕНТИРОВАННЫЕ СТРОКИ БЫЛИ ИСПОЛЬЗОВАНЫ ДЛЯ ОТПРАВКИ СГРУППИРОВАННЫХ ПО НАПРАВЛЕНИЮ БИЛЕТОВ
# sorted_directions: list = await sort_on_subdirection(_directions)
# # Проход по каждому направлению отдельно
# for directions in sorted_directions:
#     updated_tickets = []
#     # Проход по поднаправлениями
#     for subdirection in directions:
#         await self.update_subdirection(direction=subdirection, api=api, settings=settings)


# status = await checking_update(
#                 new_ticket=new_ticket,
#                 old_ticket=old_ticket,
#                 direction=direction,
#                 settings=settings,
#             )
#             if status:
#                 updated_tickets.append(new_ticket)
#             else:
#                 continue
#         if len(updated_tickets) != 0:
#             await create_notification(
#                 updated_tickets=updated_tickets,
#                 direction=await parse_direction(_subdirections[0]),
#                 bot=self.bot
#             )

# async def sort_on_subdirection(directions: list) -> list:
#     result = {}
#     for item in directions:
#         key = item[1]
#         if key not in result:
#             result[key] = []
#         result[key].append(item)
#     return list(result.values())

# msg_head = f"{direction.smail} {direction.direction_to} из {ticket[0].origin_name}" #direction.direction_from
#     msg_body = ""
#     for ticket in ticket:
#         msg_body += (
#         f"<b>{ticket.destination_name} ({ticket.destination_code})</b>\n" #direction.destination_code
#         f"🛫 {ticket.departure_at}\n"
#         f"💳 {int(ticket.price)} ₽ | <a href='{ticket.link}'>купить билет</a>\n\n"
#         )
#     msg = (
#         f"{msg_head}\n\n"
#         f"{msg_body}"
#     )

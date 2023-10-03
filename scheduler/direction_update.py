
from avia_bot.service import BotService
from avia_api.http_session import HttpSessionMaker
from database.mysqldb import database
from avia_api.adapter import TicketsApi
from avia_api.models import Direction
from avia_api.models import Ticket

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
        api = TicketsApi(self.http_session_maker)
        directions = await database.get_directions()
        for _direction in directions:
            direction: Direction = await parse_direction(_direction)
            await get_tickets(api, direction, self.bot)

async def parse_direction(direction: tuple):
    id_direction: id = int(direction[0])
    origin: str = direction[1]
    destination: str = direction[2]
    max_price: int = direction[3]
    count_posts: int = direction[4]
    return Direction(
        id_direction=id_direction,
        origin=origin,
        destination=destination,
        max_price=max_price,
        count_posts=count_posts
    )

async def get_tickets(api: TicketsApi, direction: Direction, bot: BotService):
    id_direction: int = int(direction.id_direction)
    origin: str = direction.origin
    destination: str = direction.destination
    max_price: int = direction.max_price
    count_posts: int = direction.count_posts
    ticket: Ticket = await api.get_ticket(origin=origin, destination=destination)
    # TODO Проверки на порог цен и так далее.
    await _notify_group(ticket, bot)

async def _notify_group(ticket: Ticket, bot: BotService):
    await bot.send_alerts_to_group(ticket)
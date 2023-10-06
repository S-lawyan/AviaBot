import aiomysql
from avia_bot.config import Settings
from avia_bot.config import config
from loguru import logger
from avia_api.models import Ticket
from datetime import datetime
from avia_api.exceptions import DatabaseAddTicketError
from avia_api.exceptions import DatabaseUpdateTicketError
from avia_api.models import PriceSettings, Direction

class DataBaseService:
    def __init__(self, _config: Settings):
        self.db_pool = None
        self.config = _config

    async def create_pool(self) -> None:
        try:
            self.db_pool = await aiomysql.create_pool(
                host=self.config.db.db_host,
                port=self.config.db.db_port,
                user=self.config.db.db_user,
                password=self.config.db.db_pass.get_secret_value(),
                db=self.config.db.db_name,
                minsize=1,
                maxsize=10,
                autocommit=True
            )
            logger.info("Pool was created successfully!")
        except Exception as e:
            logger.error(f"Ошибка при подключении к БД: {e}")

    async def execute_query(self, query):
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query)
                result = await cur.fetchall()
        return result

    async def close(self) -> None:
        self.db_pool.close()
        await self.db_pool.wait_closed()

    async def create_database_internals(self) -> None:
        query = """ CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY   
                ); """
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query)

    async def save_ticket(self, ticket: Ticket, direction: Direction):
        try:
            query = f""" INSERT INTO tickets 
            (id_direction, origin_name, destination_name, destination_code, price, departure_date, link, last_update) 
            VALUES (
                {direction.id_direction}, 
                '{ticket.origin_name}', 
                '{ticket.destination_name}', 
                '{direction.destination_code}',
                {int(ticket.price)}, 
                '{ticket.departure_at}', 
                '{ticket.link}', 
                '{datetime.now().strftime("%Y.%m.%d • %H:%M")}'
            ) """
            await self.execute_query(query)
        except Exception as e:
            logger.error(f"Ошибка при добавлении билета в БД: {e}")
            raise DatabaseAddTicketError()

    async def update_ticket(self, ticket: Ticket, direction: Direction):
        try:
            query = f""" 
                UPDATE tickets SET 
                id_direction={direction.id_direction}, 
                origin_name='{ticket.origin_name}', 
                destination_name='{ticket.destination_name}', 
                destination_code='{direction.destination_code}', 
                price={int(ticket.price)}, 
                departure_date='{ticket.departure_at}', 
                link='{ticket.link}', 
                last_update='{datetime.now().strftime("%Y.%m.%d • %H:%M")}'
            """
            await self.execute_query(query)
        except Exception as e:
            logger.error(f"Ошибка при обновлении данных билета {direction.id_direction} - {direction.destination_code} : {e}")
            raise DatabaseUpdateTicketError()

    async def get_settings(self) -> PriceSettings:
        query = """ SELECT * FROM settings """
        result = await self.execute_query(query)
        return pars_settings(result)

    async def get_directions(self):
        query = """ SELECT * FROM directions """
        return await self.execute_query(query)
        # TODO Сделать, чтобы функция возвращала список классов Direction

    async def get_ticket_(self, direction: Direction) -> Ticket | None:
        query = f""" SELECT * FROM tickets WHERE id_direction = {direction.id_direction} 
        AND destination_code = '{direction.destination_code}' """
        result = await self.execute_query(query)
        if len(result) == 0:
            return None
        else:
            return pars_ticket_(result)

def pars_ticket_(response) -> Ticket:
    data = response[0]
    origin_name: str = data[2]
    destination_name: str = data[3]
    destination_code: str = data[4]
    price: float = float(data[5])
    departure_at: str = data[6] # 2023.10.11 • 08:45
    link: str = data[7]
    last_update: str = data[8]
    return Ticket(
        price=price,
        origin_name=origin_name,
        destination_name=destination_name,
        destination_code=destination_code,
        link=link,
        departure_at=departure_at,
        last_update=last_update
    )


# def datetime_from_ticket(datetime_str: str) -> datetime:
#     """Конвертация даты и времени из API ответа в читаемый формат"""
#     return datetime.strptime(
#         str(datetime_str)[: len(datetime_str) - 9], "%Y-%m-%dT%H:%M"
#     )

def pars_settings(response) -> PriceSettings:
    data = response[0]
    difference: int = data[0]
    critical_difference: int = data[1]
    return PriceSettings(
        difference=difference,
        critical_difference=critical_difference
    )



database = DataBaseService(config)
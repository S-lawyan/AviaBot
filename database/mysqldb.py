import aiomysql
from avia_bot.config import Settings
from avia_bot.config import config
from loguru import logger
from avia_api.models import Ticket
from datetime import datetime
from avia_api.exceptions import DatabaseAddTicketError, DatabaseGetTicketError, UpdateMaxPriceDirection
from avia_api.exceptions import DatabaseUpdateTicketError
from avia_api.exceptions import DatabaseUpdateDirectionSentPostsError
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
                '{datetime.now().strftime("%d.%m.%Y • %H:%M")}'
            ) """
            await self.save_price(id_direction=direction.id_direction, destination_code=direction.destination_code,
                                  ticket=ticket)
            await self.calculating_max_price(direction=direction)
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
                WHERE id_direction={direction.id_direction} 
                and destination_code='{direction.destination_code}'
            """
            await self.save_price(id_direction=direction.id_direction, destination_code=direction.destination_code,
                                  ticket=ticket)
            await self.calculating_max_price(direction=direction)
            await self.execute_query(query)
        except Exception as e:
            logger.error(
                f"Ошибка при обновлении данных билета {direction.id_direction} - {direction.destination_code} : {e}")
            raise DatabaseUpdateTicketError()

    async def get_last_20_price(self, id_direction: int, destination_code: str) -> list:
        try:
            query = f"""
            SELECT 
                price
            FROM price_history
            WHERE id_direction={id_direction} AND destination_code='{destination_code}'
            ORDER BY datetime DESC
            LIMIT 20;
            """
            _result = await self.execute_query(query)
            result = [int(item[0]) for item in _result]
            return result
        except Exception as e:
            logger.error(
                f"Ошибка при получении цен билета из истории {id_direction} - {destination_code} : {e}")
            raise DatabaseGetTicketError()

    async def get_coefficient(self, id_direction: int, destination_code: str) -> int:
        query = f"""
            SELECT coefficient
            FROM directions
            WHERE id_direction={id_direction} AND destination_code='{destination_code}'
        """
        result = await self.execute_query(query)
        return result[0][0]

    async def calculating_max_price(self, direction: Direction):
        last_prices: list = await self.get_last_20_price(id_direction=direction.id_direction,
                                                         destination_code=direction.destination_code)
        if len(last_prices) < 20:
            return
        else:
            coefficient: int = await self.get_coefficient(id_direction=direction.id_direction,
                                                          destination_code=direction.destination_code)
            count_prices = len(last_prices)
            arithmetic_mean = int(sum(last_prices) / count_prices)
            current_max_price = arithmetic_mean + (arithmetic_mean * (coefficient / 100))
            await self.update_max_price(price=int(current_max_price), id_direction=direction.id_direction,
                                        destination_code=direction.destination_code)

    async def update_max_price(self, price: int, id_direction: int, destination_code: str):
        try:
            query = f"""
            UPDATE directions
            SET
            max_price = {price}
            WHERE id_direction={id_direction} AND destination_code='{destination_code}'
            """
            await self.execute_query(query)
            logger.info(
                f"Обновление максимальной цены билета {id_direction} - {destination_code}")
        except Exception as e:
            logger.error(
                f"Ошибка при обновлении максимальной цены билета {id_direction} - {destination_code} : {e}")
            raise UpdateMaxPriceDirection()

    # async def get_ticket_id(self, id_direction, destination_code) -> int:
    #     try:
    #         query = f"""
    #             SELECT id FROM tickets
    #             WHERE id_direction={id_direction}
    #             and destination_code='{destination_code}'
    #         """
    #         _id = await self.execute_query(query=query)
    #         return _id[0][0]
    #     except Exception as e:
    #         logger.error(f"Ошибка при получении идентификатора билета {id_direction} - {destination_code} : {e}")
    #         raise DatabaseUpdateTicketError()

    async def save_price(self, id_direction: int, destination_code: str, ticket: Ticket):
        try:
            query = f""" 
                INSERT INTO price_history 
                (id_direction, destination_code, price, datetime)
                VALUES ( 
                {id_direction},
                '{destination_code}',
                {int(ticket.price)},
                NOW()
                )
            """
            # '{date_time}'
            await self.execute_query(query)
        except Exception as e:
            logger.error(
                f"Ошибка при добавлении цены билета {id_direction} - {destination_code} : {ticket.price} : {e}")
            raise DatabaseUpdateTicketError()

    async def update_limit(self, sent_posts: int, direction: Direction):
        try:
            query = f"""
                UPDATE directions SET
                sent_posts={sent_posts}
                WHERE id_direction={direction.id_direction}
            """
            # and destination_code='{direction.destination_code}'
            await self.execute_query(query)
        except Exception as e:
            logger.error(
                f"Ошибка при обновлении sent_posts {direction.id_direction} - {direction.destination_code} : {e}")
            raise DatabaseUpdateDirectionSentPostsError()

    async def reset_limit(self) -> None:
        try:
            query = f""" UPDATE directions SET sent_posts=0 """
            await self.execute_query(query)
        except Exception as e:
            logger.error(f"Ошибка при сбросе sent_posts : {e}")
            raise DatabaseUpdateDirectionSentPostsError()

    async def get_settings(self) -> PriceSettings:
        query = """ SELECT * FROM settings """
        result = await self.execute_query(query)
        return pars_settings(result)

    async def get_directions(self) -> list[Direction] | None:
        query = """ SELECT * FROM directions """
        result = await self.execute_query(query)
        if len(result) == 0:
            return None
        else:
            return parse_directions(result)

    async def get_ticket_(self, direction: Direction) -> Ticket | None:
        try:
            query = f""" SELECT * FROM tickets WHERE id_direction = {direction.id_direction} 
            AND destination_code = '{direction.destination_code}' """
            result = await self.execute_query(query)
            if len(result) == 0:
                return None
            else:
                return pars_ticket_(result)
        except Exception as e:
            logger.error(f"Ошибка при получении билета из БД : {e}")
            raise DatabaseGetTicketError()


def parse_directions(response) -> list[Direction]:
    return [parse_direction(direction) for direction in response]


def parse_direction(direction) -> Direction:
    smail: str = direction[1]
    id_direction: id = int(direction[2])
    direction_from: str = direction[3]
    direction_to: str = direction[4]
    origin_code: str = direction[5]
    destination_code: str = direction[6]
    max_price: int = direction[7]
    count_posts: int = direction[8]
    sent_posts: int = direction[9]
    return Direction(
        smail=smail,
        id_direction=id_direction,
        direction_from=direction_from,
        direction_to=direction_to,
        origin_code=origin_code,
        destination_code=destination_code,
        max_price=max_price,
        count_posts=count_posts,
        sent_posts=sent_posts,
    )


def pars_ticket_(response) -> Ticket:
    data = response[0]
    origin_name: str = data[2]
    destination_name: str = data[3]
    destination_code: str = data[4]
    price: float = float(data[5])
    departure_at: str = data[6]
    link: str = reformat_ulr(url=data[7])
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


def reformat_ulr(url: str) -> str:
    _base = "https://tp.media/r?marker=491628&trs=273786&p=4114&u="
    _end = "&campaign_id=100"
    url = url.replace("&marker=491628", "")
    url = url.replace(":", "%3A")
    url = url.replace("/", "%2F")
    url = url.replace("=", "%3D")
    url = url.replace("&", "%26")
    reformated = _base + url + _end
    return reformated


def pars_settings(response) -> PriceSettings:
    data = response[0]
    difference: int = data[1]
    critical_difference: int = data[2]
    return PriceSettings(
        difference=difference,
        critical_difference=critical_difference
    )


database = DataBaseService(config)

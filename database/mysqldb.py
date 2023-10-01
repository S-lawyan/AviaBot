import aiomysql
from avia_bot.config import Settings
from avia_bot.config import config
from loguru import logger


class DataBaseService:
    def __init__(self, _config: Settings):
        self.db_pool = None
        self.config = _config

    async def create_pool(self):
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


    async def close(self):
        self.db_pool.close()
        await self.db_pool.wait_closed()

    async def create_database_internals(self):
        query = """ CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY   
                ); """
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query)

database = DataBaseService(config)
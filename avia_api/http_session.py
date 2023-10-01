import aiohttp
from aiohttp import ClientSession

class HttpSessionMaker:
    def __init__(self):
        self.session: aiohttp.ClientSession | None = None

    def __call__(self):
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        if self.session:
            await self.session.close()

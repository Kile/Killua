"""
This file includes one "download" function which downloads all cards to a local file to be able to run 
tests with them offline later
"""
import json
import aiohttp
from .static.constants import CARDS_URL

async def download():
    async with aiohttp.ClientSession() as session:
        async with session.get(CARDS_URL) as resp:
            data = await resp.text()
            data = json.loads(data)
            with open("cards.json", "w") as f:
                f.write(json.dumps(data))
                f.close()
        await session.close()
    
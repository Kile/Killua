"""
This file includes one "download" function which downloads all cards to a local file to be able to run 
tests with them offline later
"""

import json
import aiohttp
from .static.constants import CARDS_URL
from .static.enums import PrintColors
from logging import info


async def download():
    async with aiohttp.ClientSession() as session:
        info(f"Downloading cards...")
        async with session.get(CARDS_URL) as resp:
            if resp.status != 200:
                info(f"{PrintColors.FAIL}Failed to download cards{PrintColors.ENDC}")
                return
            data = await resp.json()
            info(f"{PrintColors.OKGREEN}GET request successful{PrintColors.ENDC}")
            with open("api/src/cards.json", "w+") as f:
                f.write(json.dumps(data))
                f.close()
                info(f"{PrintColors.OKGREEN}Cards saved to file (api/src/cards.json){PrintColors.ENDC}")
                info("These cards are now available for offline testing. To use the locally downloaded cards, run the bot with the -fl flag.")
            await session.close()
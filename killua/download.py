"""
This file includes one "download" function which downloads all cards to a local file to be able to run 
tests with them offline later
"""

import json
import aiohttp
from .static.constants import CARDS_URL
from .static.enums import PrintColors
from logging import info
from typing import Literal
from os import environ


async def download(choice: Literal["public", "private"]) -> None:
    if choice == "private":
        AUTHORIZATION = environ.get("API_KEY")
        if AUTHORIZATION is None:
            info(f"{PrintColors.FAIL}API_KEY environment variable not set (needed to download the private version of cards){PrintColors.ENDC}")
            return
        headers = {"Authorization": AUTHORIZATION}
    else:
        headers = {}
        
    session = aiohttp.ClientSession()
    info(f"Downloading cards...")
    resp = await session.get(CARDS_URL + ("true" if choice == "public" else "false"), headers=headers)
    if resp.status != 200:
        info(f"{PrintColors.FAIL}Failed to download cards. API returned error code {resp.status}-{PrintColors.ENDC}")
        await session.close()
        return
    data = await resp.json()
    info(f"{PrintColors.OKGREEN}GET request successful for {choice} cards{PrintColors.ENDC}")
    with open("cards.json", "w+") as f:
        f.write(json.dumps(data))
        f.close()
        info(f"{PrintColors.OKGREEN}Cards saved to file (cards.json){PrintColors.ENDC}")
        info("These cards are now available for offline testing. To use the locally downloaded cards, run the bot with the -fl flag.")
    await session.close()
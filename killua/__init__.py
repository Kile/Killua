from . import cogs
import discord
import aiohttp
import logging
from prometheus_client import Counter

from .tests import run_tests
from .migrate import migrate
from .download import download
from .bot import BaseBot as Bot, get_prefix
# This needs to be in a seperate file from the __init__ file to
# avoid relative import errors when subclassing it in the testing module
from .static.constants import TOKEN
from .metrics import PrometheusLoggingHandler

import killua.args as args_file

async def main():
    args_file.Args.get_args()

    args = args_file.Args

    # Set up logger from command line arguments
    logging.basicConfig(
        level=getattr(logging, args.log.upper()), 
        datefmt='%I:%M:%S', 
        format="[%(asctime)s] %(levelname)s: %(message)s",
        handlers=[PrometheusLoggingHandler()]
    )

    if args.migrate:
        return migrate()

    if args.test is not None:
        return await run_tests(args.test)

    if args.download:
        return await download()

    session = aiohttp.ClientSession()
    intents = discord.Intents(
        guilds=True,
        members=True,
        emojis_and_stickers=True, # this is not needed in the code but I'd like to have it
        messages=True,
        message_content=True
    )
    # Create the bot instance.
    bot = Bot(
        command_prefix=get_prefix,
        description="The discord bot Killua",
        case_insensitive=True,
        intents=intents,
        session=session
    )
    bot.session = session
    # Checks if the bot is a dev bot
    bot.is_dev = args.development
    bot.run_in_docker = args.docker

    # Setup cogs.
    for cog in cogs.all_cogs:
        await bot.add_cog(cog.Cog(bot))
       
    await bot.start(TOKEN)
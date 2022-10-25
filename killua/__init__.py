from . import cogs
import discord
import aiohttp
import asyncio
import logging

from .tests import run_tests
# from .tests.types.db import TestingDatabase as Database
from .migrate import migrate
from .bot import BaseBot as Bot, get_prefix
# This needs to be in a seperate file from the __init__ file to
# avoid relative import errors when subclassing it in the testing module
from .webhook.api import app
from .utils.help import MyHelp
from .static.constants import TOKEN, PORT

import killua.args as args_file

# class TestingDB:
#     teams = Database("teams")
#     items = Database("items")
#     guilds = Database("guilds")

#     shop = Database("shop")
#     blacklist = Database("blacklist")
#     stats = Database("stats")
#     presence = Database("presence")
#     todo = Database("todo")
#     updates = Database("updates")

async def main():
	args_file.Args.get_args()

	args = args_file.Args

	# Set up logger from command line arguments
	logging.basicConfig(level=getattr(logging, args.log.upper()), datefmt='%I:%M:%S', format="[%(asctime)s] %(levelname)s: %(message)s")

	if args.migrate:
		return migrate()

	if args.test is not None:
		return await run_tests(args.test)

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
	# Setup commands.
	bot.help_command = MyHelp()
	# Checks if the bot is a dev bot
	bot.is_dev = args.development

	# Setup cogs.
	for cog in cogs.all_cogs:
		await bot.add_cog(cog.Cog(bot))

	if bot.is_dev: # runs the api locally if the bot is in dev mode
		# loop = asyncio.get_event_loop()
		await asyncio.wait([bot.start(TOKEN), app.run_task(host="0.0.0.0", port=PORT)], return_when=asyncio.FIRST_COMPLETED)
		# loop.run_forever()
		# Thread(target=loop.run_forever).start()
	else:
		# Start the bot.		
		await bot.start(TOKEN)
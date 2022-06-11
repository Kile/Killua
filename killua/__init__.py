from . import cogs
import discord
import aiohttp
import asyncio
import getopt, sys

from .tests import run_tests
from .bot import BaseBot as Bot, get_prefix
# This needs to be in a seperate file from the __init__ file to
# avoid relative import errors when subclassing it in the testing module
from .webhook.api import app
from .utils.help import MyHelp
from .static.constants import TOKEN, PORT

def is_dev() -> bool:
	"""Checks if the bot is run with the --development argument"""
	raw_arguments = sys.argv[1:]

	arguments, _ = getopt.getopt(raw_arguments, "d", ["development"])
	for arg, _ in arguments:
		if arg in ("--development", "-d"):
			return True
	return False

def should_run_tests() -> bool:
	"""Checks wether arguments were given to run the tests"""
	raw_arguments = sys.argv[1:]

	arguments, _ = getopt.getopt(raw_arguments, "td", ["test", "development"])
	for arg, _ in arguments:
		if arg in ("--test", "-t"):
			return True
	return False

async def main():
	if should_run_tests():
		return await run_tests()

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
	bot.is_dev = is_dev()

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
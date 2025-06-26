from . import cogs
import discord
import aiohttp
import asyncio
import logging

from .tests import run_tests
from .migrate import migrate
from .download import download
from .bot import BaseBot as Bot, get_prefix
# This needs to be in a seperate file from the __init__ file to
# avoid relative import errors when subclassing it in the testing module
from .webhook.api import app
from .static.constants import TOKEN, PORT

import killua.args as args_file

async def main():
	start_time = time.time()
	args_file.Args.get_args()
	args = args_file.Args

	# Set up logger from command line arguments
	log_level = getattr(logging, args.log.upper())
	logging.basicConfig(
		level=log_level, 
		datefmt='%I:%M:%S', 
		format="[%(asctime)s] %(levelname)s: %(message)s"
	)
	logger = logging.getLogger('killua')
	logger.info(f"Starting Killua bot with log level: {args.log.upper()}")

	# Check if MongoDB is running before proceeding
	try:
		logger.info("Checking MongoDB connection...")
		# Set a shorter timeout for faster startup
		DB.const.database.client.server_info()
		logger.info("MongoDB connection successful")
	except Exception as e:
		logger.critical(f"MongoDB connection failed: {e}")
		logger.critical("Please make sure MongoDB is running and the connection string is correct in config.json")
		logger.critical("Bot cannot start without a database connection. Exiting...")
		return 1

	if args.migrate:
		logger.info("Running database migration")
		return migrate()

	if args.test is not None:
		logger.info(f"Running tests: {args.test}")
		return await run_tests(args.test)

	if args.download:
		logger.info("Running download operation")
		return await download()

	logger.info("Initializing HTTP session")
	async with aiohttp.ClientSession() as session:
		logger.info("Setting up Discord intents")
		intents = discord.Intents(
			guilds=True,
			members=True,
			emojis_and_stickers=True,
			messages=True,
			message_content=True
		)
		
		# Create the bot instance
		logger.info("Creating bot instance")
		bot = Bot(
			command_prefix=get_prefix,
			description="The discord bot Killua",
			case_insensitive=True,
			intents=intents,
			session=session
		)
		bot.session = session
		
		# Set development mode
		bot.is_dev = args.development
		logger.info(f"Development mode: {bot.is_dev}")

		# Setup cogs
		logger.info(f"Loading {len(cogs.all_cogs)} cogs...")
		cog_load_start = time.time()
		for i, cog_module in enumerate(cogs.all_cogs):
			try:
				logger.debug(f"Loading cog {i+1}/{len(cogs.all_cogs)}: {cog_module.__name__}")
				await bot.add_cog(cog_module.Cog(bot))
			except Exception as e:
				logger.error(f"Failed to load cog {cog_module.__name__}: {e}")
		logger.info(f"Loaded all cogs in {time.time() - cog_load_start:.2f} seconds")

		# Calculate startup time
		logger.info(f"Bot initialization completed in {time.time() - start_time:.2f} seconds")

		if bot.is_dev: # runs the api locally if the bot is in dev mode
			logger.info(f"Starting development server on port {PORT}")
			# Use asyncio.create_task instead of deprecated get_event_loop
			tasks = [bot.start(TOKEN), app.run_task(host="0.0.0.0", port=PORT)]
			logger.info("Bot is now running in development mode")
			done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
			# Cancel any pending tasks
			for task in pending:
				task.cancel()
		else:
			# Start the bot in production mode
			logger.info("Starting bot in production mode")
			await bot.start(TOKEN)
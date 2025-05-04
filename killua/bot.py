import logging
import math
import asyncio
import discord
import jishaku
import time
import sys

from typing import Dict, Union, List, Tuple, Coroutine, Any, Optional
from datetime import date, datetime
from random import randint, choice
from discord.ext import commands
from aiohttp import ClientSession

from killua.static.constants import *
from killua.static.tips import TIPS
from killua.utils.db import DB
from killua.utils.enums import Category
from killua.utils.functions import get_prefix
from killua.utils.ui import Modal
from killua.utils.migrate import migrate_requiring_bot

# Configure root logger
logging.basicConfig(level=logging.INFO, 
                   format='[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s',
                   datefmt='%Y-%m-%d %H:%M:%S')

# Create a logger for this module
logger = logging.getLogger('killua.bot')

def get_prefix(bot, message):
	if bot.is_dev:
		return commands.when_mentioned_or('kil!', 'kil.')(bot, message)
	try:
		from .utils.classes import Guild
		
		g = Guild(message.guild.id)
		if g is None:
			return commands.when_mentioned_or('k!')(bot, message)
		return commands.when_mentioned_or(g.prefix)(bot, message)
	except Exception:
		# in case message.guild is `None` or something went wrong getting the prefix the bot still NEEDS to react to mentions and k!
		return commands.when_mentioned_or('k!')(bot, message)

class BaseBot(commands.AutoShardedBot):
	def __init__(self, *args, **kwargs):
		logger.info("Initializing Killua bot...")
		self.startup_time = time.time()
		
		# Extract session from kwargs if provided
		self.session = kwargs.pop('session', None)
		logger.debug(f"Session provided: {self.session is not None}")
		
		# Set modern defaults for Discord.py 2.5+
		kwargs.setdefault('chunk_guilds_at_startup', False)
		kwargs.setdefault('max_messages', 10000)  # Increase message cache for better performance
		kwargs.setdefault('enable_debug_events', False)
		kwargs.setdefault('assume_unsync_clock', True)  # Better for distributed systems
		
		logger.info("Calling parent constructor with optimized settings")
		super().__init__(*args, **kwargs)

		# Bot configuration
		self.support_server_invite = "https://discord.gg/MKyWA5M"
		self.invite = "https://discord.com/oauth2/authorize?client_id=756206646396452975&scope=bot%20applications.commands&permissions=268723414"
		self.is_dev = False
		logger.info(f"Development mode: {self.is_dev}")
		
		# Performance optimizations
		self._command_cache = {}
		self._formatted_commands_cache = None
		logger.info("Bot initialization complete")

	async def setup_hook(self):
		logger.info("Setting up bot hooks and extensions...")
		
		# Check MongoDB connection first
		try:
			logger.info("Testing MongoDB connection...")
			db_info = DB.const.database.client.server_info()
			logger.info(f"Connected to MongoDB version: {db_info.get('version', 'unknown')}")
		except Exception as e:
			logger.critical(f"MongoDB connection failed: {e}")
			logger.critical("Please make sure MongoDB is running and the connection string is correct in config.json")
			logger.critical("Bot cannot start without a database connection. Exiting...")
			sys.exit(1)
		
		# Load extensions
		try:
			logger.info("Loading jishaku extension...")
			await self.load_extension("jishaku")
			logger.info("Successfully loaded jishaku extension")
		except Exception as e:
			logger.error(f"Failed to load jishaku: {e}")
		
		# Sync application commands
		try:
			logger.info("Syncing application commands...")
			await self.tree.sync()
			logger.info("Successfully synced application commands")
		except Exception as e:
			logger.error(f"Failed to sync application commands: {e}")
		
		# Check for migration
		try:
			logger.info("Checking for pending database migrations...")
			migrate_doc = DB.const.find_one({"_id": "migrate"})
			if migrate_doc and migrate_doc.get("value", False):
				logger.info("Running database migration...")
				migrate_requiring_bot(self)
				logger.info("Database migration completed successfully")
			else:
				logger.info("No pending migrations found")
		except Exception as e:
			logger.error(f"Failed to check/run migration: {e}")
			
		logger.info("Bot setup completed successfully")

	async def close(self):
		# Clean up resources before closing
		logger.info("Bot is shutting down, cleaning up resources...")
		
		# Calculate uptime
		uptime = time.time() - self.startup_time
		logger.info(f"Bot was running for {uptime:.2f} seconds")
		
		# Clear caches
		logger.debug("Clearing command caches")
		self._command_cache.clear()
		self._formatted_commands_cache = None
		
		# Only close the session if it was created by this instance and not passed in
		if hasattr(self, 'session') and self.session is not None and not self.session.closed:
			try:
				logger.info("Closing HTTP session")
				await self.session.close()
				logger.debug("HTTP session closed successfully")
			except Exception as e:
				logger.error(f"Error closing session: {e}")
		
		# Call parent close method
		logger.info("Calling parent close method")
		await super().close()
		logger.info("Bot shutdown complete")

	def __format_command(self, res: Dict[str, list], cmd: commands.Command) -> dict:
		"""Adds a command to a dict of formatted commands"""
		if cmd.name in ["jishaku", "help"] or cmd.hidden:
			return res

		res[cmd.extras["category"].value["name"]]["commands"].append(cmd)
        
		return res

	def get_formatted_commands(self) -> dict:
		"""Gets a dictionary of formatted commands with caching for better performance"""
		# Return cached result if available
		if self._formatted_commands_cache is not None:
			return self._formatted_commands_cache
		
		# Initialize result dictionary
		res = {c.value["name"]: {"description": c.value["description"], "emoji": c.value["emoji"], "commands": []} for c in Category}

		# Process commands
		for cmd in self.commands:
			if isinstance(cmd, commands.Group) and cmd.name != "jishaku":
				for c in cmd.commands:
					res = self.__format_command(res, c)
				continue
			res = self.__format_command(res, cmd)

		# Cache the result
		self._formatted_commands_cache = res
		return res

	async def find_user(self, ctx: commands.Context, user: str) -> Union[discord.Member, discord.User, None]:
		"""Attempts to create a member or user object from the passed string
		Optimized for Python 3.11 with better error handling"""
		# Check if input is empty
		if not user:
			return None
		
		# Try to convert to member first (most common case)
		try:
			return await commands.MemberConverter().convert(ctx, user)
		except commands.MemberNotFound:
			pass
		
		# If not a digit ID, return None
		if not user.isdigit():
			return None

		# Try to get from cache first (faster)
		user_id = int(user)
		res = self.get_user(user_id)
		if res:
			return res
		
		# Fetch from API as last resort
		try:
			return await self.fetch_user(user_id)
		except (discord.NotFound, discord.HTTPException):
			return None

	def get_lootbox_from_name(self, name: str) -> Union[int, None]:
		"""Gets a lootbox id from its name"""
		for k, v in LOOTBOXES.items():
			if name.lower() == v["name"].lower():
				return k

	def callback_from_command(self, command: Coroutine, message: bool, *args, **kwargs) -> Coroutine[discord.Interaction, Union[discord.Member, discord.Message], None]:
		"""Turn a command function into a context menu callback"""
		if message:
			async def callback(interaction: discord.Interaction, message: discord.Message):
				ctx = await commands.Context.from_interaction(interaction)
				ctx.message = message
				ctx.invoked_by_context_menu = True # This is added so we can check inside of the command if it was invoked from a modal
				await ctx.invoke(command, text=message.content, *args, **kwargs)
		else:
			async def callback(interaction: discord.Interaction, member: discord.Member):
				ctx = await commands.Context.from_interaction(interaction)
				ctx.invoked_by_context_menu = True
				await ctx.invoke(command, str(member.id), *args, **kwargs)
		return callback

	async def get_text_response(
		self, 
		ctx: commands.Context, 
		text: str, 
		timeout: int = None, 
		timeout_message: str = None, 
		interaction: discord.Interaction = None,
		*args, 
		**kwargs
	) -> Union[str, None]:
		"""Gets a reponse from either a textinput UI or by waiting for a response"""

		if (ctx.interaction and not ctx.interaction.response.is_done()) or interaction:
			modal = Modal(title="Anser the question(s) and click submit", timeout=timeout)
			textinput = discord.ui.TextInput(label=text, *args, **kwargs)
			modal.add_item(textinput)

			if interaction:
				await interaction.response.send_modal(modal)
			else:
				await ctx.interaction.response.send_modal(modal)

			await modal.wait()
			if modal.timed_out:
				if timeout_message:
					await ctx.send(timeout_message, delete_after=5)
				return
			await modal.interaction.response.defer()

			return textinput.value

		else:
			def check(m: discord.Message):
				return m.author.id == ctx.author.id

			msg = await ctx.send(text)
			try:
				confirmmsg: discord.Message = await self.wait_for('message', check=check, timeout=timeout)
			except asyncio.TimeoutError:
				if timeout_message:
					await ctx.send(timeout_message, delete_after=5)
				res = None
			else:
				res = confirmmsg.content

			await msg.delete()
			try:
				await confirmmsg.delete()
			except commands.Forbidden:
				pass
			
			return res

	async def update_presence(self):
		"""Update the bot's presence with improved error handling and caching"""
		logger.debug("Updating bot presence...")
		try:
			# Try to get custom presence from database
			logger.debug("Fetching presence data from database")
			status = DB.const.find_one({"_id": "presence"})
			if status and status.get('text'):
				logger.info(f"Using custom presence: {status['text']}")
				# Set defaults if missing
				activity_type = status.get('activity', 'playing')
				presence_status = status.get('presence', 'online')
				
				# Create activity object
				activity = discord.Activity(
					name=status['text'], 
					type=getattr(discord.ActivityType, activity_type)
				)
				
				# Update presence
				logger.debug(f"Setting presence: {activity.name} ({activity.type.name})")
				await self.change_presence(
					activity=activity, 
					status=getattr(discord.Status, presence_status)
				)
				return
			
			# Calculate bot age
			today = date.today()
			bot_birthday = date(2020, 9, 17)  # The day Killua was born!!
			days_running = (today - bot_birthday).days
			
			# Create default activity
			logger.info(f"Using default presence for {len(self.guilds)} guilds")
			playing = discord.Activity(
				name=f'over {len(self.guilds)} guilds | k! | day {days_running}', 
				type=discord.ActivityType.watching
			)
			
			# Update presence
			logger.debug(f"Setting default presence: {playing.name}")
			await self.change_presence(status=discord.Status.online, activity=playing)
			logger.info("Presence updated successfully")
		except Exception as e:
			logger.error(f"Failed to update presence: {e}")

	async def send_message(self, messageable: discord.abc.Messageable, *args, **kwargs) -> discord.Message:
		"""A helper function sending messages and adding a tip with the probability of 5%"""
		msg = await messageable.send(*args, **kwargs)
		if randint(1, 100) < 6: # 5% probability to send a tip afterwards
			await messageable.send(f"**Tip:** {choice(TIPS).replace('<prefix>', get_prefix(self, messageable.message)[2]) if hasattr(messageable, 'message') else ('k!' if not self.is_dev else 'kil!')}", ephemeral=True)
		return msg

	def convert_to_timestamp(self, id: int, args: str = "f") -> str:
		"""Turns a discord snowflake into a discord timestamp string"""
		return f"<t:{int((id >> 22) / 1000) + 1420070400}:{args}>"

	def _encrypt(self, n: int, b: int = 10000, smallest: bool = True) -> str:
		"""Changes an integer into base 10000 but with my own characters resembling numbers. It only returns the last 2 characters as they are the most unique"""
		chars = "".join([chr(i) for i in range(b+1)][::-1])
		chars = chars.replace(":", "").replace(";", "").replace("-", "").replace(",", "") # These characters are indicators used in the ids so they should be not be available as characters

		if n == 0:
			return [0]
		digits = []
		while n:
			digits.append(int(n % b))
			n //= b
		return "".join([chars[d] for d in digits[::-1]])[-2:] if smallest else "".join([chars[d] for d in digits[::-1]])
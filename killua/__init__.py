from . import cogs
import discord
import aiohttp
import asyncio
import getopt, sys
from random import randint, choice
from discord.ext import commands, ipc
from datetime import date
from typing import Union
from threading import Thread

from .webhook.api import app
from .utils.help import MyHelp
from .utils.classes import Guild
from .static.enums import Category
from .static.constants import TOKEN, IPC_TOKEN, presence, TIPS, PORT

class Bot(commands.Bot):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.support_server_invite = "https://discord.gg/MKyWA5M"
		self.invite = "https://discord.com/oauth2/authorize?client_id=756206646396452975&scope=bot&permissions=268723414&applications.commands"
		self.ipc = ipc.Server(self, secret_key=IPC_TOKEN)
		self.is_dev = False

	async def on_ipc_error(self, endpoint, error):
		print(endpoint, "raised", error)

	def __format_command(self, res:dict, cmd:commands.Command, group:Union[None, str]=None) -> dict:
		"""Adds a command to a dict of formatted commands"""
		if cmd.name in ["jishaku", "help"] or cmd.hidden:
			return res

		res[cmd.extras["category"].value["name"]]["commands"].append({"name": cmd.name, "usage": cmd.usage, "help": cmd.help, "parent": group})
        
		return res

	def get_formatted_commands(self) -> dict:
		"""Gets a dictionary of formatted commands"""
		res = {c.value["name"]:{"description":c.value["description"], "emoji": c.value["emoji"], "commands": []} for c in Category}

		for cmd in self.commands:
			if isinstance(cmd, commands.Group) and cmd.name != "jishaku":
				for c in cmd.commands:
					res = self.__format_command(res, c, group=cmd.qualified_name)
				continue
			res = self.__format_command(res, cmd)

		return res

	async def update_presence(self):
		status = presence.find_one({})
		if status['text']:
			if not status['activity']:
				status['activity'] = 'playing'
			if status['activity'] == 'playing':
				s = discord.Activity(name=status['text'], type=discord.ActivityType.playing)
			if status['activity'] == 'watching':
				s = discord.Activity(name=status['text'], type=discord.ActivityType.watching)
			if status['activity'] == 'listening':
				s = discord.Activity(name=status['text'], type=discord.ActivityType.listening)
			if status['activity'] == 'competing':
				s = discord.Activity(name=status['text'], type=discord.ActivityType.competing)

				
			if not status['presence']:
				status['presence'] = 'online'
			if status['presence'] == 'online':
				return await self.change_presence(status=discord.Status.online, activity=s)
			if status['presence'] == 'dnd':
				return await self.change_presence(status=discord.Status.dnd, activity=s)
			if status['presence'] == 'idle':
				return await self.change_presence(status=discord.Status.idle, activity=s)
		a = date.today()
		#The day Killua was born!!
		b = date(2020,9,17)
		delta = a - b
		playing = discord.Activity(name=f'over {len(self.guilds)} guilds | k! | day {delta.days}', type=discord.ActivityType.watching)
		return await self.change_presence(status=discord.Status.online, activity=playing)

	async def send_message(self, messageable:discord.abc.Messageable, *args, **kwargs) -> discord.Message:
		"""A helper function sending messages and adding a tip with the probability of 5%"""
		msg = await messageable.send(*args, **kwargs)
		if randint(1, 100) < 6: # 5% probability to send a tip afterwards
			await messageable.send(f"**Tip:** {choice(TIPS).replace('<prefix>', get_prefix(self, messageable.message)[2]) if hasattr(messageable, 'message') else ('k!' if not self.is_dev else 'kil!')}")
		return msg

	def convert_to_timestamp(self, id: int, args: str = "f") -> str:
		"""Turns a discord snowflake into a discord timestamp string"""
		return f"<t:{int((id >> 22) / 1000) + 1420070400}:{args}>"


def is_dev() -> bool:
	"""Checks if the bot is run with the --development argument"""
	raw_arguments = sys.argv[1:]

	arguments, _ = getopt.getopt(raw_arguments, "d", ["development"])
	for arg, _ in arguments:
		if arg in ("--development", "-d"):
			return True
	return False

def get_prefix(bot, message):
	if bot.is_dev:
		return commands.when_mentioned_or('kil!', 'kil.')(bot, message)
	try:
		g = Guild(message.guild.id)
		if g is None:
			return commands.when_mentioned_or('k!')(bot, message)
		return commands.when_mentioned_or(g.prefix)(bot, message)
	except Exception:
		# in case message.guild is `None` or something went wrong getting the prefix the bot still NEEDS to react to mentions and k!
		return commands.when_mentioned_or('k!')(bot, message)

def main():
	session = aiohttp.ClientSession()
	intents = discord.Intents(
		guilds=True,
		members=True,
		emojis_and_stickers=True, # this is not needed in the code but I'd like to have it
		messages=True
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
		bot.add_cog(cog.Cog(bot))

	bot.load_extension("jishaku")
	bot.ipc.start()

	if bot.is_dev: # runs the api locally if the bot is in dev mode
		loop = asyncio.get_event_loop()
		loop.create_task(bot.start(TOKEN))
		Thread(target=loop.run_forever).start()
		app.run(host="0.0.0.0", port=PORT)
	else:
		# Start the bot.
		bot.run(TOKEN)
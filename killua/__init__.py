from . import cogs
import discord
#from discord.ext.commands import command as discord_command, \
#	group as discord_group
from discord.ext import commands
import json
import aiohttp
from pymongo import MongoClient
from typing import Callable, Coroutine
from .help import MyHelp

# all_commands = []

# def command(*args, **kwargs):
# 	"""Converts the decorated symbol into a command, and also adds that command to
# 	the all_commands list."""

# 	def decorator(function: Callable[..., Coroutine]):
# 		command = discord_command(*args, **kwargs)(function)
# 		all_commands.append(command)
# 		return command
# 	return decorator

# def group(*args, **kwargs):
# 	"""Converts the decorated symbol into a group, and also adds that group to the
# 	all_commands list."""

# 	def decorator(function: Callable[..., Coroutine]):
# 		group = discord_group(*args, **kwargs)(function)
# 		all_commands.append(group)
# 		return group
# 	return decorator


with open('config.json', 'r') as config_file:
    config = json.loads(config_file.read())

cluster = MongoClient(config['mongodb'])
db = cluster['Killua']
collection = db['teams']
top = db['teampoints']
server = db['guilds']

def get_prefix(bot, message):
	if bot.user.id == 758031913788375090:
		return commands.when_mentioned_or('kil!', 'kil.')(bot, message)
	try:
		y = server.find_one({'id': message.guild.id})
		if y is None:
			return commands.when_mentioned_or('k!')(bot, message)
		return commands.when_mentioned_or(y['prefix'])(bot, message)
	except Exception:
		return commands.when_mentioned_or('k!')(bot, message)


def main():
	session = aiohttp.ClientSession()
	intents = discord.Intents.all()
	intents.presences = False
	# Create the bot instance.
	bot = commands.Bot(
		command_prefix=get_prefix,
		description="The discord bot Killua",
		case_insensitive=True,
		intents=intents,
		session=session
	)
	bot.session = session
	# Setup commands.
	bot.help_command = MyHelp()
#	for command in all_commands:
#		bot.add_command(command)

	# Setup cogs.
	for cog in cogs.all_cogs:
		bot.add_cog(cog.Cog(bot))

	# Start the bot.
	bot.load_extension("jishaku")
	bot.run(config['token'])
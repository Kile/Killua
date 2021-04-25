from . import cogs
import discord
from datetime import datetime, timedelta
from discord.ext.commands import command as discord_command, \
	group as discord_group
from discord.ext import commands
from inspect import getsource
from io import BytesIO
from json import loads
import json
from pymongo import MongoClient
from random import choice, randint
from typing import Callable, Coroutine

all_commands = []

def command(*args, **kwargs):
	"""Converts the decorated symbol into a command, and also adds that command to
	the all_commands list."""

	def decorator(function: Callable[..., Coroutine]):
		command = discord_command(*args, **kwargs)(function)
		all_commands.append(command)
		return command
	return decorator

def group(*args, **kwargs):
	"""Converts the decorated symbol into a group, and also adds that group to the
	all_commands list."""

	def decorator(function: Callable[..., Coroutine]):
		group = discord_group(*args, **kwargs)(function)
		all_commands.append(group)
		return group
	return decorator


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


@command()
async def load(ctx, extension):
	if ctx.author.id == 606162661184372736:
		ctx.bot.load_extension(f'killua.cogs.{extension}')
		await ctx.send(f'Loaded cog `{extension}`')

@command()
async def unload(ctx, extension):
	if ctx.author.id == 606162661184372736:
		ctx.bot.unload_extension(f'killua.cogs.{extension}')
		await ctx.send(f'Unloaded cog `{extension}`')


def main():
	intents = discord.Intents.all()
	intents.presences = False
	# Create the bot instance.
	bot = commands.AutoShardedBot(
		command_prefix=get_prefix,
		description="The discord bot Killua",
		case_insensitive=True,
		intents=intents
	)

	# Setup commands.
	bot.remove_command('help')
	for command in all_commands:
		bot.add_command(command)

	# Setup cogs.
	for cog in cogs.all_cogs:
		bot.add_cog(cog.Cog(bot))

	# Start the bot.
	bot.load_extension("jishaku")
	bot.run(config['token'])

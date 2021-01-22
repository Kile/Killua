from . import cogs
import discord
from datetime import datetime, timedelta
from discord import Embed, File
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
	try:
		y = server.find_one({'id': message.guild.id})
		if y is None:
			return 'k!'
		try:
			return y['prefix']
		except KeyError:
			return 'k!'
	except:
		return 'k!'

@command()
async def load(ctx, extension):
	if ctx.author.id == 606162661184372736:
		ctx.bot.load_extension(f'cogs.{extension}')
		await ctx.send(f'Loaded cog `{extension}`')

@command()
async def unload(ctx, extension):
	if ctx.author.id == 606162661184372736:
		ctx.bot.unload_extension(f'cogs.{extension}')
		await ctx.send(f'Unloaded cog `{extension}`')


def main():
	intents = discord.Intents.all()
	intents.presences = False
	# Create the bot instance.
	bot = commands.Bot(
		command_prefix=get_prefix,
		description="default prefix",
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

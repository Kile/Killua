from . import cogs
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
	y = server.find({'id': message.guild.id})
	for x in y:
		prefix = x['prefix']
		return prefix
	return 'k!'

huggif = [f'https://i.pinimg.com/originals/66/9b/67/669b67ae57452f7afbbe5252b6230f85.gif', f'https://i.pinimg.com/originals/70/83/0d/70830dfba718d62e7af95e74955867ac.jpg', 'https://cdn.discordapp.com/attachments/756945125568938045/756945463432839168/image0.gif', 'https://cdn.discordapp.com/attachments/756945125568938045/756945308381872168/image0.gif', 'https://cdn.discordapp.com/attachments/756945125568938045/756945151191941251/image0.gif', 'https://pbs.twimg.com/media/Dl4PPE4UUAAsb7c.jpg', 'https://encrypted-tbn0.gstatic.com/images?q=tbn%3AANd9GcSJgTjRyQW3NzmDzlvskIS7GMjlFpyS7yt_SQ&usqp=CAU', 'https://static.zerochan.net/Hunter.x.Hunter.full.1426317.jpg', 'https://encrypted-tbn0.gstatic.com/images?q=tbn%3AANd9GcQJjVWplBdqrasz8Fh-7nDkxRjnnNBqk0bZlQ&usqp=CAU', 'https://i.pinimg.com/originals/75/2e/0a/752e0a5f813400dfebe322fc8b0ad0ae.jpg', 'https://thumbs.gfycat.com/IllfatedComfortableAplomadofalcon-small.gif', 'https://steamuserimages-a.akamaihd.net/ugc/492403625757327002/9B089509DDCB6D9F8E11446C7F1BC29B9BA57384/', f'https://cdn.discordapp.com/attachments/756945125568938045/758235270524698634/image0.gif', f'https://cdn.discordapp.com/attachments/756945125568938045/758236571974762547/image0.jpg', 'https://cdn.discordapp.com/attachments/756945125568938045/758236721216749638/image0.jpg', 'https://cdn.discordapp.com/attachments/756945125568938045/758237072975855626/image0.jpg', 'https://cdn.discordapp.com/attachments/756945125568938045/758237082484473856/image0.jpg', 'https://cdn.discordapp.com/attachments/756945125568938045/758237352756903936/image0.png', 'https://cdn.discordapp.com/attachments/756945125568938045/758237832954249216/image0.jpg']


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


@command()
async def hug(ctx, *, content=None):
	#c Best hug command out there
	#t 1-3 hours
	if ctx.message.mentions:
		if ctx.author == ctx.message.mentions[0]:
			return await ctx.send(f'Someone hug {ctx.author.name}!')

		hugtext = [f'**{ctx.author.name}** hugs **{ctx.message.mentions[0].name}** as strong as they can', f'**{ctx.author.name}** hugs **{ctx.message.mentions[0].name}** and makes sure to not let go', f'**{ctx.author.name}** gives **{ctx.message.mentions[0].name}** the longest hug they have ever seen', f'**{ctx.author.name}** cuddles **{ctx.message.mentions[0].name}**', f'**{ctx.author.name}** uses **{ctx.message.mentions[0].name}** as a teddybear', f'**{ctx.author.name}** hugs **{ctx.message.mentions[0].name}** until all their worries are gone and 5 minutes longer',f'**{ctx.author.name}** clones themself and together they hug **{ctx.message.mentions[0].name}**', f'**{ctx.author.name}** jumps in **{ctx.message.mentions[0].name}**\'s arms', f'**{ctx.author.name}** gives **{ctx.message.mentions[0].name}** a bearhug', f'**{ctx.author.name}** finds a lamp with a Jinn and gets a wish. So they wish to hug **{ctx.message.mentions[0].name}**', f'**{ctx.author.name}** asks **{ctx.message.mentions[0].name}** for motivation and gets a hug']
		embed = Embed.from_dict({
			'title': choice(hugtext),
			'image':{
				'url': choice(huggif)
			},
			'color': 0x1400ff
			})
		await ctx.send(embed=embed)
	else:
		await ctx.send('Invalid user.. Should- I hug you?')
		def check(m):
			return m.content.lower() == 'yes' and m.author == ctx.author

		msg = await ctx.bot.wait_for('message', check=check, timeout=60)
		hugtextself = [f'**Killua** hugs **{ctx.author.name}** as strong as they can', f'**Killua** hugs **{ctx.author.name}** and makes sure to not let go', f'**Killua** gives **{ctx.author.name}** the longest hug they have ever seen', f'**Killua** cuddles **{ctx.author.name}**', f'**Killua** uses **{ctx.author.name}** as a teddybear', f'**Killua** hugs **{ctx.author.name}** until all their worries are gone and 5 minutes longer',f'**Killua** clones themself and together they hug **{ctx.author.name}**', f'**Killua** jumps in **{ctx.author.name}**\'s arms', f'**Killua** gives **{ctx.author.name}** a bearhug', f'**Killua** finds a lamp with a Jinn and gets a wish. So they wish to hug **{ctx.author.name}**', f'**Killua** asks **{ctx.author.name}** for motivation and gets a hug']
		embed = Embed.from_dict({
			'title': choice(hugtextself),
			'image':{
				'url': choice(huggif)
			},
			'color': 0x1400ff
			})
		await ctx.send(embed=embed)

@group(name='team', invoke_without_command=True)
async def team(ctx):
	pass


def main():
	# Create the bot instance.
	bot = commands.Bot(
		command_prefix=get_prefix,
		description="default prefix",
		case_insensitive=True
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

from . import cogs
import discord
from discord.ext import commands, ipc
import json
import aiohttp
from pymongo import MongoClient
from typing import Callable, Coroutine
from .help import MyHelp

with open('config.json', 'r') as config_file:
    config = json.loads(config_file.read())

cluster = MongoClient(config['mongodb'])
db = cluster['Killua']
collection = db['teams']
top = db['teampoints']
server = db['guilds']

class Bot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ipc = ipc.Server(self, secret_key=config["ipc"])

    async def on_ipc_error(self, endpoint, error):
        print(endpoint, "raised", error)

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

	# Setup cogs.
	for cog in cogs.all_cogs:
		bot.add_cog(cog.Cog(bot))

	# Start the bot.
	bot.load_extension("jishaku")
	bot.ipc.start()
	bot.run(config['token'])
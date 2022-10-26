import discord
from discord.ext import commands

import asyncio
from random import randint, choice
from discord.ext import commands # NOTE Ipc needed here
from datetime import date
from typing import Coroutine, Union, Dict

from .static.enums import Category
from .utils.interactions import Modal
from .static.constants import IPC_TOKEN, TIPS, LOOTBOXES, DB

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

class BaseBot(commands.Bot):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.support_server_invite = "https://discord.gg/MKyWA5M"
		self.invite = "https://discord.com/oauth2/authorize?client_id=756206646396452975&scope=bot&permissions=268723414&applications.commands"
		# self.ipc = ipc.Server(self, secret_key=IPC_TOKEN)
		self.is_dev = False

	async def setup_hook(self):
		await self.load_extension("jishaku")
		# await self.ipc.start()
		await self.tree.sync()

	async def close(self):
		await super().close()
		await self.session.close()

	def __format_command(self, res: Dict[str, list], cmd: commands.Command) -> dict:
		"""Adds a command to a dict of formatted commands"""
		if cmd.name in ["jishaku", "help"] or cmd.hidden:
			return res

		res[cmd.extras["category"].value["name"]]["commands"].append(cmd)
        
		return res

	def get_formatted_commands(self) -> dict:
		"""Gets a dictionary of formatted commands"""
		res = {c.value["name"]: {"description": c.value["description"], "emoji": c.value["emoji"], "commands": []} for c in Category}

		for cmd in self.commands:
			if isinstance(cmd, commands.Group) and cmd.name != "jishaku":
				for c in cmd.commands:
					res = self.__format_command(res, c)
				continue
			res = self.__format_command(res, cmd)

		return res

	async def find_user(self, ctx: commands.Context, user: str) -> Union[discord.Member, discord.User, None]:
		"""Attempts to create a member or user object from the passed string"""
		try:
			res = await commands.MemberConverter().convert(ctx, user)
		except commands.MemberNotFound:
			if not user.isdigit():
				return

			res = self.get_user(int(user))
			if not res:
				try:
					res = await self.fetch_user(int(user))
				except discord.NotFound:
					return
		return res

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
				ctx.invoked_by_modal = True # This is added so we can check inside of the command if it was invoked from a modal
				await ctx.invoke(command, text=message.content, *args, **kwargs)
		else:
			async def callback(interaction: discord.Interaction, member: discord.Member):
				ctx = await commands.Context.from_interaction(interaction)
				ctx.invoked_by_modal = True
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
			modal = Modal(ctx.author.id, title="Anser the question(s) and click submit", timeout=timeout)
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

			return textinput.value

		else:
			def check(m):
				return m.author.id == ctx.author.id

			msg = await ctx.send(text)
			try:
				confirmmsg = await self.wait_for('message', check=check, timeout=timeout)
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
		status = DB.presence.find_one({})
		if status['text']:
			if not status['activity']:
				status['activity'] = 'playing'

			s = discord.Activity(name=status['text'], type=getattr(discord.ActivityType, status['activity']))
				
			if not status['presence']:
				status['presence'] = 'online'

			return await self.change_presence(activity=s, status=getattr(discord.Status, status['presence']))

		a = date.today()
		#The day Killua was born!!
		b = date(2020,9,17)
		delta = a - b
		playing = discord.Activity(name=f'over {len(self.guilds)} guilds | k! | day {delta.days}', type=discord.ActivityType.watching)
		return await self.change_presence(status=discord.Status.online, activity=playing)

	async def send_message(self, messageable: discord.abc.Messageable, *args, **kwargs) -> discord.Message:
		"""A helper function sending messages and adding a tip with the probability of 5%"""
		msg = await messageable.send(*args, **kwargs)
		if randint(1, 100) < 6: # 5% probability to send a tip afterwards
			await messageable.send(f"**Tip:** {choice(TIPS).replace('<prefix>', get_prefix(self, messageable.message)[2]) if hasattr(messageable, 'message') else ('k!' if not self.is_dev else 'kil!')}", ephemeral=True)
		return msg

	def convert_to_timestamp(self, id: int, args: str = "f") -> str:
		"""Turns a discord snowflake into a discord timestamp string"""
		return f"<t:{int((id >> 22) / 1000) + 1420070400}:{args}>"
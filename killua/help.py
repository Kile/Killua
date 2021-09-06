import discord
import datetime
import asyncio
from discord.ext import commands
from .classes import Category, Button
from .paginator import Paginator, View, DefaultEmbed

class HelpPaginator(Paginator):
    """A normal paginator with a button that returns to the original help command"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.view.add_item(Button(label="Menu", style=discord.ButtonStyle.blurple, custom_id="1"))

    async def start(self):
        view = await self._start()

        if view.ignore:
            return
        
        await self.view.message.delete()
        await self.ctx.command.__call__(self.ctx)


class HelpEmbed(discord.Embed):
    def __init__(self, av:str, **kwargs):
        super().__init__(**kwargs)
        self.title = "Help menu"
        self.color = 0x1400ff
        self.set_thumbnail(url=av)
        self.timestamp = datetime.datetime.utcnow()


class Select(discord.ui.Select):
    """Creates a select menu to view the command groups"""
    def __init__(self, options, **kwargs):
        super().__init__( 
            min_values=1, 
            max_values=1, 
            options=options,
            **kwargs
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.value = int(interaction.data["values"][0])
        for opt in self.options:
            if opt.value == str(self.view.value):
                opt.default = True
        self.view.stop()

class MyHelp(commands.HelpCommand):
    def __init__(self):
        super().__init__(
            command_attrs={
                "help": "The help command for the bot",
                "extras": {"category": Category.OTHER},
                "aliases": ['commands']
            }
        )
        self.cache = None
    
    async def send(self, **kwargs):
        """a short cut to sending to get_destination"""
        return await self.get_destination().send(**kwargs)

    async def _send_group_help(self, group:int, prefix:str) -> None:
        k, v = [x for i, x in enumerate(self.cache.items()) if i == group][0]
        c = v["commands"]

        def make_embed(page, embed, pages):
            embed.title = "Commands from the group `"+ k + "`"
            data = pages[page-1]
            embed.description = f"Command: `{prefix}{(data['parent'] + ' ') if data['parent'] else ''}{data['name']}`\n\n{data['help']}\n\nUsage: ```html\n{prefix}{(data['parent'] + ' ') if data['parent'] else ''}{data['usage']}\n```"
            return embed

        await HelpPaginator(self.context, c, timeout=100, func=make_embed).start()

    async def send_bot_help(self, mapping):
        """triggers when a `<prefix>help` is called"""
        ctx = self.context
        prefix = ctx.bot.command_prefix(ctx.bot, ctx.message)[2]
        embed = HelpEmbed(str(ctx.me.avatar.url))
        if not self.cache:
            self.cache = ctx.bot.get_formatted_commands()

        for k, v in self.cache.items():
            embed.add_field(name=f"{v['emoji']['normal']} `{k}` ({len(v['commands'])} commands)", value=v['description'], inline=False)
        embed.add_field(name="** **", value="\nFor more info to a specific command, use ```css\nhelp <command_name>```", inline=False)
        view = View(user_id=ctx.author.id, timeout=None)
        view.add_item(Select([discord.SelectOption(label=k, value=str(i), emoji=v['emoji']['unicode']) for i, (k, v) in enumerate(self.cache.items())], placeholder="Select a command group"))

        view.add_item(discord.ui.Button(url=ctx.bot.support_server_invite, label="Support server"))
        view.add_item(discord.ui.Button(url="https://github.com/kile/killua", label="Source code"))
        view.add_item(discord.ui.Button(url="https://killua.dev", label="Website"))
        view.add_item(discord.ui.Button(url="https://patreon.com/kilealkuri", label="Premium"))
        msg = await self.send(embed=embed, view=view, reference=ctx.message, allowed_mentions=discord.AllowedMentions.none())

        try:
            await asyncio.wait_for(view.wait(), timeout=100)
        except asyncio.TimeoutError:
            await view.disable(msg)
        else:
            #await msg.edit(embed=msg.embeds[0], view=discord.ui.View())
            await msg.delete()
            return await self._send_group_help(view.value, prefix)

    async def send_command_help(self, command):
        """triggers when a `<prefix>help <command>` is called"""
        ctx = self.context
        if isinstance(command, commands.Group) or command.hidden or command.qualified_name.startswith("jishaku") or command.name == "help": # not showing what it's not supposed to. Hacky I know
            return await ctx.send(f"No command called \"{command.name}\" found.")

        prefix = ctx.bot.command_prefix(ctx.bot, ctx.message)[2]
        embed = DefaultEmbed(title="Infos about command " + prefix + command.qualified_name, description=command.help or "No help found...")

        embed.add_field(name="Category", value=command.extras["category"].value["name"])

        if command._buckets and (cooldown := command._buckets._cooldown): # use of internals to get the cooldown of the command
            embed.add_field(
                name="Cooldown",
                value=f"{cooldown.rate} per {cooldown.per:.0f} seconds",
                inline=False
            )
        usage = f"```css\n{prefix}{(command.parent.name + ' ') if command.parent else ''}{command.usage}\n```"
        embed.add_field(name="Usage", value=usage, inline=False)

        await self.send(embed=embed)

    async def send_help_embed(self, title, description, commands): # a helper function to add commands to an embed
        embed = CommandEmbed(title=title, description=description or "No help found...")

        if filtered_commands := await self.filter_commands(commands):
            for command in filtered_commands:
                embed.add_field(name=self.get_command_signature(command), value=command.help or "No help found...")
           
        await self.send(embed=embed)
import discord
import datetime
import contextlib
import asyncio
from discord.ext import commands
from .classes import Category, Guild
from .paginator import Paginator, View

class CommandEmbed(discord.Embed):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.color = 0x1400ff
        self.timestamp = datetime.datetime.utcnow()

class DefaultEmbed(discord.Embed):
    """The default embed to use if no embed is provided"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.color = 0x1400ff
        self.timestamp = datetime.datetime.utcnow()

class HelpEmbed(discord.Embed):
    def __init__(self, av:str, **kwargs):
        super().__init__(**kwargs)
        self.title = "Help menu"
        self.color = 0x1400ff
        self.set_thumbnail(url=av)
        self.timestamp = datetime.datetime.utcnow()


class Select(discord.ui.Select):
    """Creates a select menu to view the command groups"""
    def __init__(self, options:list):
        super().__init__(
            placeholder="Select a command group", 
            min_values=1, 
            max_values=1, 
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.value = int(interaction.data["values"][0])
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
        self.prefix = Guild(self.context.guild.id).prefix if (self.context.guild if self.context else None) else "k!"
        self.cache = None
    
    async def send(self, **kwargs):
        """a short cut to sending to get_destination"""
        return await self.get_destination().send(**kwargs)

    async def _send_group_help(self, group:int, commands:dict):
        key = [x for i, x in enumerate(commands.keys()) if i == group][0]
        c = commands[key]

        def make_embed(page, embed, pages):
            embed.title = "Commands from the group `"+key.value["name"] + "`"
            embed.description = pages[page-1]
            return embed

        await Paginator(self.context, c, timeout=100, func=make_embed, embed=CommandEmbed()).start()

    async def send_bot_help(self, mapping):
        """triggers when a `<prefix>help` is called"""
        ctx = self.context
        commands = {}
        embed = HelpEmbed(str(ctx.me.avatar.url))
        if self.cache:
            commands = self.cache
        else:
            for cmds in mapping.values(): #iterating through our mapping of commands
                for command in cmds:
                    if command.hidden or command.name == "jishaku":
                        continue
                    text = f"\nCommand: `{self.prefix}{command.name}`\n\n{command.help}\n\nUsage:```markdown\n{self.prefix}{command.usage}\n```"
                    if command.extras["category"] in commands:
                        commands[command.extras["category"]].append(text)  
                    else:
                        commands[command.extras["category"]] = [text]
            self.cache = commands

        for k, v in commands.items():
            embed.add_field(name=f"** **", value=f"{k.value['emoji']['normal']} `{k.value['name']}` ({len(v)} commands)\n{k.value['description']}", inline=False)
        embed.add_field(name="** **", value="\nFor more info to a specific command,, use ```css\nhelp <command_name>```\n[Support server](https://discord.gg/be4nvwq7rZ)\n[Source code](https://github.com/kile/killua)\n[Website](https://killua.dev)", inline=False)
        view = View(user_id=ctx.author.id, timeout=None)
        view.add_item(Select([discord.SelectOption(label=k.value['name'], value=str(i), emoji=k.value['emoji']['unicode']) for i, k in enumerate(commands.keys())]))
        msg = await self.send(embed=embed, view=view, reference=ctx.message, allowed_mentions=discord.AllowedMentions.none())

        try:
            await asyncio.wait_for(view.wait(), timeout=100)
        except asyncio.TimeoutError:
            await msg.edit(embed=msg.embeds[0], view=discord.ui.View())
        else:
            #await msg.edit(embed=msg.embeds[0], view=discord.ui.View())
            await msg.delete()
            return await self._send_group_help(view.value, commands)

    async def send_command_help(self, command):
        """triggers when a `<prefix>help <command>` is called"""
        embed = CommandEmbed(title="Infos about command " + self.prefix + command.name, description=command.help or "No help found...")

        embed.add_field(name="Category", value=command.extras["category"].value["name"])

        can_run = "No"
        # command.can_run to test if the cog is usable
        with contextlib.suppress(commands.CommandError):
            if await command.can_run(self.context):
                can_run = "Yes"
            
        embed.add_field(name="Usable", value=can_run, inline=False)

        if command._buckets and (cooldown := command._buckets._cooldown): # use of internals to get the cooldown of the command
            embed.add_field(
                name="Cooldown",
                value=f"{cooldown.rate} per {cooldown.per:.0f} seconds",
                inline=False
            )
        
        embed.add_field(name="Usage", value=f"```css\n{command.usage}\n```", inline=False)

        await self.send(embed=embed)

    async def send_help_embed(self, title, description, commands): # a helper function to add commands to an embed
        embed = CommandEmbed(title=title, description=description or "No help found...")

        if filtered_commands := await self.filter_commands(commands):
            for command in filtered_commands:
                embed.add_field(name=self.get_command_signature(command), value=command.help or "No help found...")
           
        await self.send(embed=embed)
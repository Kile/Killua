import discord, os
from typing import List, Union, cast
from discord.ext import commands
from datetime import datetime
from inspect import getsourcelines

from killua.bot import BaseBot
from killua.utils.classes import Guild
from killua.static.enums import Category
from killua.utils.paginator import Paginator
from killua.utils.interactions import Select, View, Button

class HelpPaginator(Paginator):
    """A normal paginator with a button that returns to the original help command"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.view.add_item(Button(label="Menu", style=discord.ButtonStyle.blurple, custom_id="1"))

    async def start(self):
        view = await self._start()

        if view.ignore or view.timed_out:
            return
        
        try:
            await self.view.message.delete()
        except discord.errors.Forbidden:
            pass 
        # Happens sometimes when invoked with a user installation.
        # Idk why but since that means the response is likely ephemeral,
        # we don't need to declutter the channel as badly. The command
        # failing would be worse.
        await self.ctx.command.__call__(self.ctx)


class HelpEmbed(discord.Embed):
    def __init__(self, av: str, **kwargs):
        super().__init__(**kwargs)
        self.title = "Help menu"
        self.color = 0x3e4a78
        self.set_thumbnail(url=av)
        self.timestamp = datetime.now()

class HelpCommand(commands.Cog):

    def __init__(self, client: BaseBot) -> None:
        self.client = client
        self.client.remove_command("help")
        self.cache = {}

    def find_source(self, command: commands.HybridCommand) -> str:
        """Finds the source of a command and links the GitHub link to it"""
        base_url = "https://github.com/kile/killua"
        branch = "master" if not self.client.is_dev else "v1.0"

        source = command.callback.__code__
        filename = source.co_filename

        lines, firstlineno = getsourcelines(source)
        location = os.path.relpath(filename).replace("\\", "/")

        return f"{base_url}/blob/{branch}/{location}#L{firstlineno}-L{firstlineno + len(lines) - 1}"

    def get_command_help(self, command: commands.HybridCommand, prefix: str) -> discord.Embed:
        """Gets the help embed for a command"""

        embed = discord.Embed(title="Infos about command `" + command.qualified_name + "`", description=command.help or "No help found...")
        embed.color = 0x3e4a78

        embed.add_field(name="Category", value=cast(Category, command.extras["category"]).value["name"])

        checks = command.checks

        premium_guild, premium_user, cooldown = False, False, False

        if [c for c in checks if hasattr(c, "premium_guild_only")]:
            premium_guild = True

        if [c for c in checks if hasattr(c, "premium_user_only")]:
            premium_user = True

        if (res := [c for c in checks if hasattr(c, "cooldown")]):
            check = res[0]
            cooldown = getattr(check, "cooldown", False)

        if premium_guild or premium_user:
            embed.description += f"\n{'<:premium_guild_badge:883473807292121149>' if premium_guild else '<:tier_one_badge:879390548857880597>'} `[Premium {'servers' if premium_guild else 'users'} only]`"

        if cooldown:
            embed.add_field(name="Cooldown", value=f"{cooldown} seconds")

        # Get the app command type parent of this command
        embed.add_field(
            name="User installable", 
            value=(
                "Yes" if 
                command.parent and 
                cast(commands.HybridCommand, command).app_command.parent.allowed_installs and
                cast(commands.HybridCommand, command).app_command.parent.allowed_installs.user
                else "No"
            )
        )

        # print(command, command.parent, command.qualified_name, type(command.parent), type(command.cog))
        usage_slash = "```css\n/" + command.qualified_name.replace(command.name, "") + command.usage + "\n```" if not isinstance(command.cog, commands.GroupCog) else f"```css\n/" + command.cog.__cog_group_name__ + " " + command.usage + "\n```"
        usage_message = f"```css\n{prefix}" + command.qualified_name.replace(command.name, "") + command.usage + "\n```" if not isinstance(command.cog, commands.GroupCog) else f"```css\n{prefix}" + command.usage + "\n```"
        embed.add_field(name="Usage", value="Slash:\n" + usage_slash + "\nMessage:\n" + usage_message, inline=False)

        if len(prefix) < 100: # We don't want large prefixes to break the embed and make the help command unusable
            embed.set_footer(text=f"Message prefix: {prefix}")

        return embed

    def get_group_help(self, ctx: commands.Context, group: Category, prefix: str) -> HelpPaginator:
        """Gets the help embed for a group"""

        c = self.cache[group.name.lower()]["commands"]

        def make_embed(page, embed, pages):
            embed = self.get_command_help(c[page-1], prefix)
            source = self.find_source(c[page-1])
            embed.description += f"\n[Source code]({source})"
            if len(prefix) < 100: # We don't want large prefixes to break the embed and make the help command unusable
                embed.set_footer(text=f"Page {page}/{len(pages)} | Message prefix: {prefix}")
            else:
                embed.set_footer(text=f"Page {page}/{len(pages)}")
            return embed

        return HelpPaginator(ctx, c, timeout=100, func=make_embed)
    
    async def handle_command(self, ctx: commands.Context, cmd: commands.Command, message_prefix: str):
        """Handles a command help"""

        if isinstance(cmd, commands.HybridGroup) or isinstance(cmd, discord.app_commands.ContextMenu) or cmd.hidden or cmd.qualified_name.startswith("jishaku") or cmd.name == "help": # not showing what it's not supposed to. Hacky I know
            return await ctx.send(f"No command called \"{cmd.name}\" found.", ephemeral=True)

        source_link = self.find_source(cmd)

        embed = self.get_command_help(cmd, message_prefix)

        source_view = View(user_id=ctx.author.id, timeout=None)
        source_view.add_item(discord.ui.Button(url=source_link, label="Source code", style=discord.ButtonStyle.link))

        return await ctx.send(embed=embed, view=source_view)
    
    def find_category(self, string: str) -> Union[Category, None]:
        for cat in Category:
            if cast(str, cat.value["name"]).lower() == string.lower():
                return cat
        return None

    async def help_autocomplete(
        self,
        _: discord.Interaction,
        current: str,
    ) -> List[discord.app_commands.Choice[str]]:
        """Autocomplete for all cards"""
        if not self.cache:
            self.cache = self.client.get_formatted_commands()

        all_commands = [v["commands"] for v in self.cache.values()]
        # combine all individual lists in all_commands into one in one line
        all_commands: List[commands.Command] = [item for sublist in all_commands for item in sublist]
        
        return [command.qualified_name for command in all_commands if current.lower() in command.qualified_name][0:25]

    @commands.hybrid_command(usage="help [group] [command]", extras={"id": 45})
    @discord.app_commands.describe(group="The group to get help for", command="The command to get help for")
    @discord.app_commands.autocomplete(command=help_autocomplete)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @discord.app_commands.allowed_installs(users=True, guilds=True)
    async def help(self, ctx: commands.Context, group: str = None, command: str = None) -> None:
        """Displays helfpul information about a command, group, or the bot itself."""
        message_prefix = Guild(ctx.guild.id).prefix if ctx.guild else "k!"

        if not self.cache:
            self.cache = self.client.get_formatted_commands()

        if not (group or command):
            embed = HelpEmbed(str(ctx.me.avatar.url))

            for k, v in self.cache.items():
                embed.add_field(name=f"{v['emoji']['normal']} `{k}` ({len(v['commands'])} commands)", value=v["description"], inline=False)

            embed.add_field(name="** **", value="\nFor more info to a specific command, use ```css\nhelp <command_name>```", inline=False)
            view = View(user_id=ctx.author.id, timeout=None)
            view.add_item(Select([discord.SelectOption(label=k, value=str(i), emoji=v["emoji"]["unicode"]) for i, (k, v) in enumerate(self.cache.items())], placeholder="Select a command group"))

            view.add_item(discord.ui.Button(url=self.client.support_server_invite, label="Support server"))
            view.add_item(discord.ui.Button(url="https://github.com/kile/killua", label="Source code"))
            view.add_item(discord.ui.Button(url="https://killua.dev", label="Website"))
            view.add_item(discord.ui.Button(url="https://patreon.com/kilealkuri", label="Premium"))

            msg = await ctx.send(embed=embed, view=view)

            
            await view.wait()
            if view.timed_out:
                view.children[0].disabled = True # Instead of looping through all the children, we just disable the select menu since we want the links to remain clickable
                return await msg.edit(view=view)
            else:
                #await msg.edit(embed=msg.embeds[0], view=discord.ui.View())
                await msg.delete()
                paginator = self.get_group_help(ctx, self.find_category(list(self.cache.keys())[view.value]), message_prefix)
                return await paginator.start()

        elif group and not command: # if group is specified, but not command
            # Check if the group exists
            if self.find_category(group):
                paginator = self.get_group_help(ctx, self.find_category(group), message_prefix)
                return await paginator.start()
            
            # If the group doesn't exist, check if the command exists
            all_commands = [v["commands"] for v in self.cache.values()]
            # combine all individual lists in all_commands into one in one line
            all_commands: List[commands.Command] = [item for sublist in all_commands for item in sublist]

            # if command not in [c.qualified_name for c in self.client.commands]:
            #     return await ctx.send(f"No command called \"{command}\" found.", ephemeral=True)
            if not group.lower() in [c.qualified_name for c in all_commands]:
                return await ctx.send(f"No command or group called \"{group}\" found.", ephemeral=True)

            cmd = next(c for c in all_commands if c.qualified_name == group.lower())
            return await self.handle_command(ctx, cmd, message_prefix)

        elif command: # If both command and group exist, command takes priority
            all_commands = [v["commands"] for v in self.cache.values()]
            # combine all individual lists in all_commands into one in one line
            all_commands: List[commands.Command] = [item for sublist in all_commands for item in sublist]

            # if command not in [c.qualified_name for c in self.client.commands]:
            #     return await ctx.send(f"No command called \"{command}\" found.", ephemeral=True)
            if not command.lower() in [c.qualified_name for c in all_commands]:
                return await ctx.send(f"No command called \"{command}\" found.", ephemeral=True)

            cmd = next(c for c in all_commands if c.qualified_name == command.lower())
            return await self.handle_command(ctx, cmd, message_prefix)

        elif group:
            if not self.find_category(group):
                return await ctx.send(f"No group called \"{group}\" found.", ephemeral=True)

            paginator = self.get_group_help(ctx, self.find_category(group), message_prefix)
            return await paginator.start()

Cog = HelpCommand
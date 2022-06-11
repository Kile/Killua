
import discord
from discord.ext import commands
from typing import Union, Type

from killua.static.constants import DB, PatreonBanner
from .classes import User, Guild

cooldowndict = {}

def _clean_command_name(command:Union[commands.Command, Type[commands.Command]]) -> str:
	"""returns the clean command name of a command"""
	if not command.parent:
		return command.name
	else:
		name = ""
		c = command
		while c.parent:
			name = c.parent.qualified_name + " " + name
			c = c.parent
		return name + command.name

def blcheck(userid:int): # It is necessary to define it twice as I might have to use this function on its own
    """
    Input:
        userid (int): The id of the user who should be checked

    Returns:
        (boolean): if the user is blacklisted or not

    Purpose:
        Checking before everry command if the user is blacklisted
    """
    result = DB.blacklist.find_one({"id": userid})

    if result is None:
        return False
    else:
        return True

def premium_guild_only():

    async def predicate(ctx: commands.Context) -> bool:

        if not Guild(ctx.guild.id).is_premium:
            view = discord.ui.View()
            view.add_item(discord.ui.Button(style=discord.ButtonStyle.grey, label="Premium", url="https://patreon.com/kilealkuri"))
            await ctx.send("This command group is currently only a premium feature. To enable your guild to use it, become a Patreon!", file=PatreonBanner.file(), view=view)
            return False
        return True

    return commands.check(predicate)

def premium_member_only():

    async def predicate(ctx: commands.Context) -> bool:
            
            if not User(ctx.author.id).is_premium:
                view = discord.ui.View()
                view.add_item(discord.ui.Button(style=discord.ButtonStyle.grey, label="Premium", url="https://patreon.com/kilealkuri"))
                await ctx.send("This command is currently only a premium feature. To enable your account to use it, become a Patreon!", file=PatreonBanner.file(), view=view)
                return False
            return True

    return commands.check(predicate)

def check(time: int = 0):
    """
    A check that checks for blacklists, dashboard configuration and cooldown in that order
    """
    
    from datetime import datetime
    from killua.static.constants import DB

    def add_usage(command:Union[commands.Command, Type[commands.Command]]) -> None:
        data = DB.stats.find_one({"_id": "commands"})["command_usage"]
        command = _clean_command_name(command)
        data[command] = data[command]+1 if command in data else 1
        DB.stats.update_one({"_id": "commands"}, {"$set": {"command_usage": data}})

    def blcheck(userid: int) -> bool:
        """
        Input:
            userid (int): The id of the user who should be checked

        Returns:
            (boolean): if the user is blacklisted or not

        Purpose:
            Checking before every command if the user is blacklisted
        """

        result = DB.blacklist.find_one({"id": userid})

        if result is None:
            return False
        else:
            return True
    
    async def custom_cooldown(ctx: commands.Context, time:int) -> bool:
        global cooldowndict
        now = datetime.now()
        try:
            cdwn = cooldowndict[ctx.author.id][ctx.command.name]
        except KeyError as e: # if there is no entry in the cooldowndict yet for either the command or user
            error = e.args[0]
            if error == ctx.author.id:
                cooldowndict = {ctx.author.id: {ctx.command.name: now}}
                return True
            if error == ctx.command.name:
                cooldowndict[ctx.author.id][ctx.command.name] = now
                return True

        cd = now-cdwn 
        diff = cd.seconds
        
        user = User(ctx.author.id)
        guild = Guild(ctx.guild.id) if ctx.guild else None
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Get premium", url="https://patreon.com/kilealkuri", style=discord.ButtonStyle.blurple)) # sadly I cannot color a link button :c

        if guild and guild.is_premium:
            time /= 2

        if user.is_premium:
            time /= 2

        if diff > time:
            cooldowndict[ctx.author.id][ctx.command.name] = now
            return True 
                    
        await ctx.send(f":x: Command on cooldown! Try again  after `{time-diff}` seconds\n\nHalf your cooldown by clicking on the button and becoming a Patreon",file=PatreonBanner.file(), view=view, delete_after=10)
        return False

    async def settings_check(ctx: commands.Context) -> bool:
        if not ctx.guild:
            return True

        guild = Guild(ctx.guild.id)
            
        if not ctx.command.name in guild.commands:
            return True

        command = guild.commands[ctx.command.name]

        # Checking if a command is disabled
        if command["enabled"] is False:
            return False

        # Checking if the member is whitelisted (not implemented)
        #if ctx.author.id in [int(x) for x in command["restricted_to_members"] if len(command["restricted_to_members"]) > 0]:
            #return True

        # Checking if the member is blacklisted (not implemented)
        #if ctx.author.id in [int(x) for x in command["blacklisted_members"] if len(command["blacklisted_members"]) > 0]:
            #return False

        # Checking if the channel is blacklisted
        if ctx.channel.id in [int(x) for x in command["blacklisted_channels"]]:
            return False

        # Checking if the channel is whitelisted if it is only whitelisted to a few channels
        if not ctx.channel.id in command["restricted_to_channels"]:
            return False

        # Checking if the user has a role the command is restricted to
        if not len([i for i, j in zip([x.id for x in ctx.author.roles], [int(x) for x in command["restricted_to_roles"]]) if i == j]) > 0 and len(command["restricted_to_roles"]) > 0:
            return False

        # Checking if a role a user has is blacklisted
        if len([i for i, j in zip([x.id for x in ctx.author.roles], [int(x) for x in command["blacklisted_roles"]]) if i == j]) > 0:
            return False

        # Checking if the command invokation should be deleted
        if "delete_invokation" in command and command["delete_invokation"]:
            try:
                await ctx.message.delete()
            except discord.HTTPException: # if it is already deleted for some reason
                pass

        return True

    async def predicate(ctx: commands.Context) -> bool:
        if blcheck(ctx.author.id):
            return False

        try:
            if (await settings_check(ctx)) is False:
                return False
        except Exception: #If someone used the api and messed up the guilds data structure
            pass

        if time == 0:
            add_usage(ctx.command)
            return True

        if await custom_cooldown(ctx, time) is False:
            return False

        add_usage(ctx.command)

        return True

    return commands.check(predicate)
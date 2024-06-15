
import discord
from discord.ext import commands
from typing import Union, Type
from datetime import datetime, timedelta

from killua.static.constants import DB, PatreonBanner, daily_users
from .classes import User, Guild

cooldowndict = {}

class CommandUsageCache:
    data = dict(DB.const.find_one({"_id": "usage"})["command_usage"])

    """
    A class to cache command usage
    """
    def __init__(self):
        ...

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value
        DB.const.update_one({"_id": "usage"}, {"$set": {"command_usage": self.data}})

    def __contains__(self, key):
        return key in self.data
    
    def get(self, key, default):
        return self.data.get(key, default)

def blcheck(userid:int): # It is necessary to define it twice as I might have to use this function on its own
    """
    Checks if a user is blacklisted
    """
    result = [d for d in DB.const.find_one({"_id": "blacklist"})["blacklist"] if d["id"] == userid]

    if not result:
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

    setattr(predicate, "premium_guild_only", True)

    return commands.check(predicate)

def premium_user_only():

    async def predicate(ctx: commands.Context) -> bool:
            
            if not User(ctx.author.id).is_premium:
                view = discord.ui.View()
                view.add_item(discord.ui.Button(style=discord.ButtonStyle.grey, label="Premium", url="https://patreon.com/kilealkuri"))
                await ctx.send("This command is currently only a premium feature. To enable your account to use it, become a Patreon!", file=PatreonBanner.file(), view=view)
                return False
            return True

    setattr(predicate, "premium_user_only", True)

    return commands.check(predicate)

def check(time: int = 0):
    """
    A check that checks for blacklists, dashboard configuration and cooldown in that order
    """

    def add_daily_user(userid: int):
        """
        Adds a user who has run a command to the daily_users list if they are not already in it
        """
        if userid not in daily_users.users:
            daily_users.users.append(userid)

    def add_usage(command: Union[commands.Command, Type[commands.Command]]) -> None:
        """Adds one to the usage count of a command"""
        if isinstance(command, commands.HybridGroup) or isinstance(command, discord.app_commands.Group):
            return

        data = CommandUsageCache()
        data[str(command.extras["id"])] = (
            data[str(command.extras["id"])]+1 
            if str(command.extras["id"]) in data 
            else 1
        )
    
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

        cd: timedelta = now-cdwn 
        diff = cd.seconds
        
        user = User(ctx.author.id)
        guild = Guild(ctx.guild.id) if ctx.guild else None
        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="Get premium", 
                url="https://patreon.com/kilealkuri", 
                style=discord.ButtonStyle.blurple
            )
        ) # sadly I cannot color a link button :c

        if guild and guild.is_premium:
            time /= 2

        if user.is_premium:
            time /= 2

        if diff > time:
            cooldowndict[ctx.author.id][ctx.command.name] = now
            return True 

        timestamp = f"<t:{int((now + timedelta(seconds=time)).timestamp())}:R>"
        
        embed = discord.Embed(
            title="Cooldown", 
            description=f":x: Command on cooldown! Try again {timestamp}\n\nHalf your cooldown by clicking on the button and becoming a Patreon", 
            color=discord.Color.red()
        )
        embed.set_image(url=PatreonBanner.URL)
        await ctx.send(embed=embed, view=view, delete_after=10)
        # The one below currently does not work because imgur does not
        # not like my server's IP so I cannot download the banner.
        # await ctx.send(f":x: Command on cooldown! Try again  after `{time-diff}` seconds\n\nHalf your cooldown by clicking on the button and becoming a Patreon",file=PatreonBanner.file(), view=view, delete_after=10)
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
        if ctx.guild and not ctx.guild.chunked:
            await ctx.guild.chunk()
            
        if blcheck(ctx.author.id):
            return False

        try:
            if (await settings_check(ctx)) is False:
                return False
        except Exception: #If someone used the api and messed up the guilds data structure
            pass

        if time > 0 and await custom_cooldown(ctx, time) is False:
            return False

        add_usage(ctx.command)
        add_daily_user(ctx.author.id)

        return True

    predicate.cooldown = time

    return commands.check(predicate)
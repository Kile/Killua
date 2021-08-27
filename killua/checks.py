import discord
from discord.ext import commands
from typing import Union, Type
from .constants import blacklist

cooldowndict = {}

def _clean_command_name(command:Union[commands.Command, Type[commands.Command]]) -> str:
	"""returns the clean command make of a command"""
	if not command.parent:
		return command.name
	else:
		name = ""
		c = command
		while c.parent:
			name = c.parent.qualified_name + " " + name
			c = c.parent
		else:
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
    result = blacklist.find_one({'id': userid})

    if result is None:
        return False
    else:
        return True

def check(time:int=0):
    """
    A check that checks for blacklists, dashboard configuration and cooldown in that order
    """
    
    from datetime import datetime, timedelta
    from killua.constants import guilds, teams, blacklist, stats

    def add_usage(command:Union[commands.Command, Type[commands.Command]]) -> None:
        data = stats.find_one({'_id': 'commands'})['command_usage']
        command = _clean_command_name(command)
        data[command] = data[command]+1 if command in data else 1
        stats.update_one({'_id': 'commands'}, {'$set': {'command_usage': data}})

    def blcheck(userid:int) -> bool:
        """
        Input:
            userid (int): The id of the user who should be checked

        Returns:
            (boolean): if the user is blacklisted or not

        Purpose:
            Checking before everry command if the user is blacklisted
        """

        result = blacklist.find_one({'id': userid})

        if result is None:
            return False
        else:
            return True
    
    async def custom_cooldown(ctx, time:int) -> bool:
        global cooldowndict
        now = datetime.today()
        later = datetime.now()+timedelta(seconds=time)
        try:
            cdwn = cooldowndict[ctx.author.id][ctx.command.name]
        except KeyError as e:
            error = e.args[0]
            if error == ctx.author.id:
                cooldowndict = {ctx.author.id: {ctx.command.name: later}}
                return True
            if error == ctx.command.name:
                cooldowndict[ctx.author.id][ctx.command.name] = later
                return True

        cd = cdwn-now 

        if str(cdwn) < str(now):
            cooldowndict[ctx.author.id][ctx.command.name] = later
            return True 

        else:
            user = teams.find_one({'id': ctx.author.id})
            guild = guilds.find_one({'id': ctx.guild.id}) if ctx.guild else None

            if cd.seconds < time:
                t = -1*(6-time-cd.seconds)
                if guild is None:
                    pass
                elif 'partner' in guild['badges'] or 'premium' in guild['badges']:
                    if int(cd.seconds) > time/2:
                        t = t/2
                    else:
                        cooldowndict[ctx.author.id][ctx.command.name] = later
                        return True

                if user is None:
                    await ctx.send(f':x: Command on cooldown! Try again after `{t}` seconds\n\nHalf your cooldown by becoming a patreon here: https://patreon.com/kilealkuri', delete_after=5)
                    return False

                if 'premium' in user['badges']:
                    if int(cd.seconds) > t/2:
                        await ctx.send(f':x: Command on cooldown! Try again after `{t/2}` seconds\n\nHalf your cooldown by becoming a patreon here: https://patreon.com/kilealkuri', delete_after=5)
                        return False
                    else:
                        cooldowndict[ctx.author.id][ctx.command.name] = later
                        return True
                    
                await ctx.send(f':x: Command on cooldown! Try again after `{t}` seconds\n\nHalf your cooldown by becoming a patreon here: https://patreon.com/kilealkuri', delete_after=5)
                return False
            return True

    async def settings_check(ctx) -> bool:

        guild = guilds.find_one({'id': ctx.guild.id})

        if not 'commands' in guild:
            return True
            
        if not ctx.command.name in guild['commands']:
            return True

        command = guild['commands'][ctx.command.name]

        # Checking if a command is disabled
        if command['enabled'] is False:
            return False

        # Checking if the member is whitelisted (not implemeted)
        #if ctx.author.id in [int(x) for x in command['restricted_to_members'] if len(command['restricted_to_members']) > 0]:
            #return True

        # Checking if the member is blacklisted (not implemented)
        #if ctx.author.id in [int(x) for x in command['blacklisted_members'] if len(command['blacklisted_members']) > 0]:
            #return False

        # Checking if the channel is blacklisted
        if ctx.channel.id in [int(x) for x in command['blacklisted_channels']]:
            return False

        # Checking if the channel is whitelisted if it is only whitelisted to a few channels
        if not ctx.channel.id in command['restricted_to_channels'] and len(command['restricted_to_channels']) > 0:
            return False

        # Checking if the user has a role the command is restricted to
        if not len([i for i, j in zip([x.id for x in ctx.author.roles], [int(x) for x in command['restricted_to_roles']]) if i == j]) > 0 and len(command['restricted_to_roles']) > 0:
            return False

        # Checking if a role a user has is blacklisted
        if len([i for i, j in zip([x.id for x in ctx.author.roles], [int(x) for x in command['blacklisted_roles']]) if i == j]) > 0:
            return False

        # Checking if the command invokation should be deleted
        if command['delete_invokation']:
            await ctx.message.delete() # This could break stuff, fixing later

        return True

    async def predicate(ctx):
        if blcheck(ctx.author.id):
            return False

        try:
            if (await settings_check(ctx)) is False:
                return False
        except Exception: #If someone used the api and messed up the guilds data struture
            pass

        if time == 0:
            add_usage(ctx.command)
            return True

        if await custom_cooldown(ctx, time) is False:
            return False

        add_usage(ctx.command)

        return True

    return commands.check(predicate)
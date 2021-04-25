import discord
from discord.ext import commands

'''function blcheck
Input:
userid (int): The id of the user who should be checked

Returns:
(boolean): if the user is blacklisted or not

Purpose:
Checking before everry command if the user is blacklisted
'''   

def blcheck(userid:int):
    from pymongo import MongoClient
    import json

    with open('config.json', 'r') as config_file:
	    config = json.loads(config_file.read())

    c = MongoClient(config['mongodb'])
    gdb = c['general']
    bl = gdb['blacklist']
    result = bl.find_one({'id': userid})

    if result is None:
        return False
    else:
        return True

cooldowndic = {}

def custom_cooldown(time:int):
    async def predicate(ctx):
        global cooldowndic
        from pymongo import MongoClient
        import json
        from datetime import datetime, timedelta

        with open('config.json', 'r') as config_file:
	        config = json.loads(config_file.read())

        c = MongoClient(config['mongodb'])
        db = c['killua']
        t = db['teams']
        g = db['guilds']

        now = datetime.today()
        later = datetime.now()+timedelta(seconds=time)
        try:
            cdwn = cooldowndic[ctx.author.id][ctx.command.name]
        except KeyError as e:
            error = e.args[0]
            if error == ctx.author.id:
                cooldowndic = {ctx.author.id: {ctx.command.name: later}}
                return True
            if error == ctx.command.name:
                cooldowndic[ctx.author.id][ctx.command.name] = later
                return True

        cd = cdwn-now 

        if str(cdwn) < str(now):
            cooldowndic[ctx.author.id][ctx.command.name] = later
            return True 

        else:
            user = t.find_one({'id': ctx.author.id})
            guild = g.find_one({'id': ctx.guild.id})

            if cd.seconds < time:
                t = -1*(6-time-cd.seconds)
                if guild is None:
                    pass
                elif 'partner' in guild['badges'] or 'premium' in guild['badges']:
                    if int(cd.seconds) > time/2:
                        await ctx.send(f':x: Command on cooldown! Try again after `{t/2}` seconds', delete_after=5)
                        return False
                    else:
                        cooldowndic[ctx.author.id][ctx.command.name] = later
                        return True

                if user is None:
                    await ctx.send(f':x: Command on cooldown! Try again after `{t/2}` seconds', delete_after=5)
                    return False
                if 'supporter' in user['badges']:
                    if int(cd.seconds) > time/2:
                        await ctx.send(f':x: Command on cooldown! Try again after `{t/2}` seconds', delete_after=5)
                        return False
                    else:
                        cooldowndic[ctx.author.id][ctx.command.name] = later
                        return True
                
                await ctx.send(f':x: Command on cooldown! Try again after `{t}` seconds', delete_after=5)
                return False
            return True
      
    return commands.check(predicate)

'''async function p
Input:
self: taking in self because it is outside of a function

Returns:
Nothing

Purpose:
Changing Killuas presence freqently if he is added to a guild, removed or 12 hour pass, now also customisable by me at will
'''   

async def p(self):
    from pymongo import MongoClient
    import json
    from datetime import datetime, timedelta, date


    with open('config.json', 'r') as config_file:
	    config = json.loads(config_file.read())

    c = MongoClient(config['mongodb'])
    db = c['general']
    pr = db['presence']

    status = pr.find_one({})
    if status['text']:
        if not status['activity']:
            status['activity'] = 'playing'
        if status['activity'] == 'playing':
            s = discord.Activity(name=status['text'], type=discord.ActivityType.playing)
        if status['activity'] == 'watching':
            s = discord.Activity(name=status['text'], type=discord.ActivityType.watching)
        if status['activity'] == 'listening':
            s = discord.Activity(name=status['text'], type=discord.ActivityType.listening)
        if status['activity'] == 'competing':
            s = discord.Activity(name=status['text'], type=discord.ActivityType.competing)

            
        if not status['presence']:
            status['presence'] = 'online'
        if status['presence'] == 'online':
            return await self.client.change_presence(status=discord.Status.online, activity=s)
        if status['presence'] == 'dnd':
            return await self.client.change_presence(status=discord.Status.dnd, activity=s)
        if status['presence'] == 'idle':
            return await self.client.change_presence(status=discord.Status.idle, activity=s)
    a = date.today()
    #The day Killua was born!!
    b = date(2020,9,17)
    delta = a - b
    playing = discord.Activity(name=f'over {len(self.client.guilds)} guilds | k! | day {delta.days}', type=discord.ActivityType.watching)
    return await self.client.change_presence(status=discord.Status.online, activity=playing)

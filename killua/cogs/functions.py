import discord
from discord.ext import commands


def blcheck(userid:int):
    import pymongo
    from pymongo import MongoClient
    import json
    from json import loads

    with open('config.json', 'r') as config_file:
	    config = json.loads(config_file.read())

    c = MongoClient(json['mongodb'])
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
        import pymongo
        from pymongo import MongoClient
        import json
        from json import loads
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
            cdwn = cooldowndic[ctx.author.id]
        except KeyError:
            cooldowndic[ctx.author.id] = later
            return True

        cd = cdwn-now 

        if str(cdwn) < str(now):
            cooldowndic[ctx.author.id] = later
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
                        cooldowndic[ctx.author.id] = later
                        return True

                if user is None:
                    await ctx.send(f':x: Command on cooldown! Try again after `{t/2}` seconds', delete_after=5)
                    return False
                if 'supporter' in user['badges']:
                    if int(cd.seconds) > time/2:
                        await ctx.send(f':x: Command on cooldown! Try again after `{t/2}` seconds', delete_after=5)
                        return False
                    else:
                        cooldowndic[ctx.author.id] = later
                        return True
                
                await ctx.send(f':x: Command on cooldown! Try again after `{t}` seconds', delete_after=5)
                return False
      
    return commands.check(predicate)
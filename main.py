from discord.ext import commands
import time
import discord
import random
import json
import pymongo
from random import randint
from datetime import datetime
from discord.ext import tasks
import pymongo
from pymongo import MongoClient
from datetime import datetime
from datetime import datetime, timedelta
from pprint import pprint
import asyncio
import inspect
from datetime import date
from discord.utils import find
from discord import client
from PIL import Image, ImageDraw, ImageFilter, ImageFont




cluster = MongoClient('mongodb+srv://Kile:Kile2-#2@cluster0.q9qss.mongodb.net/teams?retryWrites=true&w=majority')
db = cluster['Killua']
collection = db['teams']
top =db['teampoints']
server = db['guilds']



def get_prefix(bot, message):
    y = server.find({'id': message.guild.id})
    if y.len != 0:
        prefix = y[0]['prefix']
        return prefix
    else:
        return '!k'
    
    

bot = commands.Bot(command_prefix= get_prefix, description="default prefix", case_insensitive=True)
bot.remove_command('help')


huggif = [f'https://i.pinimg.com/originals/66/9b/67/669b67ae57452f7afbbe5252b6230f85.gif', f'https://i.pinimg.com/originals/70/83/0d/70830dfba718d62e7af95e74955867ac.jpg', 'https://cdn.discordapp.com/attachments/756945125568938045/756945463432839168/image0.gif', 'https://cdn.discordapp.com/attachments/756945125568938045/756945308381872168/image0.gif', 'https://cdn.discordapp.com/attachments/756945125568938045/756945151191941251/image0.gif', 'https://pbs.twimg.com/media/Dl4PPE4UUAAsb7c.jpg', 'https://encrypted-tbn0.gstatic.com/images?q=tbn%3AANd9GcSJgTjRyQW3NzmDzlvskIS7GMjlFpyS7yt_SQ&usqp=CAU', 'https://static.zerochan.net/Hunter.x.Hunter.full.1426317.jpg', 'https://encrypted-tbn0.gstatic.com/images?q=tbn%3AANd9GcQJjVWplBdqrasz8Fh-7nDkxRjnnNBqk0bZlQ&usqp=CAU', 'https://i.pinimg.com/originals/75/2e/0a/752e0a5f813400dfebe322fc8b0ad0ae.jpg', 'https://thumbs.gfycat.com/IllfatedComfortableAplomadofalcon-small.gif', 'https://steamuserimages-a.akamaihd.net/ugc/492403625757327002/9B089509DDCB6D9F8E11446C7F1BC29B9BA57384/', f'https://cdn.discordapp.com/attachments/756945125568938045/758235270524698634/image0.gif', f'https://cdn.discordapp.com/attachments/756945125568938045/758236571974762547/image0.jpg', 'https://cdn.discordapp.com/attachments/756945125568938045/758236721216749638/image0.jpg', 'https://cdn.discordapp.com/attachments/756945125568938045/758237072975855626/image0.jpg', 'https://cdn.discordapp.com/attachments/756945125568938045/758237082484473856/image0.jpg', 'https://cdn.discordapp.com/attachments/756945125568938045/758237352756903936/image0.png', 'https://cdn.discordapp.com/attachments/756945125568938045/758237832954249216/image0.jpg']
topics = ['What\'s your favorite animal?', 'What is your favorite TV show?', 'If you could go anywhere in the world, where would you go?', 'What did you used to do, stopped and wish you hadn\'t?', 'What was the best day in your life?', 'For what person are you the most thankful for?', 'What is and has always been your least favorite subject?', 'What always makes you laugh and/or smile when you think about it?', 'Do you think there are aliens?', 'What is your earliest memory?', 'What\'s your favorite drink?', 'Where do you like going most for vacation?']


@bot.event
async def on_ready():
    print('------')
    print('Logged in as: ' + bot.user.name + f" (ID: {bot.user.id})")
    print('------')
    bot.startup_datetime = datetime.now()
        
        
@bot.event
async def on_guild_join(guild):
    
    general = find(lambda x: x.name == 'general',  guild.text_channels)
    if general and general.permissions_for(guild.me).send_messages:
        await general.send('Hello {}!'.format(guild.name))

    try:
        print('Please work')
        results = server.find({'id': guild.id})
        for result in results:
            t = result['points']
        print(t)     
    except Exception as e:
        server.update_many({'id': guild.id},{'$set':{'points': 0,'items': '','badges': '', 'prefix': 'k!'}}, upsert=True)



@bot.command(aliases = ['pref'])
async def prefix(ctx, prefix=None):
    results = server.find({'id': ctx.guild.id})
    for result in results:
            pref = result['prefix']
    if prefix:
        if ctx.author.guild_permissions.administrator:

            server.update_many({'id': ctx.guild.id},{'$set':{'prefix': str(pref)}}, upsert=True)

            await ctx.send(f'Changed server prefix to `{prefix}`')

        else: 
            await ctx.send('Missing permissions')
    else:
        await ctx.send(f'The current server prefix is `{pref}`')
        
@bot.event
async def on_message(message):
    if message.content == 'k!default pref' and message.author.guild_permissions.administrator:
        server.update_many({'id': message.guild.id},{'$set':{'prefix': 'k!'}}, upsert=True)

        await message.channel.send('Set prefix to default `k!`')
    await bot.process_commands(message)
            
        
        
@bot.command()
async def ping(ctx):
    start = time.time()
    msg = await ctx.send('Pong!')
    end = time.time()
    await msg.edit(content = str('Pong in `' + str(1000 * (end - start))) + '` ms')
    

@bot.command(name='topic')
async def topic(ctx):
    await ctx.send(random.choice(topics))

    
@bot.command()
async def hi(ctx):
    await ctx.send("Hello " + str(ctx.author)) 
    
@bot.command(aliases=['patreon'])
async def support(ctx):

    embed = discord.Embed.from_dict({
        'title': '**Support Killua**',
        'thumbnail':{
            'url': 'https://cdn.discordapp.com/avatars/758031913788375090/e44c0de4678c544e051be22e74bc502d.png?size=1024'},
        'description': 'Hey, do you have too much money? I have a solution for that! I now have a Patreon account where you can donate to support me and get special stuff, helping with building Killua. Not that I expect anyone to do this, but I have it set up now.\n\n https://www.patreon.com/KileAlkuri',
        'color': 0x1400ff
    })
    await ctx.send(embed=embed)


@bot.command(aliases=['c'])
async def commands(ctx):

    embed = discord.Embed.from_dict({
        'title': '**Bot commands**',
        'description': 'Prefix: `k!`\n\n `hi` makes Killua say hi to you \n\n `hug <@someone>` gives someone a Killua hug\n\n `info` displays info about the bot\n\n`invite` gives you the ability to invite Killua to your own server\n\n`ping` checks how fast Killua responds\n\n`topic` Killua gives you a random topic to talk about\n\n`patreon` gives you my Patreon account in case you want to support me and give me motivation :)\n\n If you have suggestions or bugs to report or unanswered questions, join the support server: https://discord.gg/zXqDHkm',
        'color': 0x1400ff 
    })
        
    await ctx.author.send(embed=embed)
    await ctx.send('Check your dms ;)')

@bot.command()
async def info(ctx):
    embed = discord.Embed(
        title = 'Info',
        description = ' This is Killua, Kile\'s bot version 0.2.2, the first features simply include ~this command, `k!ping`, `k!hi`, `k!invite`, `k!hug <user>` and `k!topic`, relatively self-explanatory, also a team mode already implemented but not yet finsihed\n I hope to be adding a lot more soon while I figure Python out on the go\n\n **Last time restarted:**\n '+ str(bot.startup_datetime.strftime('%Y-%m-%d-%H:%M:%S')),
        color = 0x1400ff
    )
    await ctx.send(embed=embed) 

@bot.command()
async def daily(ctx):
    now = datetime.today().strftime('%Y-%m-%d-%H:%M:%S')
    results = collection.find({'id': ctx.author.id})
    for result in results:
        nexttime = result['cooldowndaily']
        balance = result['points']
        team = result['team']
    results = top.find({'team': team})
    for result in results:
        points = result['points']
    if str(nexttime) < str(now):
        later = (datetime.now() + timedelta(hours=24)).strftime('%Y-%m-%d-%H:%M:%S')
        daily = randint(50, 100)
        collection.update_many({'id': ctx.author.id},{'$set':{'cooldowndaily':later, 'points': balance + daily}}, upsert=True)
        top.update_one({'team': team}, {'$set':{'points': points + daily}})
        await ctx.send(f'You claimed your {daily} daily points and hold now on to {int(balance) + int(daily)}')
    else:
        await ctx.send(f'You can claim your points the next time: {nexttime}')
    

@bot.command()
async def invite(ctx):
    embed = discord.Embed(
        title = 'Invite',
        description = 'Invite the bot to your server **today** [here](https://discord.com/oauth2/authorize?client_id=756206646396452975&scope=bot&permissions=1342531648)',
        color = 0x1400ff
    )
    await ctx.send(embed=embed) 

@bot.command()
async def guilds(ctx):
    if ctx.author.id == 606162661184372736 or ctx.author.id == 383790610727043085:
        embed = discord.Embed(
            title = 'Guilds',
            description = '\n'.join([guild.name for guild in bot.guilds]),
            color = 0x1400ff
        )
        await ctx.send(embed=embed) 

@bot.command()
async def hug(ctx,  *, content=None):
    if ctx.message.mentions:
        if ctx.author == ctx.message.mentions[0]:
            return await ctx.send(f'Someone hug {ctx.author.name}!')
        
        hugtext = [f'**{ctx.author.name}** hugs **{ctx.message.mentions[0].name}** as strong as they can', f'**{ctx.author.name}** hugs **{ctx.message.mentions[0].name}** and makes sure to not let go', f'**{ctx.author.name}** gives **{ctx.message.mentions[0].name}** the longest hug they have ever seen', f'**{ctx.author.name}** cuddles **{ctx.message.mentions[0].name}**', f'**{ctx.author.name}** uses **{ctx.message.mentions[0].name}** as a teddybear', f'**{ctx.author.name}** hugs **{ctx.message.mentions[0].name}** until all their worries are gone and 5 minutes longer',f'**{ctx.author.name}** clones themself and together they hug **{ctx.message.mentions[0].name}**', f'**{ctx.author.name}** jumps in **{ctx.message.mentions[0].name}**\'s arms', f'**{ctx.author.name}** gives **{ctx.message.mentions[0].name}** a bearhug', f'**{ctx.author.name}** finds a lamp with a Jinn and gets a wish. So they wish to hug **{ctx.message.mentions[0].name}**', f'**{ctx.author.name}** asks **{ctx.message.mentions[0].name}** for motivation and gets a hug']
        embed = discord.Embed.from_dict({
            'title': random.choice(hugtext),
            'image':{
                'url': random.choice(huggif)
            },
            'color': 0x1400ff
            })
        await ctx.send(embed=embed)
    else:
        await ctx.send('Invalid user.. Should- I hug you?')
        def check(m):
            return m.content.lower() == 'yes' and m.author == ctx.author

        msg = await bot.wait_for('message', check=check, timeout=60) 
        hugtextself = [f'**Killua** hugs **{ctx.author.name}** as strong as they can', f'**Killua** hugs **{ctx.author.name}** and makes sure to not let go', f'**Killua** gives **{ctx.author.name}** the longest hug they have ever seen', f'**Killua** cuddles **{ctx.author.name}**', f'**Killua** uses **{ctx.author.name}** as a teddybear', f'**Killua** hugs **{ctx.author.name}** until all their worries are gone and 5 minutes longer',f'**Killua** clones themself and together they hug **{ctx.author.name}**', f'**Killua** jumps in **{ctx.author.name}**\'s arms', f'**Killua** gives **{ctx.author.name}** a bearhug', f'**Killua** finds a lamp with a Jinn and gets a wish. So they wish to hug **{ctx.author.name}**', f'**Killua** asks **{ctx.author.name}** for motivation and gets a hug']
        embed = discord.Embed.from_dict({
            'title': random.choice(hugtextself),
            'image':{
                'url': random.choice(huggif)
            },
            'color': 0x1400ff
            })
        await ctx.send(embed=embed) 

@bot.event
async def on_connect():
    await p()
    days.start()
    
@bot.event
async def on_guild_join(guild):
    await p()

@bot.event
async def on_guild_remove(guild):
    await p()
    
@tasks.loop(hours=1)
async def days():
   await  p()


async def p():
    a = date.today()
    b = date(2020,9,17)
    delta = a - b
    playing = discord.Activity(name=f'over {len(bot.guilds)} guilds | day {delta.days}', type=discord.ActivityType.watching)
    await bot.change_presence(status=discord.Status.online, activity=playing)

@bot.group(name='team', invoke_without_command=True)
async def team(ctx):
    pass


@team.command(name="killua")
async def killua(ctx):
    pro = await procont('killua')
    if pro <= 0.35:
        points = collection.count_documents({"id": ctx.author.id})
        if points == 0:
            collection.update_many({'id': ctx.author.id},{'$set':{'team':'killua', 'points': 0, 'cooldowndaily': 0, 'cooldown': 0}}, upsert=True)
            await ctx.send("You sucessfully joined the `killua` team!")
        else:
            collection.update_one({'id': ctx.author.id},{'$set':{'team':'killua', 'points': 0}}, upsert=True)
            await ctx.send("You sucessfully joined the `killua` team! Your points from your previous team have been reset")     
    else:
        await ctx.send('The team currently has too many members, please join another team or wait for a spot to get free')

@team.command(name="gon")
async def gon(ctx):
    pro = await procont('gon')
    if pro <= 0.35:
        points = collection.count_documents({"id": ctx.author.id})
        if points == 0:
            collection.update_many({'id': ctx.author.id},{'$set':{'team':'gon', 'points': 0, 'cooldowndaily': 0, 'cooldown': 0}}, upsert=True)
            await ctx.send("You sucessfully joined the `gon` team!")
        else:
            collection.update_one({'id': ctx.author.id},{'$set':{'team':'gon', 'points': 0}}, upsert=True)
            await ctx.send("You sucessfully joined the `gon` team! Your points from your previous team have been reset")
    else:
        await ctx.send('The team currently has too many members, please join another team or wait for a spot to get free')

@team.command(name="kurapika")
async def kurapika(ctx):
    pro = await procont('kurapika')
    if pro <= 0.35:
        points = collection.count_documents({"id": ctx.author.id})
        if points == 0:
            collection.update_many({'id': ctx.author.id},{'$set':{'team':'kurapika', 'points': 0, 'cooldowndaily': 0, 'cooldown': 0}}, upsert=True)
        
            await ctx.send("You sucessfully joined the `kurapika` team!")
        else:
            collection.update_one({'id': ctx.author.id},{'$set':{'team':'kurapika', 'points': 0}}, upsert=True)
            await ctx.send("You sucessfully joined the `kurapika` team! Your points from your previous team have been reset")
    else:
        await ctx.send('The team currently has too many members, please join another team or wait for a spot to get free')

@team.command(name="leorio")
async def leorio(ctx):
    pro = await procont('leorio')
    if pro <= 0.35:
        points = collection.count_documents({"id": ctx.author.id})
        if points == 0:
            collection.update_many({'id': ctx.author.id},{'$set':{'team':'leorio', 'points': 0, 'cooldowndaily': 0, 'cooldown': 0}}, upsert=True)
            
            
            await ctx.send("You sucessfully joined the `leorio` team!")
        else:
            collection.update_one({'id': ctx.author.id},{'$set':{'team':'leorio', 'points': 0}}, upsert=True)
            await ctx.send("You sucessfully joined the `leorio` team! Your points from your previous team have been reset")
    else:
        await ctx.send('The team currently has too many members, please join another team or wait for a spot to get free')

@team.command(name="current")
async def current(ctx):
    results = collection.find({'id': ctx.author.id})
    for result in results:
        team = result['team']
    await ctx.send(f'You are currently member of the `{team}` team!')



@team.command(name="info")
async def info(ctx, text= None):
    if text:
        if text == 'Killua':
            embed = discord.Embed.from_dict({
            'title': 'Information about team Killua',
            'description': 'Hi, my name is Killua! I\'ve been trained by my family to be an assasin, long hard training, I\'ve killed lots of people already. When the only thing I want is being friends with Gon... I would be glad to so you in my team fighting by my side for the first place! \n\n Attributes: **power, intelligent, strong, putting friends always first**',
            'thumbnail':{
                'url': 'https://i.pinimg.com/474x/c8/15/e5/c815e5ea92cad30c6a6409dabf0358af.jpg'
            },
            'color': 0x1400ff
            })
            return await ctx.send(embed=embed)
        if text == 'Gon':
            embed = discord.Embed.from_dict({
            'title': 'Information about team Gon',
            'description': 'Hello, I am Gon! I am glad to be here, to have made so many friends on the search for my father and I love making more. I am kind to everyone unless someone hurts one of my friends, then I can get a bit... protective. Let\'s win this thing, together and make new friends on the way! \n\n Attributes: **kind, open hearted, protective**',
            'thumbnail':{
                'url': 'https://giantbomb1.cbsistatic.com/uploads/scale_medium/2/27436/2722697-gon_freecss_2617.jpg'
            },
            'color': 0x43AB15
            })
            return await ctx.send(embed=embed)
        if text == 'Leorio':
            embed = discord.Embed.from_dict({
            'title': 'Information about team Leorio',
            'description': 'Hi my name is Leorio! Originally I was planning to get my license to sell it, because as I say, money rules the world when all I want is being a doctor and able to help peoplle for free.. Then I met friends who helped my get my license and I love to spend time with them! For now I gotta learn for my exams though\n\n Attributes: **smart, money oriented**',
            'thumbnail':{
                'url': 'https://i.pinimg.com/736x/52/0e/b5/520eb54bcfe98466df902ad677d13b8e.jpg'
            },
            'color': 0x0D0293
            })
            return await ctx.send(embed=embed)
        if text == 'Kurapika':
            embed = discord.Embed.from_dict({
            'title': 'Information about team Kurapika',
            'description': 'Hello kind person, my name is Kurapika. I am the last surviving member of the Kurta-clan, the rest has been killed by a group called the Phantom Troupe and I\'ve made it my goal to ill every one of them. But unless I find one I am nice and kind but always searching for them \n\n Attributes: **excellent in cooking, experienced, powerfull, risiking everything**',
            'thumbnail':{
                'url': 'https://i.pinimg.com/originals/27/ca/b9/27cab9588503c762f88e6311751ebddf.jpg'
            },
            'color': 0xE8EB0B  
            })
            return await ctx.send(embed=embed)

        await ctx.send('Not an existing team')
    else:
        teaminfo = '\n'.join([f"{x['_id']}: {x['count']}" for x in list(collection.aggregate([{"$group": {"_id": "$team", "count": {"$sum": 1}}}]))])
        embed = discord.Embed(
            title = '**Teams info**',
            color = 0x00FF80,
            description = f'Introducing team mode!\n 4 teams are available to join\n Once you join a team, you collect points for it to get it on global rank 1!\n\n Join a team with `k!team <team name>`\n Teams: \n\nGon\n Killua\n Kurapika\n Leorio\n\n *For more info about each team and what it resembles, use `k!team info <team name>`*\n\nTeam ratio:\n {teaminfo}'
        )
        embed.set_thumbnail(url='https://imgix.ranker.com/user_node_img/3683/73654539/original/hunter-x-hunter-u47?fm=pjpg&q=80.img')
        await ctx.send(embed=embed)

@bot.command(aliases=['eval'])
async def exec(ctx, *, c):
    if ctx.author.id == 606162661184372736 or ctx.author.id == 383790610727043085:
        try:
            global bot
            await ctx.channel.send(f'```py\n{eval(c)}```')
        except Exception as e:
            await ctx.channel.send(str(e))
                              
@bot.command()
async def source(ctx, name):
    if ctx.author.id == 606162661184372736 or ctx.author.id == 383790610727043085:
        func = bot.get_command(name).callback
        code = inspect.getsource(func)
        await ctx.send('```python\n{}```'.format(code.replace('```', '``')))
                              

async def procont(team):
    amountteam = collection.count_documents({"team": team})
    amounttotal = collection.count_documents({})
    try:
        procentage = amountteam/amounttotal
        return procentage
    except Exception as e:
        return 0

bot.run('NzU2MjA2NjQ2Mzk2NDUyOTc1.X2OeUg.mt0HJ8nW3ADNMGz0xNAwhvsgJ-c')

import io
from discord.ext import commands
import aiohttp
import json
import time
import discord
import random
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
from datetime import date
import inspect
from discord.utils import find
from discord import client
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import os
import requests
import urllib
from numpy import *
from matplotlib.pyplot import *
import matplotlib.pyplot as plt
import numpy as np
import numexpr as ne


intents = discord.Intents.default()


cluster = MongoClient('not happenin danii')
db = cluster['Killua']
collection = db['teams']
top =db['teampoints']
server = db['guilds']
items = db['items']




bot = commands.Bot(command_prefix= 'kil!', description="default prefix", case_insensitive=True, intents=intents)
bot.remove_command('help')
cogs = ['ping']

for cog in cogs:
    bot.load_extension(f"Cogs.{cog}")



huggif = [f'https://cdn.discordapp.com/attachments/756945125568938045/758235270524698634/image0.gif', f'https://cdn.discordapp.com/attachments/756945125568938045/758236571974762547/image0.jpg', 'https://cdn.discordapp.com/attachments/756945125568938045/758236721216749638/image0.jpg', 'https://cdn.discordapp.com/attachments/756945125568938045/758237072975855626/image0.jpg', 'https://cdn.discordapp.com/attachments/756945125568938045/758237082484473856/image0.jpg', 'https://cdn.discordapp.com/attachments/756945125568938045/758237352756903936/image0.png', 'https://cdn.discordapp.com/attachments/756945125568938045/758237832954249216/image0.png']
topics = ['What motivates you?', 'What is the best thing about school/work?', 'What\'s better, having high expectations or having low expectations?', 'What was the last movie you saw?', 'Have you read anything good recently?', 'What is your favorite day of the year?', 'What kind of music do you like to listen to?', 'What things are you passionate about?', 'What is your favorite childhood memory?', 'If you could acquire any skill, what would you choose?', 'What is the first thing that you think of in the morning?', 'What was the biggest life change you have gone through?', 'What is your favorite song of all time?', 'If you won $1 million playing the lottery, what would you do?', 'How would you know if you were in love?', 'If you could choose to have any useless super power, what would you pick?', ]

@bot.command()
async def kick(ctx, member: discord.Member, *,reason=None):
    #t 30 minutes
    #h What you would expect of a ban command, bans a user and deletes all their messages of the last 24 hours, optional reason

    if ctx.channel.permissions_for(ctx.author).kick_members == True:

        if member.id == ctx.me.id:
            return await ctx.send('Hey!')

        if member.id == ctx.author.id:
            return await ctx.send('You can\'t kick yourself!')

        if ctx.author.top_role < member.top_role:
            return await ctx.send('You can\'t kick someone with a higher role than you')

        if ctx.me.top_role < member.top_role:
            return await ctx.send('My role needs to be moved higher up to grant me permission to kick this person')

        if ctx.channel.permissions_for(ctx.me).kick_members == False:
            return await ctx.send('I don\t have the permission to kick members yet')

        await member.send(f'You have been kicked from {ctx.guild.name} because of: ```\n{reason}```by `{ctx.author}`')
        await member.kick(reason=reason)
        await ctx.send(f':hammer: Kicked **{member}** because of: ```\n{reason}```Operating moderator: **{ctx.author}**')
    else:
        await ctx.send('Nice try but you don\'t have the required permission (`kick members`) to execute this command')

@bot.command()
async def ban(ctx, member: discord.Member, *,reason=None):
    #t 30 minutes
    #h What you would expect of a ban command, bans a user and deletes all their messages of the last 24 hours, optional reason

    if ctx.channel.permissions_for(ctx.author).ban_members == True:
        if member.id == ctx.author.id:
            return await ctx.send('You can\'t ban yourself!')

        if ctx.author.top_role < member.top_role:
            return await ctx.send('You can\'t ban someone with a higher role than you')

        if ctx.me.top_role < member.top_role:
            return await ctx.send('My role needs to be moved higher up to grant me permission to ban this person')

        if ctx.channel.permissions_for(ctx.me).ban_members == False:
            return await ctx.send('I don\t have the permission to ban members yet')

        await member.send(f'You have been banned from {ctx.guild.name} because of: ```\n{reason}```by `{ctx.author}`')
        await member.ban(reason=reason, delete_message_days=1)
        await ctx.send(f':hammer: Banned **{member}** because of: ```\n{reason}```Operating moderator: **{ctx.author}**')
    else:
        await ctx.send('Nice try but you don\'t have the required permission (`ban members`) to execute this command')
    
#guild.ban(discord.Object(id=x))

@bot.command()
async def unban(ctx, *, member):
    #t 1 hour
    #h Unbans a user by ID **or**, which is unique, by tag, meaning k!unban Kile#0606 will work :3
    banned_users = await ctx.guild.bans()

    if ctx.channel.permissions_for(ctx.author).ban_members == False:
        return await ctx.send('You do not have the permission to unban users')

    if ctx.channel.permissions_for(ctx.me).ban_members == False:
            return await ctx.send('I don\t have the permission to unban members yet, make sure you give me the permission `ban members`')

    if ctx.channel.permissions_for(ctx.me).view_audit_log == False:
            return await ctx.send('I don\t have the permission to view the audit log yet, make sure you give me the permission `view audit log`')

    
    try:
        int(member)
        try:
            user = discord.Object(id=int(member))
            if user is None:
                return await ctx.send(f'No user with the user ID {member} found')
            try:
                await ctx.guild.unban(user)
            except discord.NotFound:
                return await ctx.send('The user is not currently banned')
            await ctx.send(f':ok_hand: Unbanned **{user}**\nOperating moderator: **{ctx.author}**')
        except Exception as e:
            await ctx.send(e)
    except Exception:
        member_name, member_discriminator = member.split("#")
    

        loopround = 0

        for ban_entry in banned_users:
            bannedtotal = len(banned_users)
            user = ban_entry.user
        
            if (user.name, user.discriminator) == (member_name, member_discriminator):
                await ctx.guild.unban(user)
                await ctx.send(f':ok_hand: Unbanned {user.mention}\nOperating moderator: **{ctx.author}**')

            loopround = loopround+1
            if loopround == bannedtotal:
                return await ctx.send('User is not currently banned')

        #693957716044939305
        
            

@bot.command()
async def meme(ctx, memenumber, *, caption):
    session = aiohttp.ClientSession() 
    data = requests.get('https://api.imgflip.com/get_memes').json()['data']['memes']
    images = [{'name':image['name'],'url':image['url'],'id':image['id']} for image in data]
    URL = 'https://api.imgflip.com/caption_image'
    captions = caption.split('|')
    
    if len(captions) >= 2:
        text2 = captions[1]
    else:
        text2 = ''
    params = {
        'username': 'KileAlkuri',
        'password': 'Kile2-#2',
        'template_id': memenumber,
        'text0': str(captions[0]),
        'text1': text2
    }
    async with session.post(URL, params=params) as r: 
        response = await r.json()
    if response['success'] is False:
        await session.close()
        return await ctx.send(response['error_message'])

    embed = discord.Embed.from_dict({
            'title': 'Your fresh crafted meme',
            'image': {'url': response['data']['url']},
            'color': 0xc21a1a
        })
    await ctx.send(embed=embed)
    await session.close()

@bot.command()
async def memelist(ctx):
    data = requests.get('https://api.imgflip.com/get_memes').json()['data']['memes']
    images = [{'name':image['name'],'url':image['url'],'id':image['id']} for image in data]


    memelist = []
    ctr = 1
    for img in images:
        if ctr != 20:
            name = img['name']
            id = img['id']
            memelist.append(f'{ctr}) {name} ID: {id}')
            ctr = ctr+1
        else:
            return await ctx.send(str(memelist).replace(',', '\n'))
        
    


    
       
@bot.command()
async def help(ctx, group=None, command=None):
    if group is None and command is None:
        results = server.find({'id': ctx.guild.id})
        for result in results:
            pref = result['prefix']
        embed = discord.Embed.from_dict({
            'title': 'Bot commands',
            'description': f'''Current server Prefix: `{pref}` (Ignore on Killua dev)
            Command groups for {ctx.me.name}:

            :tools: `Moderation`

            :clown: `Fun`

            :trophy: `Economy/teams`

            <:killua_wink:769919176110112778> `Other`
            
            To see a groups commands, use```css\nhelp <groupname>```
            For more info to a specific command, use
            ```css\nhelp command <commandname>```''',
            'color': 0xc21a1a,
            'thumbnail': {'url': str(ctx.me.avatar_url)}
            })
        await ctx.send(embed=embed)
    elif group:
        if group.lower() in ['moderation', 'fun', 'economy', 'teams', 'other', 'command']:
            if command and group.lower() == 'command':
                try:
                    func = bot.get_command(command).callback
                    code = inspect.getsource(func)
                    linecount = code.splitlines()

                    restricted = ''
                    desc = 'No description yet'


                    for item in linecount:
                        first, middle, last = item.partition("#h")
                        firstr, middler, lastr = item.partition("#r")

                        if lastr is None or lastr == '':
                            restricted = ''
                        else:
                            retricted = f'\n\nCommand restricted to: {lastr}'

                        if last:
                            desc = last

                    

                    print(desc)

                    if lastr is None or lastr == '':
                        restricted = ''
                    else:
                        retricted = f'\n\nCommand restricted to: {lastr}'

                    embed = discord.Embed.from_dict({
                        'title': f'Info about command `k!{command}`',
                        'description': f'{desc} {restricted}',
                        'color': 0xc21a1a,
                        'thumbnail': {'url': str(ctx.me.avatar_url)}
                        })
                    await ctx.send(embed=embed)                    

                except Exception as e:
                    await ctx.send(e)
            else:
                embed = commands(group)
                embed.color = 0xc21a1a
                embed.set_thumbnail(url= str(ctx.me.avatar_url))
                await ctx.send(embed=embed)
        else:
            await ctx.send('Not a valid group, please make sure you know what groups are available')

def commands(commandgroup):
    if commandgroup.lower() == 'command':
        embed = discord.Embed.from_dict({'description': 'You need to input a command to see it\'s information'
            })
        return embed

    if commandgroup.lower() == 'moderation':
        embed = discord.Embed.from_dict({
            'title': 'Moderation commands',
            'description': '''```css\nprefix <string>```
            Sets a new prefix for Killua for the server, can only be used by admins

            ```css\nk!default pref```
            If you should have forgotten your prefix, run this command to reset it to `k!`'''
        })
        return embed

    if commandgroup.lower() == 'fun':
        embed = discord.Embed.from_dict({
            'title': 'Fun commands',
            'description': '''```css\nquote <@user> <text>```
            Send a screenshot of a user saying what you defined. Use `-c`ast the start of `text` for compact mode or `-l` for light mode or both

            ```css\ncmm <text>```
            Sends the *Change My Mind* meme with the text you defined

            ```css\nrps <@user> <optional integer>```
            Challenges someone to a game of Rock Paper Scissors. If you specify an amount you play with points and the winner gets them all

            ```css\nhug <@user>```
            We all need  more hugs in our life, this hugs the user specified

            ```css\ntopic```
            You suck at small talk? Get a topic with this command!

            *8 ball and heads or tails in planned*
            '''
        })
        return embed

    if commandgroup.lower() == 'economy' or commandgroup.lower() == 'teams':
        embed = discord.Embed.from_dict({
            'title': 'Economy/Teams commands',
            'description': '''```css\nteam <teamname>```
            Lets you join a team to collect points for it. Use `team current` to see your current Team

            ```css\nteaminfo <optional team>``
            Gives you more info about the Team system or individual Teams

            ```css\ndaily```
            Gives you your daily points
            
            ```css\ndaily```
            See how many points you hold on to'''
        })
        return embed

    if commandgroup.lower() == 'other':
        embed = discord.Embed.from_dict({
            'title': 'Other commands',
            'description': '''```css\nhi```
            Replies `Hi username, usertag` I am leaving this in because it was the first Killua command

            ```css\ninfo```
            Gives you some info about the bot
            
            ```css\npatreon```
            Gives you a link to my Patreon profile, feel free to help me and Killua out a bit <:killua_wink:769919176110112778>
            
            ```css\ninvite```
            Gives you the invite link to the bot
            
            ```css\ncodeinfo <command>```
            Gives you some more insights to a command like how long it took me etc
            
            ```css\npermissions```
            Killua lists his permissions on this server'''
        })
        return embed

@bot.command()
async def permissions(ctx):
    #t 30 min
    perms = ctx.me.guild_permissions
    permissions = '\n'.join([f"{v} {n}" for n, v in perms])
    prettier = permissions.replace('_', ' ').replace('True', '<:CheckMark:771754620673982484>').replace('False', '<:x_:771754157623214080>')
    embed = discord.Embed.from_dict({
            'title': 'Bot permissions',
            'description': prettier,
            'color': 0xc21a1a,
            'thumbnail': {'url': str(ctx.me.avatar_url)}
        })
    await ctx.send(embed=embed)



@bot.command()
async def load(ctx, extension):
    if ctx.author.id == 606162661184372736:
        bot.load_extension(f'Cogs.{extension}')
        await ctx.send(f'Loaded cog {extension}')

@bot.command()
async def unload(ctx, extension):
    if ctx.author.id == 606162661184372736:
        bot.unload_extension(f'Cogs.{extension}')
        await ctx.send(f'Unloaded cog {extension}')

@bot.group(name='top', invoke_without_command=True)
async def top(ctx):
    pass

@bot.command()
async def test2(ctx):    
    itemlist = items.list()
    await ctx.send(itemlist)


@bot.command()
async def shop(ctx, buy=None, item=None):
    try:

        if buy and item:
            if buy.lower() == 'buy':
                if item.lower() in itemlist:

                    results = collection.find({'name': item.lower()})
                    for result in results:
                        cost = result['cost']
                    results = collection.find({'id': ctx.author.id})
                    for result in results:
                        points = result['points']

                    if points < cost:
                        return await ctx.send('You can\'t afford this item')

                    collection.update_many({'id': ctx.author.id}, {'$set':{'points': points - cost}})


                else:
                    await ctx.send('Item not available')
            else:
                await ctx.send('Invalid action')
        else:
            random.choice(1, 2, 3)
    except Exception as e:
        await ctx.send(e)

@bot.event
async def on_ready():
    print('------')
    print('Logged in as: ' + bot.user.name + f" (ID: {bot.user.id})")
    print('------')
    bot.startup_datetime = datetime.now()
    print(os.getcwd())

@bot.event
async def on_guild_join(guild):
    await p()
    general = find(lambda x: x.name == 'general',  guild.text_channels)
    if general and general.permissions_for(guild.me).send_messages:
        embed = discord.Embed.from_dict({
            'title': 'Hello {}!'.format(guild.name),
            'description': 'Hi, my name is Killua dev, thank you for choosing me! \n\nTo get some info about me, use `k!info`\n\nTo change the server prefix, use `k!prefix <new prefix>` (you need administrator perms for that\n\nFor more commands, use `k!help` to see every command',
            'color': c21a1a
        })
        await general.send(embed=embed)

    try:
        
        results = server.find({'id': guild.id})
        for result in results:
            t = result['points']
        print(t)     
    except Exception as e:
        server.update_many({'id': guild.id},{'$set':{'points': 0,'items': '','badges': '', 'prefix': 'k!'}}, upsert=True)

@bot.command()
async def codeinfo(ctx, content):
    
    
    try:
        func = bot.get_command(content).callback
        code = inspect.getsource(func)
        linecount = code.splitlines()
        time= ''
        restricted = ''
        comment = ''

        for item in linecount:
            firstt, middlet, lastt = item.partition("#t")
            firstr, middler, lastr = item.partition("#r")
            firstc, middlec, lastc = item.partition("#c")
            if lastt == '':
                pass
            else:
                time = lastt
            if lastr == '':
                pass
            else:
                restricted = lastr
            if lastc == '':
                pass
            else:
                comment = lastc

            #c this very code
            #t 1-2 hours
        if restricted == '' or restricted is None or restricted == '")':
            realrestricted = ''
        else:
            realrestricted = f'**Restricted to:** {restricted}'

        embed= discord.Embed.from_dict({
            'title': f'Command **{content}**',
            'color': 0xc21a1a,
            'description': f'''**Characters:** {len(code)}
            **Lines:**  {len(linecount)}

            **Time spend on code:** {time or 'No time provided'}
            **Comments:** {comment or 'No comment'}
            
            {realrestricted}'''
            })
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send('Invalid command')

@bot.command()
async def urban(ctx, content):
    #t test
    #c test
    session = aiohttp.ClientSession() 
    headers = {'Content-Type': 'application/json',
        'Authorization': 'Bearer 16c6fa735e974848ea8395a4160b8'} 
    body = {
        'args': { 'text': content }
      } 
    
    async with session.post('https://fapi.wrmsr.io/urban', headers=headers, json=body) as r: 
        response = await r.json()

    if response == []:
        return await ctx.send(':x: Not found')

    
    desc = urbandesc(response)
    embed = discord.Embed.from_dict({
            'title': f'Results for **{content}**',
            'description': desc,

            'color': 0xc21a1a
            })
    await ctx.send(embed=embed)
    session.close
    
def urbandesc(array):
    
    desc = f'''**__{array[0]["header"]}__**
**Meaning** \n{array[0]["meaning"]}\n
**Example** \n{array[0]["example"]}\n'''

    try:
        desc = desc + f'''\n**__{array[2]["header"]}__**
    **Meaning** \n{array[2]["meaning"]}\n
    **Example** \n{array[2]["example"]}\n\n'''
    except Exception as e:
        print('no')
    try:
        desc = desc + f'''\n**__{array[3]["header"]}__**
    **Meaning** \n{array[3]["meaning"]}\n
    **Example** \n{array[3]["example"]}\n\n'''
    except Exception as e:
        print('no')

    return desc

@bot.command()
async def cmm(ctx, *, content):
    session = aiohttp.ClientSession() 
    headers = {'Content-Type': 'application/json',
        'Authorization': 'Bearer 16c6fa735e974848ea8395a4160b8'} 
    body = {
        'args': { 'text': content }
      } 
    
    async with session.post('https://fapi.wrmsr.io/changemymind', headers=headers, json=body) as r: 
        image_bytes = await r.read()
        file = discord.File(io.BytesIO(image_bytes), filename="image.png")
    await ctx.send(file=file)

@bot.command()
async def quote(ctx, quotist: discord.Member, *, content):
    #t 2 hours
    #c powered by fAPI
    light = False
    compact = False
    name = ''
    now = datetime.now()
    message = content
    realcolor = quotist.color
    hours = f"{now:%I}"
    if int(hours) < 10:
        hours = hours[1:]
    if str(quotist.color) == '#000000':
        realcolor = '#ffffff'
    else:
        realcolor = str(quotist.color)

    if content.startswith('-l'):
        light = True
        message = content[2:]
        if realcolor == '#ffffff':
            realcolor = '#000000'
    if content.startswith('-c'):
        compact = True
        message = content[2:]
    if message.startswith(' -c'):
        compact = True
        message = message[3:]
    if message.startswith(' -l'):
        light = True
        message = message[3:]
        if realcolor == '#ffffff':
            realcolor = '#000000'

    if quotist.nick:
        name = quotist.nick
    else: 
        name = quotist.name
    session = aiohttp.ClientSession() 
    headers = {'Content-Type': 'application/json',
        'Authorization': 'Bearer 16c6fa735e974848ea8395a4160b8'} 
    body = {
        'args': { 'message': {'content': message},
        'author': {'color': realcolor,
        'bot': quotist.bot,
        'username': str(name),
        'avatarURL': str(quotist.avatar_url)},
        'timestamp':  f'Today at {hours}:{now:%M %p}',
        'light': light,
        'compact': compact}
      } 
    
    async with session.post('https://fapi.wrmsr.io/quote', headers=headers, json=body) as r: 
        image_bytes = await r.read()
        file = discord.File(io.BytesIO(image_bytes), filename="absolutelyreal.png")
    await ctx.send(file=file)

@bot.command()
async def say(ctx, *, content):
    #t 10 minutes
    #r User 606162661184372736
    #c Me
    if ctx.author.id == 606162661184372736:
        await ctx.message.delete()
        await ctx.send(content)

@bot.command()
async def ping(ctx):
    start = time.time()
    msg = await ctx.send('Pong!')
    end = time.time()
    await msg.edit(content = str('Pong in `' + str(1000 * (end - start))) + '` ms')

@bot.command()
async def hunter(ctx,  *, content=None):
    print('Executed')
    if content:
        if ctx.message.mentions:
            user = message.mentions[0]
            embed = await hunterinfofront(user)
            await ctx.send(embed=embed)

        else:
            ctx.send('Invalid user')
    else:
        user = ctx.author
        embed = await hunterinfofront(user)
        ctx.send(embed=embed)
    

async def hunterinfofront(user: discord.Member):  

    results = collection.find({'id': user.id})
    for result in results:
            pro = result['pro']
            name = result['name']
            
    if pro == True:
        im = Image.open("/Users/eriklippert/Documents/prohunterfront.PNG")
        helvetica = ImageFont.truetype(size=40)
        d = ImageDraw.Draw(im)

        location = (100, 50)
        
        d.text(location, user.name)

        endresult = im.save("drawn_grid.png")

    else:
        im = Image.open("/Users/eriklippert/Documents/hunterfront.PNG")
        helvetica = ImageFont.truetype(size=40)
        d = ImageDraw.Draw(im)

        location = (100, 50)
        
        d.text(location, user.name)

        cendresult = im.save("drawn_grid.png")

    embed = discord.Embed.from_dict({
        'title': f'License of {user.name}',
        'image': endresult,
        'color': 0x1400ff
        })
    return embed



@bot.event
async def on_connect():
    await p()
    days.start()
    


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


@bot.command()
async def info(ctx):
    embed = discord.Embed(
        title = 'Info',
        description = ' This is Killua-dev, Kile\'s dev-bot version 0.5 where he runs experimenta l scripts to upload them later. The first features simply include this command, `k!source` (restricted), `k!hi` and and `k!hug <user>` with way more on the main bot\n I hope to be adding a lot more soon while I figure Python out on the go\n\n **Last time started:**\n '+ str(bot.startup_datetime.strftime('%Y-%m-%d-%H:%M:%S')),
        color = 0xc21a1a
    )
    await ctx.send(embed=embed) 

@bot.command()
async def test(ctx):
    try:
        results = collection.find({'id': 3})
        for result in results:
            t = result['team']
            
        await ctx.send(f'You are currently member of the `{t}` team!')
    except Exception as e:
        await ctx.send('You currently are in no team')

@bot.command()
async def hug(ctx,  *, content=None, pass_context=True):
    if ctx.message.mentions:
        if ctx.author == ctx.message.mentions[0]:
            return await ctx.send(f'Someone hug {ctx.author.name}!')
        
        hugtext = [f'**{ctx.author.name}** gives **{ctx.message.mentions[0].name}** a bearhug', f'**{ctx.author.name}** finds a lamp with a Jinn and gets a wish. So they wish to hug **{ctx.message.mentions[0].name}**', f'**{ctx.author.name}** asks **{ctx.message.mentions[0].name}** for motivation and gets a hug']
        embed = discord.Embed.from_dict({
            'title': random.choice(hugtext),
            'image':{
                'url': random.choice(huggif)},

            'color': 0xc21a1a
            })
        await ctx.send(embed=embed)
    else:
        await ctx.send('Invalid user.. Should- I hug you?')
        def check(m):
            return m.content.lower() == 'yes' and m.author == ctx.author

        msg = await bot.wait_for('message', check=check, timeout=60) 
        hugtextself = [f"**Killua** gives **{ctx.author.name}** a bearhug", f"**Killua** finds a lamp with a Jinn and gets a wish. So they wish to hug **{ctx.author.name}**", f"**Killua** asks **{ctx.author.name}** for motivation and gets a hug"]
        embed = discord.Embed.from_dict({
            'title': random.choice(hugtextself),
            'image':{
                'url': random.choice(huggif)
            },
            'color': 0xc21a1a
            })
        await ctx.send(embed=embed) 

@bot.command()
async def points(ctx):
    results = collection.find({'id': ctx.author.id})
    for result in results:
        p1 = result['points']
    await ctx.send(f'You currently hold on to {p1} points!')


@bot.command()
async def rps(ctx, member: discord.User, points: int=None):
    t2 = None
    p2 = 0

    resultsopp = collection.find({'id': member.id})
    for resulte in resultsopp:
        p2 = resulte['points']
        t2 = resulte['team']

    print(t2)

    results = collection.find({'id': ctx.author.id})
    for result in results:
        p1 = result['points']
        t1 = result['team']

    try:

        if t1 == None and points:
            await ctx.send('You need to join a team to play Rock Paper Scissors')
            return
        
        if points:
            if points <= 0 or points > 100:
                await ctx.send(f'You can only play using 1-100 points')
                return

        if points:
            if p1 < points or p1 is None:
                await ctx.send(f'You do not have enough points for that. Your current balance is `{str(p1)}`')
                return

        
        channel = ctx.message.channel
       

        if member.id == 758031913788375090:
            await ctx.author.send('You chose to play Rock Paper Scissors against me, what\'s your choice? **[Rock] [Paper] [Scissors]**')

            embed = discord.Embed.from_dict({
                'title': f'{ctx.author.name} against Killua-dev: **Rock... Paper... Scissors!**',
                'image': {'url': 'https://media1.tenor.com/images/dc503adb8a708854089051c02112c465/tenor.gif?itemid=5264587'},
                'color': 0xc21a1a
                })

            await ctx.send(embed= embed)
            def check(m):
                return m.content.lower() == 'scissors' or m.content.lower() == 'paper' or m.content.lower() == 'rock' and m.author == ctx.author
                
            msg = await bot.wait_for('message', check=check, timeout=60) 

            winlose = await rpsf(msg.content, random.choice(['paper', 'rock', 'scissors']))
            
            if winlose == 1:
                result = botemote(msg.content, 1)
                if points:
                    collection.update_one({'id': ctx.author.id}, {'$set':{'points': p1 + points}})
                    await channel.send(f'{rpsemote(msg.content.lower())} > {rpsemote(result)}: {ctx.author.mention} won against <@758031913788375090> winning {points} points')
                else:
                    await channel.send(f'{rpsemote(msg.content.lower())} > {rpsemote(result)}: {ctx.author.mention} won against <@758031913788375090>')
            if winlose == 2:
                result = botemote(msg.content, 2)
                await channel.send(f'{rpsemote(msg.content.lower())} = {rpsemote(result)}: {ctx.author.mention} tied against <@758031913788375090>')
            if winlose == 3:
                result = botemote(msg.content, 3)
                if points:
                    collection.update_one({'id': ctx.author.id}, {'$set':{'points': p1 - points}})
                    await channel.send(f'{rpsemote(msg.content.lower())} < {rpsemote(result)}: {ctx.author.mention} lost against <@758031913788375090> losing {points} points')
                else:
                    await channel.send(f'{rpsemote(msg.content.lower())} < {rpsemote(result)}: {ctx.author.mention} lost against <@758031913788375090>')
        else:
            
            
            if t2 is None and points:

                await ctx.send(f'{member.mention} is not part of a team yet')
                return

            if points:
                if int(p2) < points or p2 is None and points:

                    await ctx.send(f'{member.mention} does not have enough points for that. Their current balance is `{str(p2)}`')
                    return
            

            await ctx.send(f'{ctx.author.mention} challanged {member.mention} to a game of Rock Papaper Scissors! Will **{member.name}** accept the challange?\n **[y/n]**')
            def check(m1):
                    return m1.content.lower() in ["n", "y"] and m1.author.id == member.id

            try:
                    confirmmsg = await bot.wait_for('message', check=check, timeout=60)

            except asyncio.TimeoutError:

                await ctx.send('Sadly no answer, try it later bud')

            else:
                if confirmmsg.content.lower() == 'y':

                    embed = discord.Embed.from_dict({
                        'title': f'{ctx.author.name} against {member.name}: **Rock... Paper... Scissors!**',
                        'image': {'url': 'https://media1.tenor.com/images/dc503adb8a708854089051c02112c465/tenor.gif?itemid=5264587'},
                        'color': 0xc21a1a
                    })
                        
                    await ctx.send(embed= embed)
                    await ctx.author.send('You chose to play Rock Paper Scissors, what\'s your choice Hunter? **[Rock] [Paper] [Scissors]**') 
                    await member.send('You chose to play Rock Paper Scissors, what\'s your choice Hunter? **[Rock] [Paper] [Scissors]**') 


                    def checkauthor(m2):
                        
                        return  m2.content.lower() in ["rock", "paper", "scissors"] and m2.author == ctx.author and m2.guild is None
                    def checkopp(m3):
                       
                        return  m3.content.lower() in ["rock", "paper", "scissors"] and m3.author == member and m3.guild is None
                    

                    done, pending = await asyncio.wait([
                        bot.wait_for('message', check= checkauthor),
                        bot.wait_for('message', check= checkopp)
                    ], return_when=asyncio.ALL_COMPLETED)

                    
                    
                    r1, r2 = [r.result() for r in done]

                    
                    
                    winlose = await rpsf(str(r1.content), str(r2.content))
                    if winlose == 1:
                        if points:
                            collection.update_one({'id': ctx.author.id}, {'$set':{'points': p1 + points}})
                            collection.update_one({'id': member.id}, {'$set':{'points': p2 - points}})
                            await channel.send(f'{rpsemote(r1.content.lower())} > {rpsemote(r2.content.lower())}: {ctx.author.mention} won against {member.mention} winning {points} points')
                        else:
                             await channel.send(f'{rpsemote(r1.content.lower())} > {rpsemote(r2.content.lower())}: {ctx.author.mention} won against {member.mention}')
                    if winlose == 2:
                        await channel.send(f'{rpsemote(r1.content.lower())} = {rpsemote(r2.content.lower())}: {ctx.author.mention} tied against {member.mention}')
                    if winlose == 3:
                        if points:
                            collection.update_one({'id': ctx.author.id}, {'$set':{'points': p1 - points}})
                            collection.update_one({'id': member.id}, {'$set':{'points': p2 + points}})
                            await channel.send(f'{rpsemote(r1.content.lower())} < {rpsemote(r2.content.lower())}: {ctx.author.mention} lost against {member.mention} losing {points } points')
                        else:
                            await channel.send(f'{rpsemote(r1.content.lower())} < {rpsemote(r2.content.lower())}: {ctx.author.mention} lost against {member.mention}')
                else:
                    await ctx.send(f'{member.name} does not want to play...')

    except Exception as e:
        await ctx.send(e)
    
def rpsemote(choice):
    if choice == 'paper':
        return '📄'
    if choice == 'rock':
        return '🗿'
    if choice == 'scissors':
        return ':scissors:'

def botemote(playeremote, winlose):
    print(playeremote)
    if playeremote.lower() == 'paper':
        if winlose == 1:
            return 'rock'
        if winlose == 2:
            return 'paper'
        if winlose == 3:
            return 'scissors'

    if playeremote.lower() == 'rock':
        if winlose == 1:
            return 'scissors'
        if winlose == 2:
            return 'rock'
        if winlose == 3:
            return 'paper'

    if playeremote.lower() == 'scissors':
        if winlose == 1:
            return 'paper'
        if winlose == 2:
            return 'scissors'
        if winlose == 3:
            return 'rock'

async def rpsf(choice1, choice2):

    if choice1.lower() == 'rock' and choice2.lower() == 'scissors':
        return 1
    if choice1.lower() == 'rock' and choice2.lower() == 'rock':
        return 2
    if choice1.lower() == 'rock' and choice2.lower() == 'paper':
        return 3
    if choice1.lower() == 'paper' and choice2.lower() == 'rock':
        return 1
    if choice1.lower() == 'paper' and choice2.lower() == 'paper':
        return 2
    if choice1.lower() == 'paper' and choice2.lower() == 'scissors':
        return 3
    if choice1.lower() == 'scissors' and choice2.lower() == 'paper':
        return 1
    if choice1.lower() == 'scissors' and choice2.lower() == 'scissors':
        return 2
    if choice1.lower() == 'scissors' and choice2.lower() == 'rock':
        return 3

@bot.command(aliases=['patreon'])
async def support(ctx):

    embed = discord.Embed.from_dict({
        'title': '**Support Killua**',
        'thumbnail':{
            'url': 'https://cdn.discordapp.com/avatars/758031913788375090/e44c0de4678c544e051be22e74bc502d.png?size=1024'},
        'description': 'Hey, do you have too much money? I have a solution for that! I now have a Patreon account where you can donate to support me and get special stuff, helping with bulding Killua. No that I expect anyone to do this, but I have it set up now.\n\n https://www.patreon.com/KileAlkuri',
        'color': 0xc21a1a
    })
    await ctx.send(embed=embed)








 

#for filename in os.listdir('Users/eriklippert/Cogs'):
    #if filename.endswith('.py'):
       # bot.load_extension(f'Cogs.{filename[:-3]}')

config = json.loads("config.json")
bot.run(config["token"])

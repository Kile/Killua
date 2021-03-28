import discord
import io
import aiohttp
import time
from datetime import datetime, timedelta
from discord.ext import commands
import json
from json import loads
from killua.functions import custom_cooldown, blcheck
import typing
import asyncio

with open('config.json', 'r') as config_file:
	config = json.loads(config_file.read())

class Api(commands.Cog):
  
  def __init__(self, client):
    self.client = client


  @commands.command(aliases=['image', 'i'])
  @custom_cooldown(15)
  async def img(self, ctx, *, content):
    if blcheck(ctx.author.id) is True:
        return
    #h Get DuckDuckGo Images with this command! Use n or b to go back and forth between sides
    #u image <text>
    # Creating a session
    session = aiohttp.ClientSession()
    # Inserting api details
    headers = {'Content-Type': 'application/json',
        'Authorization': f'Bearer {config["fapi"]}'}
    body = {
        'args': { 'text': content, 'safetyLevel': 1}
    } 
    # Making the api request
    async with session.post('https://fapi.wrmsr.io/duckduckgoimages', headers=headers, json=body) as r:
        if r.status != 200:
            # r.status is 200 when everyting is fine, if that isn't the case it returns an error
            await session.close()
            return await ctx.send(f':x: Error: {r.status}') 
        #Getting a list of the image results urls
        urls = await r.json()

    embed = discord.Embed.from_dict({
        'title': f'Results for: {content}',
        'description': f'Page 1 of {len(urls)}',
        'image': {'url': urls[0]},
        'color': 0x1400ff,
        'footer': {'icon_url': str(ctx.author.avatar_url), 'text': f'Requested by {ctx.author}'}
    })
        
    msg = await ctx.send(embed=embed)
    # Making the user able to go through the images
    await imagepage(self,msg,ctx.author,1,urls, content)
    await session.close()


  @commands.command()
  @custom_cooldown(15)
  async def gay(self, ctx, image:typing.Union[discord.User, int, str]=None):
    #u gay <user/url>
    #h Lays a pride flag over a user's pfp by mentioning them, their Id or over a url to an image you provide
    if blcheck(ctx.author.id) is True:
        return
    # Looking if the argument is a user, then we just need the avatar url
    if isinstance(image, discord.User):
        image = str(image.avatar_url)
    # If the argument is an integer, we try to fetch a user with that integer as ID and get their avatar url
    if isinstance(image, int):
        try:
            user = await self.client.fetch_user(image)
            image = str(user.avatar_url)
        except:
            return await ctx.send('Invalid ID')
    # If no argument is provided we take the authors pfp
    if not image:
        image = str(ctx.author.avatar_url)
    # Creating a session
    session = aiohttp.ClientSession() 
    # Inserting api details
    headers = {'Content-Type': 'application/json',
        'Authorization': f'Bearer {config["fapi"]}'} 
    body = {
        'images': [str(image)]
    } 
    # Making the api request
    async with session.post('https://fapi.wrmsr.io/gay', headers=headers, json=body) as r: 
        if r.status != 200:
            # r.status is 200 when everyting is fine, if that isn't the case it returns an error
            await session.close()
            return await ctx.send(f':x: Error: {r.status}')
        image_bytes = await r.read()
        file = discord.File(io.BytesIO(image_bytes), filename="image.png")
    await ctx.send(file=file)
    await session.close()

  @commands.command(aliases=['fapi', 'api'])
  @custom_cooldown(15)
  async def f(self, ctx, t:str=None, image:typing.Union[discord.User, int, str]=None):
    #u fapi <type> <user/url>
    #h Get any feature of the API Killua uses! Provide a type and then ID, mention or url to let the API do it's thing. For a list of available types, use k!f
    if blcheck(ctx.author.id) is True:
        return
    # All the options the api I use provides that I consider SFW
    options = ['adidas', 'ajit', 'america', 'analysis', 'austin', 'autism', 
    'bandicam', 'bernie', 'blackify', 'blackpanther', 'bobross', 'coolguy', 'deepfry',
    'dork', 'excuse', 'eyes', 'gaben', 'gay', 'glitch', 'glow', 'god', 'goldstar', 'hawking', 
    'hypercam', 'ifunny', 'isis', 'israel', 'jack' , 'jesus', 'keemstar', 'keemstar2', 'kekistan', 
    'kirby', 'lego', 'linus', 'logan', 'miranda', 'northkorea', 'oldguy', 'perfection', 
    'resize', 'russia', 'spain', 'stock', 'surpreme', 'thinking', 'trans', 'trump', 'uk', 'ussr', 
    'wheeze', 'yusuke', 'zuckerberg']
    optionsformatted = ', '.join(options)
    # Sending options if there are no further args
    if not t and not image:
        try:
            await ctx.author.send(f'Available types for `k!f <type> <image>`:```\n{optionsformatted}```')
            await ctx.send('Send you a list of available types for `k!f` :3')
            return
        except:
            await ctx.send('I was not able to dm you, please open your dms to me')
            return
    # If the type is no available
    if not t.lower() in options:
        return await ctx.send('No valid type! Use `k!f <type> <mention/id/link>`. For a list of available types use `k!a`')
    # Looking if the argument is a user, then we just need the avatar url
    if isinstance(image, discord.User):
        image = str(image.avatar_url)
     # If the argument is an integer, we try to fetch a user with that integer as ID and get their avatar url
    if isinstance(image, int):
        try:
            user = await self.client.fetch_user(image)
            image = str(user.avatar_url)
        except:
            return await ctx.send('Invalid ID')
    # If no argument is provided we take the authors pfp
    if not image:
        image = str(ctx.author.avatar_url)
    # Creating a session
    session = aiohttp.ClientSession() 
    # Inserting API details
    headers = {'Content-Type': 'application/json',
        'Authorization': f'Bearer {config["fapi"]}'} 
    body = {
        'images': [str(image)]
    } 
        
        
    async with session.post(f'https://fapi.wrmsr.io/{t.lower()}', headers=headers, json=body) as r:
        if r.status != 200:
            await session.close()
            return await ctx.send(f':x: Error: {r.status}')
        image_bytes = await r.read()
        file = discord.File(io.BytesIO(image_bytes), filename="image.png")
    await ctx.send(file=file)
    await session.close()


  @commands.command(aliases=['ej', 'emojimosaic'])
  @custom_cooldown(15)
  async def emojaic(self, ctx, image:typing.Union[discord.User, int, str]=None):
    if blcheck(ctx.author.id) is True:
        return
    #c Emoji mosaic an image!
    #t Around 1 hour
    #h Emoji mosaic an image; let emojis recreate an image you gave Killua! Takes in a mention, ID or image url
    #u emojaic <user/url>
    if isinstance(image, discord.User):
        image = str(image.avatar_url)
    if isinstance(image, int):
        try:
            user = await self.client.fetch_user(image)
            image = str(user.avatar_url)
        except:
            return await ctx.send('Invalid ID')

    if not image:
        image = str(ctx.author.avatar_url)

    session = aiohttp.ClientSession() 
    headers = {'Content-Type': 'application/json',
        'Authorization': f'Bearer {config["fapi"]}'} 
    body = {
        'images': [str(image)], 'args':{'text': 72}
    } 
        
    
    async with session.post('https://fapi.wrmsr.io/emojimosaic', headers=headers, json=body) as r:
        if r.status != 200:
            await session.close()
            return await ctx.send(f':x: Error: {r.status}') 
        image_bytes = await r.read()
        file = discord.File(io.BytesIO(image_bytes), filename="image.png")
    await ctx.send(file=file)
    await session.close()

  @commands.command()
  @custom_cooldown(15)
  async def urban(self, ctx, *,content):
    if blcheck(ctx.author.id) is True:
      return
    session = aiohttp.ClientSession() 
    headers = {'Content-Type': 'application/json',
            'Authorization': f'Bearer {config["fapi"]}'}
    body = {
        'args': { 'text': content }
      } 
    #t 2-3 hours
    #c Using fAPI
    #h Use this command to get the definition of a word from the urban dictionary, use "" around more than one word if you want to search for that
    #u urban <text>
    async with session.post('https://fapi.wrmsr.io/urban', headers=headers, json=body) as r: 
        if r.status != 200:
            await session.close()
            return await ctx.send(f':x: Error: {r.status}')
        response = await r.json()

    if response == []:
        await session.close()
        return await ctx.send(':x: Not found')

    desc = urbandesc(response)
    embed = discord.Embed.from_dict({
            'title': f'Results for **{content}**',
            'description': desc,

            'color': 0x1400ff
            })
    await ctx.send(embed=embed)
    await session.close()
    

  @commands.command()
  @custom_cooldown(15)
  async def cmm(self, ctx, *, content):
    if blcheck(ctx.author.id) is True:
      return
    #c Change my mind!
    #t Around 1-2 hours
    #h Craft your Change My Mind meme with this command
    #u cmm <text>
    session = aiohttp.ClientSession() 
    headers = {'Content-Type': 'application/json',
        'Authorization': f'Bearer {config["fapi"]}'} 
    body = {
        'args': { 'text': content }
      } 
    
    async with session.post('https://fapi.wrmsr.io/changemymind', headers=headers, json=body) as r:
        if r.status != 200:
            await session.close()
            return await ctx.send(f':x: Error: {r.status}')
        image_bytes = await r.read()
        file = discord.File(io.BytesIO(image_bytes), filename="image.png")
    await ctx.send(file=file)
    await session.close()
    
  @commands.command()
  @custom_cooldown(20)
  async def quote(self, ctx, quotist: discord.Member, *, content):
    if blcheck(ctx.author.id) is True:
      return
    #t 2 hours
    #c powered by fAPI
    #h Fake a user saying something with this command by specifying who, what and some other stuff
    #u quote <user> <text>
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
        'Authorization': f'Bearer {config["fapi"]}'} 
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
        if r.status != 200:
            await session.close()
            return await ctx.send(f':x: Error: {r.status}') 
        image_bytes = await r.read()
        file = discord.File(io.BytesIO(image_bytes), filename="absolutelyreal.png")
    await ctx.send(file=file)

'''function urbandesc
Input: 
array: a list with results from the search term from the command

Returns:
embed: a discord embed with the first 2 urban dictionary results

Function:
"outsources" the making of the embed with the results
'''
    
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

'''async function imagepage
Input:
self: because the function is outside of a cog we need to pass it self
msg (discord.Message): the message we send the first result with so we can edit it
author (discord.Member): the author so we make sure only the author can turn pages
page (int): The current page the user is on
array (list): The list of the image urls so we only have to make one API request
content (str): The search name so it can be displayed as a title

Returns:
The function itself

Purpose:
For the user to be able to look through results of their image search
'''

async def imagepage(self, msg:discord.Message, author:discord.Member, page:int, array:list, content:str):
    def check(m):
        return m.content.lower() in ["n", "b"] and m.author.id == author.id

    try:
        confirmmsg = await self.client.wait_for('message', check=check, timeout=60)
    except asyncio.TimeoutError:
        return 
    else:
        if confirmmsg.content.lower() == 'b':
            if page == 1:
                page = len(array)
            else:
                page = page-1
        if confirmmsg.content.lower() == 'n':
            if page == len(array):
                page = 1
            else:
                page = page+1

        embed = discord.Embed.from_dict({
            'title': f'Results for: {content}',
            'description': f'Page {page} of {len(array)}',
            'image': {'url': array[page-1]},
            'color': 0x1400ff,
            'footer': {'icon_url': str(author.avatar_url), 'text': f'Requested by {author}'}
        })
        try:
            await confirmmsg.delete()
        except Exception as e:
            print(e)
        await msg.edit(embed=embed)
        return await imagepage(self, msg, author, page, array, content)

Cog = Api

def setup(client):
  client.add_cog(Api(client))

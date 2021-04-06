import discord
import io
import aiohttp
from discord.ext import commands
import json
from json import loads
from killua.functions import custom_cooldown, blcheck
import typing
import asyncio
import re
from pypxl import Pxlapi # My own library :sparkles:

with open('config.json', 'r') as config_file:
	config = json.loads(config_file.read())

pxl = Pxlapi(token=config["pxlapi"], stop_on_error=False)



async def validate_input(self, ctx, args): # a useful check that looks for what url to pass pxlapi

    image = None
    if isinstance(args, discord.Member):
        image = str(args.avatar_url_as(static_format='png'))
        
    if isinstance(args, str):
        if args.isdigit():
            try:
                user = await self.client.fetch_user(int(args))
                image = str(user.avatar_url_as(static_format='png'))
            except:
                return None
        else:
            url = re.search(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))', args)
            if not url:
                return None 
            else:
                image = args

    if not image:
        async for message in ctx.channel.history(limit=20):
            if len(message.attachments) > 0:
                image = message.attachments[0].url
                break
            elif len(message.embeds) > 0:
                embed = message.embeds[0]
                if embed.image:
                    image = embed.image.url
                    break
                if embed.thumbnail:
                    image = embed.thumbnail.url
                    break
    if not image:
        image = str(ctx.author.avatar_url_as(static_format='png'))  
    return image

class Api(commands.Cog):

    def __init__(self, client):
        self.client = client

    @commands.command(aliases=['ej', 'emojimosaic'])
    @custom_cooldown(60) # Long cooldown >-<
    async def emojaic(self, ctx, args:typing.Union[discord.Member, str]=None):
        #h Emoji mosaic an image; let emojis recreate an image you gave Killua! Takes in a mention, ID or image url
        #u emojaic <user/url>
        if blcheck(ctx.author.id) is True:
            return
        
        data = await validate_input(self, ctx, args)
        if not data:
            return await ctx.send('Invalid arguments passed! Try again')
        r = await pxl.emojaic([data], groupSize=6)
        if isinstance(r, str):
            return await ctx.send(":x: "+r)
        else:
            f = discord.File(io.BytesIO(r), filename="emojaic.png")
            return await ctx.send(file=f)

    @commands.command()
    @custom_cooldown(5)
    async def flag(self, ctx, flag:str, args:typing.Union[discord.Member, str]=None):
        if blcheck(ctx.author.id) is True:
            return
        #h Valid flags: asexual, aromantic, bisexual, pansexual, gay, lesbian, trans, nonbinary, genderfluid, genderqueer, polysexual, austria, belgium, botswana, bulgaria, ivory, estonia, france, gabon, gambia, germany, guinea, hungary, indonesia, ireland, italy, luxembourg, monaco, nigeria, poland, russia, romania, sierraleone, thailand, ukraine, yemen
        #u flag <flag> <user/url>
        
        data = await validate_input(self, ctx, args)
        if not data:
            return await ctx.send('Invalid arguments passed! Try again')
        r = await pxl.flag(flag=flag, images=[data])
        if isinstance(r, str):
            return await ctx.send(":x: "+r)
        else:
            f = discord.File(io.BytesIO(r), filename="flag.png")
            return await ctx.send(file=f)

    @commands.command()
    @custom_cooldown(30)
    async def glitch(self, ctx, args:typing.Union[discord.Member, str]=None):
        #h Tranform a users pfp into a glitchy GIF!
        #u glitch <user/url>
        if blcheck(ctx.author.id) is True:
            return
        
        data = await validate_input(self, ctx, args)
        if not data:
            return await ctx.send('Invalid arguments passed! Try again')
        r = await pxl.glitch(images=[data])
        if isinstance(r, str):
            return await ctx.send(":x: "+r)
        else:
            f = discord.File(io.BytesIO(r), filename="glitch.gif")
            return await ctx.send(file=f)

    @commands.command()
    @custom_cooldown(15)
    async def lego(self, ctx, args:typing.Union[discord.Member, str]=None):
        #h Legofies an image
        #u lego <user/url>
        if blcheck(ctx.author.id) is True:
            return
        
        data = await validate_input(self, ctx, args)
        if not data:
            return await ctx.send('Invalid arguments passed! Try again')
        r = await pxl.lego(images=[data], scale=True, groupSize=10)
        if isinstance(r, str):
            return await ctx.send(":x: "+r)
        else:
            f = discord.File(io.BytesIO(r), filename="lego.png")
            return await ctx.send(file=f)

    @commands.command(aliases=['snap'])
    @custom_cooldown(10)
    async def snapchat(self, ctx, filter:str, args:typing.Union[discord.Member, str]=None):
        if blcheck(ctx.author.id) is True:
            return

        #h Valid filters: dog, dog2, dog3, pig, flowers, random
        #u flag <flag> <user/url>
        
        data = await validate_input(self, ctx, args)
        if not data:
            return await ctx.send('Invalid arguments passed! Try again')
        r = await pxl.snapchat(filter=filter, images=[data])
        if isinstance(r, str):
            return await ctx.send(":x: "+r)
        else:
            f = discord.File(io.BytesIO(r), filename="snap.png")
            return await ctx.send(file=f)

    @commands.command()
    @custom_cooldown(5)
    async def thonkify(self, ctx, *, text:str):
        if blcheck(ctx.author.id) is True:
            return
        #h Turn text into thonks!
        #u thonkify <text>

        r = await pxl.thonkify(text=text)
        if isinstance(r, str):
            return await ctx.send(":x: "+r)
        else:
            f = discord.File(io.BytesIO(r), filename="thonk.png")
            return await ctx.send(file=f)

    @commands.command(aliases=['screen'])
    @custom_cooldown(15)
    async def screenshot(self, ctx, website:str):
        if blcheck(ctx.author.id) is True:
            return
        #h screenshot the specified webste!
        #u screenshot <url>

        r = await pxl.screenshot(url=website)
        if isinstance(r, str):
            return await ctx.send(":x: "+r)
        else:
            f = discord.File(io.BytesIO(r), filename="screenshot.png")
            return await ctx.send(file=f)

    @commands.command()
    @custom_cooldown(5)
    async def sonic(self, ctx, *, text:str):
        if blcheck(ctx.author.id) is True:
            return
        #h Let sonic say anything you want
        #u sonic <text>

        r = await pxl.sonic(text=text)
        if isinstance(r, str):
            return await ctx.send(":x: "+r)
        else:
            f = discord.File(io.BytesIO(r), filename="sonic.png")
            return await ctx.send(file=f)

    @commands.command(aliases=['8bit', 'blurr'])
    @custom_cooldown(5)
    async def jpeg(self, ctx, args:typing.Union[discord.Member, str]=None):
        if blcheck(ctx.author.id) is True:
            return
        #h Did you ever want to decrease image quality? Then this is the command for you!
        #u jpeg <user/url>
        
        data = await validate_input(self, ctx, args)
        if not data:
            return await ctx.send('Invalid arguments passed! Try again')
        r = await pxl.jpeg(images=[data])
        if isinstance(r, str):
            return await ctx.send(":x: "+r)
        else:
            f = discord.File(io.BytesIO(r), filename="jpeg.png")
            return await ctx.send(file=f)

    @commands.command(aliases=['g','search'])
    @custom_cooldown(5)
    async def google(self, ctx, *, query:str):
        if blcheck(ctx.author.id) is True:
            return
        #h Get the best results for a query the web has to offer
        #u search <query>
        
        r = await pxl.web_search(query=query)
        if isinstance(r, str):
            return await ctx.send(":x: "+r)
        else:
            results = r['results']
            embed = discord.Embed.from_dict({
                'title': f'Results for query {query}',
                'color': 0x1400ff,
            })
            for i in range(4 if len(results) >= 4 else len(results)):
                res = results[i-1]
                embed.add_field(name='** **', value=f'__**[{res["title"]}]({res["url"]})**__\n{res["description"][:100]}...' if len(res["description"]) > 100 else res["description"], inline=False)
            await ctx.send(embed=embed)

    @commands.command(aliases=['image'])
    @custom_cooldown(15)
    async def img(self, ctx, *,query:str):
        if blcheck(ctx.author.id) is True:
            return
        #h Search any image you want
        #u img <query>
        
        r = await pxl.image_search(query=query)
        if isinstance(r, str):
            return await ctx.send(":x: "+r)
        else:
            return await paginator(self.client, ctx, 1, query, r, True)

async def paginator(bot, ctx, page:int, query:str, data:list, first_time:bool=False, msg:discord.Message=None):
    embed = discord.Embed.from_dict({
        'title': f'Best results for {query}',
        'color': 0x1400ff,
        'image': {'url': data[page-1]},
        'footer': {'text': f'Page {page}/{len(data)}'}
    })

    if first_time:
        msg = await ctx.send(embed=embed)
        #arrow backwards
        await msg.add_reaction('\U000025c0')
        #arrow forwards
        await msg.add_reaction('\U000025b6')
    else:
        await msg.edit(embed=embed)

    def check(reaction, u):
        #Checking if everything is right, the bot's reaction does not count
        return u == ctx.author and reaction.message.id == msg.id and u != ctx.me and(reaction.emoji == '\U000025b6' or reaction.emoji == '\U000025c0')
    try:
        reaction, u = await bot.wait_for('reaction_add', timeout=120, check=check)
    except asyncio.TimeoutError:
        try:
            await msg.remove_reaction('\U000025c0', ctx.me)
            await msg.remove_reaction('\U000025b6', ctx.me)
            return
        except:
            pass
    else:
        if reaction.emoji == '\U000025b6':
            #forward emoji
            try:
                await msg.remove_reaction('\U000025b6', ctx.author)
            except:
                pass
            if page == len(data):
                return await paginator(bot, ctx, 1, query, data, msg=msg)
            return await paginator(bot, ctx, page+1, query, data, msg=msg)

        if reaction.emoji == '\U000025c0':
            #backwards emoji
            try:
                await msg.remove_reaction('\U000025c0', ctx.author)
            except:
                pass
            if page == 1:
                return await paginator(bot, ctx, len(data), query, data, msg=msg)
            return await paginator(bot, ctx, page-1, query, data, msg=msg)

Cog = Api

def setup(client):
    client.add_cog(bl(client))
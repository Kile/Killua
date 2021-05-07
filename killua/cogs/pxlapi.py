import discord
from discord.ext import commands
import json
from killua.functions import check
import typing
import asyncio
import re
from killua.constants import CODE
from pypxl import PxlClient # My own library :sparkles:

with open('config.json', 'r') as config_file:
	config = json.loads(config_file.read())


async def validate_input(self, ctx, args): # a useful check that looks for what url to pass pxlapi

    image = None
    if isinstance(args, discord.Member):
        image = str(args.avatar_url_as(static_format='png'))
        
    if isinstance(args, str):
        if args.isdigit():
            try:
                user = await self.client.fetch_user(int(args))
                image = str(user.avatar_url_as(static_format='png'))
            except discord.NotFound:
                return None
        else:
            url = re.search(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))', args)
            if not url:
                return None 
            else:
                image = args

    if not image:
        if len(ctx.message.attachments) > 0:
            return ctx.message.attachments[0].url
            
        async for message in ctx.channel.history(limit=10):
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
        self.pxl = PxlClient(token=config["pxlapi"], stop_on_error=False, session=self.client.session)

    @check(120) # Big cooldown >_<
    @commands.command(aliases=['ej', 'emojimosaic'])
    async def emojaic(self, ctx, args:typing.Union[discord.Member, str]=None):
        #h Emoji mosaic an image; let emojis recreate an image you gave Killua! Takes in a mention, ID or image url
        #u emojaic <user/url>
        
        data = await validate_input(self, ctx, args)
        if not data:
            return await ctx.send('Invalid arguments passed! Try again')
        r = await self.pxl.emojaic([data], groupSize=6)
        if r.success:
            f = discord.File(r.convert_to_ioBytes(), filename=f'emojiaic.{r.file_type}')
            return await ctx.send(file=f)
        return await ctx.send(f':x: '+r.error)

    @check(5)
    @commands.command()
    async def flag(self, ctx, flag:str, args:typing.Union[discord.Member, str]=None):
        #h Valid flags: asexual, aromantic, bisexual, pansexual, gay, lesbian, trans, nonbinary, genderfluid, genderqueer, polysexual, austria, belgium, botswana, bulgaria, ivory, estonia, france, gabon, gambia, germany, guinea, hungary, indonesia, ireland, italy, luxembourg, monaco, nigeria, poland, russia, romania, sierraleone, thailand, ukraine, yemen
        #u flag <flag> <user/url>
        
        data = await validate_input(self, ctx, args)
        if not data:
            return await ctx.send('Invalid arguments passed! Try again')
        r = await self.pxl.flag(flag=flag, images=[data])
        if r.success:
            f = discord.File(r.convert_to_ioBytes(), filename=f"flag.{r.file_type}") # In case the image url isn't a gif this is a meh solution but...
            return await ctx.send(file=f)
        return await ctx.send(':x: '+r.error)

    @check(5)
    @commands.command()
    async def glitch(self, ctx, args:typing.Union[discord.Member, str]=None):
        #h Tranform a users pfp into a glitchy GIF!
        #u glitch <user/url>
        
        data = await validate_input(self, ctx, args)
        if not data:
            return await ctx.send('Invalid arguments passed! Try again')
        r = await self.pxl.glitch(images=[data])
        if r.success:
            f = discord.File(r.convert_to_ioBytes(), filename=f"glitch.{r.file_type}")
            return await ctx.send(file=f)
        return await ctx.send(':x: '+r.error)

    @check(10)
    @commands.command()
    async def lego(self, ctx, args:typing.Union[discord.Member, str]=None):
        #h Legofies an image
        #u lego <user/url>
        
        data = await validate_input(self, ctx, args)
        if not data:
            return await ctx.send('Invalid arguments passed! Try again')
        r = await self.pxl.lego(images=[data], scale=True, groupSize=10)
        if r.success:
            f = discord.File(r.convert_to_ioBytes(), filename=f"lego.{r.file_type}")
            return await ctx.send(file=f)
        return await ctx.send(':x: '+r.error)

    @check(3)
    @commands.command(aliases=['snap'])
    async def snapchat(self, ctx, filter:str, args:typing.Union[discord.Member, str]=None):
        #h Valid filters: dog, dog2, dog3, pig, flowers, random
        #u flag <flag> <user/url>
        
        data = await validate_input(self, ctx, args)
        if not data:
            return await ctx.send('Invalid arguments passed! Try again')
        r = await self.pxl.snapchat(filter=filter, images=[data])
        if r.success:
            f = discord.File(r.convert_to_ioBytes(), filename=f"snap.{r.file_type}")
            return await ctx.send(file=f)
        return await ctx.send(':x: '+r.error)

    @check(3)
    @commands.command(aliases=['eye'])
    async def eyes(self, ctx, t:str, args:typing.Union[discord.Member, str]=None):
        #h Valid eyes: big, black, bloodshot, blue, default, googly, green, horror, illuminati, money, pink, red, small, spinner, spongebob, white, yellow, random
        #u eyes <eye_type> <user/url>
        
        data = await validate_input(self, ctx, args)
        if not data:
            return await ctx.send('Invalid arguments passed! Try again')
        r = await self.pxl.eyes(eyes=t, images=[data])
        if r.success:
            f = discord.File(r.convert_to_ioBytes(), filename=f"eyes.{r.file_type}")
            return await ctx.send(file=f)
        return await ctx.send(':x: '+r.error)

    @check(3)
    @commands.command(aliases=['animal'])
    async def ganimal(self, ctx, args:typing.Union[discord.Member, str]=None):
        #h Turns a face into multilple animal faces
        #u ganimal <user/url>
        data = await validate_input(self, ctx, args)
        if not data:
            return await ctx.send('Invalid arguments passed! Try again')
        r = await self.pxl.ganimal(images=[data])
        if r.success:
            f = discord.File(r.convert_to_ioBytes(), filename=f"ganimal.{r.file_type}")
            return await ctx.send(file=f)
        return await ctx.send(':x: '+r.error)

    @check()
    @commands.command()
    async def nokia(self, ctx, args:typing.Union[discord.Member, str]=None):
        #h Turns a face into multilple animal faces
        #u nokia <user/url>
        data = await validate_input(self, ctx, args)
        if not data:
            return await ctx.send('Invalid arguments passed! Try again')
        d = "const url = '" + data + ";'" + CODE
        r = await self.pxl.imagescript(code=d, version="1.2.0")
        if r.success:
            f = discord.File(r.convert_to_ioBytes(), filename=f"nokia.{r.file_type}")
            return await ctx.send(file=f)
        return await ctx.send(':x: '+r.error)

    @check(3)
    @commands.command()
    async def thonkify(self, ctx, *, text:str):
        #h Turn text into thonks!
        #u thonkify <text>

        r = await self.pxl.thonkify(text=text)
        if r.success:
            f = discord.File(r.convert_to_ioBytes(), filename=f"thonk.{r.file_type}")
            return await ctx.send(file=f)
        return await ctx.send(':x: '+r.error)

    @check(5)
    @commands.command(aliases=['screen'])
    async def screenshot(self, ctx, website:str):
        #h screenshot the specified webste!
        #u screenshot <url>

        r = await self.pxl.screenshot(url=website)
        if r.success:
            f = discord.File(r.convert_to_ioBytes(), filename=f"screenshot.{r.file_type}")
            return await ctx.send(file=f)
        return await ctx.send(':x: '+r.error)

    @check(2)
    @commands.command()
    async def sonic(self, ctx, *, text:str):
        #h Let sonic say anything you want
        #u sonic <text>

        r = await self.pxl.sonic(text=text)
        if r.success:
            f = discord.File(r.convert_to_ioBytes(), filename=f"sonic.{r.file_type}")
            return await ctx.send(file=f)
        return await ctx.send(':x: '+r.error)

    @check(4)
    @commands.command(aliases=['8bit', 'blurr'])
    async def jpeg(self, ctx, args:typing.Union[discord.Member, str]=None):
        #h Did you ever want to decrease image quality? Then this is the command for you!
        #u jpeg <user/url>
        
        data = await validate_input(self, ctx, args)
        if not data:
            return await ctx.send('Invalid arguments passed! Try again')
        r = await self.pxl.jpeg(images=[data])
        if r.success:
            f = discord.File(r.convert_to_ioBytes(), filename=f"jpeg.{r.file_type}")
            return await ctx.send(file=f)

    @check(2)
    @commands.command(aliases=['g','search'])
    async def google(self, ctx, *, query:str):
        #h Get the best results for a query the web has to offer
        #u search <query>
        
        r = await self.pxl.web_search(query=query)
        if r.success:
            results = r.data['results']
            embed = discord.Embed.from_dict({
                'title': f'Results for query {query}',
                'color': 0x1400ff,
            })
            for i in range(4 if len(results) >= 4 else len(results)):
                res = results[i-1]
                embed.add_field(name='** **', value=f'__**[{res["title"]}]({res["url"]})**__\n{res["description"][:100]}...' if len(res["description"]) > 100 else res["description"], inline=False)
            await ctx.send(embed=embed)
        return await ctx.send(':x: '+r.error)

    @check(4)
    @commands.command(aliases=['image'])
    async def img(self, ctx, *,query:str):
        #h Search any image you want
        #u img <query>
        
        r = await self.pxl.image_search(query=query)
        if r.success:
            return await paginator(self.client, ctx, 1, query, r.data, True)
        else:
            return await ctx.send(':x: '+r.error)

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
        except discord.HTTPException:
            pass
    else:
        if reaction.emoji == '\U000025b6':
            #forward emoji
            try:
                await msg.remove_reaction('\U000025b6', ctx.author)
            except discord.HTTPException:
                pass
            if page == len(data):
                return await paginator(bot, ctx, 1, query, data, msg=msg)
            return await paginator(bot, ctx, page+1, query, data, msg=msg)

        if reaction.emoji == '\U000025c0':
            #backwards emoji
            try:
                await msg.remove_reaction('\U000025c0', ctx.author)
            except discord.HTTPException:
                pass
            if page == 1:
                return await paginator(bot, ctx, len(data), query, data, msg=msg)
            return await paginator(bot, ctx, page-1, query, data, msg=msg)

Cog = Api

def setup(client):
    client.add_cog(bl(client))
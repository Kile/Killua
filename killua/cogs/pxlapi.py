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

class Api(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.pxl = PxlClient(token=config["pxlapi"], stop_on_error=False, session=self.client.session)

    async def paginator(self, ctx, page:int, query:str, data:list, first_time:bool=False, msg:discord.Message=None):
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
            reaction, u = await self.client.wait_for('reaction_add', timeout=120, check=check)
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
                    return await self.paginator(ctx, 1, query, data, msg=msg)
                return await self.paginator(ctx, page+1, query, data, msg=msg)

            if reaction.emoji == '\U000025c0':
                #backwards emoji
                try:
                    await msg.remove_reaction('\U000025c0', ctx.author)
                except discord.HTTPException:
                    pass
                if page == 1:
                    return await self.paginator(ctx, len(data), query, data, msg=msg)
                return await self.paginator(ctx, page-1, query, data, msg=msg)

    async def validate_input(self, ctx, args): # a useful check that looks for what url to pass pxlapi
        image = None
        if isinstance(args, discord.Member):
            image = str(args.avatar_url_as(static_format="png"))

        if isinstance(args, discord.Emoji):
            image = str(args.url_as(static_format="png"))
            
        if isinstance(args, str):
            if args.isdigit():
                try:
                    user = await self.client.fetch_user(int(args))
                    image = str(user.avatar_url_as(static_format="png"))
                except discord.NotFound:
                    return None
            else:
                url = re.search(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))", args)
                if not url:
                    return None 
                else:
                    image = args

        if not image:
            if len(ctx.message.attachments) > 0:
                return ctx.message.attachments[0].url
                
            async for message in ctx.channel.history(limit=5):
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
            image = str(ctx.author.avatar_url_as(static_format="png"))  
        return image

    async def handle_command(self, ctx, args, function, t=None, validate:bool=True):
        if validate:
            data = await self.validate_input(ctx, args)
            if not data:
                return await ctx.send(f'Invalid arguments passed. For help with the command, use `{self.client.command_prefix(self.client, ctx.message)[2]}help command {ctx.command.name}`')
        else:
            data = args
        r = await function(data, t)
        if r.success:
            f = discord.File(r.convert_to_ioBytes(), filename=f'{ctx.command.name}.{r.file_type}')
            return await ctx.send(file=f)
        return await ctx.send(f':x: '+r.error)

    @check(120) # Big cooldown >_<
    @commands.command(aliases=['ej', 'emojimosaic'])
    async def emojaic(self, ctx, args:typing.Union[discord.Member, discord.Emoji, str]=None):
        #h Emoji mosaic an image; let emojis recreate an image you gave Killua! Takes in a mention, ID or image url
        #u emojaic <user/url>
        async def func(data, *args):
            return await self.pxl.emojaic([data], groupSize=6)
        await self.handle_command(ctx, args, func)

    @check(5)
    @commands.command()
    async def flag(self, ctx, flag:str, args:typing.Union[discord.Member, discord.Emoji, str]=None):
        #h Valid flags: asexual, aromantic, bisexual, pansexual, gay, lesbian, trans, nonbinary, genderfluid, genderqueer, polysexual, austria, belgium, botswana, bulgaria, ivory, estonia, france, gabon, gambia, germany, guinea, hungary, indonesia, ireland, italy, luxembourg, monaco, nigeria, poland, russia, romania, sierraleone, thailand, ukraine, yemen
        #u flag <flag> <user/url>
        async def func(data, flag):
            return await self.pxl.flag(flag=flag, images=[data])
        await self.handle_command(ctx, args, func, flag)

    @check(5)
    @commands.command()
    async def glitch(self, ctx, args:typing.Union[discord.Member, discord.Emoji, str]=None):
        #h Tranform a users pfp into a glitchy GIF!
        #u glitch <user/url>
        async def func(data, *args):
            return await self.pxl.glitch(images=[data])
        await self.handle_command(ctx, args, func)

    @check(10)
    @commands.command()
    async def lego(self, ctx, args:typing.Union[discord.Member, discord.Emoji, str]=None):
        #h Legofies an image
        #u lego <user/url>
        async def func(data, *args):
            return await self.pxl.glitch(images=[data], scale=True, groupSize=10)
        await self.handle_command(ctx, args, func)

    @check(3)
    @commands.command(aliases=['snap'])
    async def snapchat(self, ctx, filter:str, args:typing.Union[discord.Member, discord.Emoji, str]=None):
        #h Valid filters: dog, dog2, dog3, pig, flowers, random
        #u flag <flag> <user/url>
        async def func(data, filter):
            return await self.pxl.snapchat(filter=filter, images=[data])
        await self.handle_command(ctx, args, func, filter)

    @check(3)
    @commands.command(aliases=['eye'])
    async def eyes(self, ctx, t:str, args:typing.Union[discord.Member, discord.Emoji, str]=None):
        #h Valid eyes: big, black, bloodshot, blue, default, googly, green, horror, illuminati, money, pink, red, small, spinner, spongebob, white, yellow, random
        #u eyes <eye_type> <user/url>
        async def func(data, t):
            return await self.pxl.eyes(eyes=t, images=[data])
        await self.handle_command(ctx, args, func, t)

    @check(3)
    @commands.command(aliases=['animal'])
    async def ganimal(self, ctx, args:typing.Union[discord.Member, discord.Emoji, str]=None):
        #h Turns a face into multilple animal faces
        #u ganimal <user/url>
        async def func(data, *args):
            return await self.pxl.ganimal(images=[data])
        await self.handle_command(ctx, args, func)

    @check(4)
    @commands.command(aliases=['8bit', 'blurr'])
    async def jpeg(self, ctx, args:typing.Union[discord.Member, discord.Emoji, str]=None):
        #h Did you ever want to decrease image quality? Then this is the command for you!
        #u jpeg <user/url>
        async def func(data, *args):
            return await self.pxl.jpeg(images=[data])
        await self.handle_command(ctx, args, func)

    @check()
    @commands.command()
    async def nokia(self, ctx, args:typing.Union[discord.Member, discord.Emoji, str]=None):
        #h Turns a face into multilple animal faces
        #u nokia <user/url>
        async def func(data, *args):
            d = "const url = '" + data + ";'" + CODE
            return await self.pxl.imagescript(version="1.2.0", code=d)
        await self.handle_command(ctx, args, func)

    @check(3)
    @commands.command()
    async def thonkify(self, ctx, *, text:str):
        #h Turn text into thonks!
        #u thonkify <text>
        async def func(data, *args):
            return await self.pxl.thonkify(text=data)
        await self.handle_command(ctx, text, func, validate=False)

    @check(5)
    @commands.command(aliases=['screen'])
    async def screenshot(self, ctx, website:str):
        #h screenshot the specified webste!
        #u screenshot <url>
        async def func(data, *args):
            return await self.pxl.screenshot(url=data)
        await self.handle_command(ctx, website, func, validate=False)

    @check(2)
    @commands.command()
    async def sonic(self, ctx, *, text:str):
        #h Let sonic say anything you want
        #u sonic <text>
        async def func(data, *args):
            return await self.pxl.sonic(text=data)
        await self.handle_command(ctx, text, func, validate=False)

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
                embed.add_field(name='** **', value=f'**[__{res["title"]}__]({res["url"]})**\n{res["description"][:100]}...' if len(res["description"]) > 100 else res["description"], inline=False)
            await ctx.send(embed=embed)
        return await ctx.send(':x: '+r.error)

    @check(4)
    @commands.command(aliases=['image'])
    async def img(self, ctx, *,query:str):
        #h Search any image you want
        #u img <query>
        
        r = await self.pxl.image_search(query=query)
        if r.success:
            return await self.paginator(ctx, 1, query, r.data, True)
        else:
            return await ctx.send(':x: '+r.error)

Cog = Api

def setup(client):
    client.add_cog(bl(client))
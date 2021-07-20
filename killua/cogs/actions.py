import discord
from discord.ext import commands
import aiohttp
import random
import asyncio
from killua.checks import check
from killua.constants import ACTIONS
from killua.classes import Category

class Actions(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.session = self.client.session

    async def request_action(self, endpoint:str):

        r = await self.session.get(f"https://shiro.gg/api/images/{endpoint}")
        if r.status == 200:
            return await r.json()
        else:
            return await r.text()

    async def get_image(self, ctx, endpoint:str): # for endpoints like /wallpaper where you don't want to mention a user
        image = await self.request_action(endpoint)
        if isinstance(image, str):
            return await ctx.send(f':x: {image}')
        embed = ({
            "title": "",
            "image": {"url": image},
            "color": 0x1400ff
        })
        return await ctx.send(embed=embed)

    def generate_users(self, members:list) -> str:
        if isinstance(members, str):
            return members
        memberlist = ''
        for member in list(dict.fromkeys(members)):
            if list(dict.fromkeys(members))[-1] == member and len(list(dict.fromkeys(members))) != 1:
                memberlist = memberlist + f' and {member.name}'
            else:
                if list(dict.fromkeys(members))[0] == member:
                    memberlist = f'{member.name}'
                else:
                    memberlist = memberlist + f', {member.name}'
        return memberlist

    async def action_embed(self, endpoint:str, author, member):
        if endpoint == 'hug':
            image = {"url": random.choice(ACTIONS[endpoint]["images"])} # This might eventually be deprecated
        else:
            image = await self.request_action(endpoint)
            if isinstance(image, str):
                return f':x: {image}'
        text = random.choice(ACTIONS[endpoint]["text"]).replace("(a)", author if isinstance(author, str) else author.name).replace("(u)", self.generate_users(member))

        embed = discord.Embed.from_dict({
            "title": text,
            "image": {"url": image["url"]},
            "color": 0x1400ff
        })
        return embed

    async def no_argument(self, ctx):
        await ctx.send(f'You provided no one to {ctx.command.name}.. Should- I {ctx.command.name} you?')
        def check(m):
            return m.content.lower() == 'yes' and m.author == ctx.author
        try:
            await self.client.wait_for('message', check=check, timeout=60) 
        except asyncio.TimeoutError:
            pass
        else:
            return await self.action_embed(ctx.command.name, 'Killua', ctx.author.name)

    async def do_action(self, ctx, members=None):
        if not members:
            embed = await self.no_argument(ctx)
        elif ctx.author == members[0]:
            return await ctx.send("Sorry... you can\'t use this command on yourself")
        else:
            embed = await self.action_embed( ctx.command.name, ctx.author, self.generate_users(members))

        if isinstance(embed, str):
            return await ctx.send(embed)
        else:
            return await ctx.send(embed=embed)

    @check()
    @commands.command(extras={"category": Category.ACTIONS}, usage="hug <user>")
    async def hug(self, ctx, members: commands.Greedy[discord.Member]=None):
        """Hug a user with this command"""
        return await self.do_action(ctx, members)

    @check()
    @commands.command(extras={"category":Category.ACTIONS}, usage="pat <user>")
    async def pat(self, ctx, members: commands.Greedy[discord.Member]=None):
        """Pat a user with this command"""
        return await self.do_action(ctx, members)

    @check()
    @commands.command(extras={"category":Category.ACTIONS}, usage="poke <user>")
    async def poke(self, ctx, members: commands.Greedy[discord.Member]=None):
        """Poke a user with this command"""
        return await self.do_action(ctx, members)

    @check()
    @commands.command(extras={"category":Category.ACTIONS}, usage="tickle <usage>")
    async def tickle(self, ctx, members: commands.Greedy[discord.Member]=None):
        """Tickle a user wi- ha- hahaha- stop- haha"""
        return await self.do_action(ctx, members)

    @check()
    @commands.command(extras={"category":Category.ACTIONS}, usage="slap <user>")
    async def slap(self, ctx, members: commands.Greedy[discord.Member]=None):
        """Slap a user with this command"""
        return await self.do_action(ctx, members)

Cog = Actions

def setup(client):
    client.add_cog(Actions(client))
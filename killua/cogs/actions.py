import discord
from discord.ext import commands
import random
import asyncio
from typing import List, Union

from killua.utils.checks import check
from killua.utils.classes import Category
from killua.static.constants import ACTIONS

class Actions(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.session = self.client.session

    async def request_action(self, endpoint:str) -> Union[dict, str]:

        r = await self.session.get(f"https://purrbot.site/api/img/sfw/{endpoint}/gif")
        if r.status == 200:
            res = await r.json()

            if res["error"]:
                return res["message"]

            return res
        else:
            return await r.text()

    async def get_image(self, ctx) -> discord.Message: # for endpoints like /blush/gif where you don't want to mention a user
        image = await self.request_action(ctx.command.name)
        if isinstance(image, str):
            return await ctx.send(f':x: {image}')
        embed = discord.Embed.from_dict({
            "title": "",
            "image": {"url": image["link"]},
            "color": 0x1400ff
        })
        return await ctx.send(embed=embed)

    def generate_users(self, members:list, title:str) -> str:
        if isinstance(members, str):
            return members
        memberlist = ''
        for p, member in enumerate(members):
            if len(memberlist+member.display_name+title.replace("(a)", "").replace("(u)", "")) > 231: # embed titles have a max lentgh of 256 characters. If the name list contains too many names, stuff breaks. This prevents that and displays the other people as "and x more"
                memberlist = memberlist + f" *and {len(members)-(p+1)} more*"
                break
            if members[-1] == member and len(members) != 1:
                memberlist = memberlist + f' and {member.display_name}'
            else:
                if members[0] == member:
                    memberlist = f'{member.display_name}'
                else:
                    memberlist = memberlist + f', {member.display_name}'
        return memberlist

    async def action_embed(self, endpoint:str, author, members:List[discord.Member]) -> discord.Embed:
        if endpoint == 'hug':
            image = {"link": random.choice(ACTIONS[endpoint]["images"])} # This might eventually be deprecated for copyright reasons
        else:
            image = await self.request_action(endpoint)
            if isinstance(image, str):
                return f':x: {image}'

        text = random.choice(ACTIONS[endpoint]["text"])
        text = text.replace("<author>", "**" + (author if isinstance(author, str) else author.name) + "**").replace("<user>",  "**" + self.generate_users(members, text) + "**")

        embed = discord.Embed.from_dict({
            "title": text,
            "image": {"url": image["link"]},
            "color": 0x1400ff
        })
        return embed

    async def no_argument(self, ctx) -> Union[None, discord.Embed]:
        await ctx.send(f'You provided no one to {ctx.command.name}.. Should- I {ctx.command.name} you?')
        def check(m):
            return m.content.lower() == 'yes' and m.author == ctx.author
        try:
            await self.client.wait_for('message', check=check, timeout=60) 
        except asyncio.TimeoutError:
            pass
        else:
            return await self.action_embed(ctx.command.name, 'Killua', ctx.author.name)

    async def do_action(self, ctx, members:List[discord.Member]=None) -> Union[discord.Message, None]:
        if not members:
            embed = await self.no_argument(ctx)
            if not embed:
                return
        elif ctx.author == members[0]:
            return await ctx.send("Sorry... you can\'t use this command on yourself")
        else:
            embed = await self.action_embed(ctx.command.name, ctx.author, members)

        if isinstance(embed, str):
            return await ctx.send(embed)
        else:
            return await ctx.bot.send_message(ctx, embed=embed)

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

    @check()
    @commands.command(extras={"category": Category.ACTIONS}, usage="dance")
    async def dance(self, ctx):
        """Show off with your dance moves!"""
        return await self.get_image(ctx)

    @check()
    @commands.command(extras={"category": Category.ACTIONS}, usage="neko")
    async def neko(self, ctx):
        """uwu"""
        return await self.get_image(ctx)

    @check()
    @commands.command(extras={"category": Category.ACTIONS}, usage="smile")
    async def smile(self, ctx):
        """Show a bright smile with this command"""
        return await self.get_image(ctx)

    @check()
    @commands.command(extras={"category": Category.ACTIONS}, usage="blush")
    async def blush(self, ctx):
        """O-Oh! T-thank you for t-the compliment... You have beautiful fingernails too!"""
        return await self.get_image(ctx)

    @check()
    @commands.command(extras={"category": Category.ACTIONS}, usage="tail")
    async def tail(self, ctx):
        """Wag your tail when you're happy!"""
        return await self.get_image(ctx)

    @check()
    @commands.command(extras={"category": Category.ACTIONS}, usage="cuddle")
    async def cuddle(self, ctx, members: commands.Greedy[discord.Member]=None):
        """Snuggle up to a user and cuddle them with this command"""
        return await self.do_action(ctx, members)

Cog = Actions

def setup(client):
    client.add_cog(Actions(client))
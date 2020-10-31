import inspect
import discord
from discord.ext import commands

class devstuff(commands.Cog):

    def __init__(self, client):
        self.client = client


    @commands.command(aliases=['eval'])
    async def exec(self, ctx, *, c):
        if ctx.author.id == 606162661184372736:
            try:
                global bot
                await ctx.channel.send(f'```py\n{eval(c)}```')
            except Exception as e:
                await ctx.channel.send(str(e))

    @commands.command()
    async def source(self, ctx, name):
        if ctx.author.id == 606162661184372736 or ctx.author.id == 383790610727043085:
            func = self.client.get_command(name).callback
            code = inspect.getsource(func)
            await ctx.send('```python\n{}```'.format(code.replace('```', '``')))




def setup(client):
    client.add_cog(devstuff(client))

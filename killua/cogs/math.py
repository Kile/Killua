import discord
from discord.ext import commands
import aiohttp
from matplotlib.pyplot import figure, plot, savefig, title
from numexpr import evaluate
from numpy import linspace
from io import BytesIO
from killua.cogs.functions import custom_cooldown, blcheck

API_ADDR = 'http://api.mathjs.org/v4/'

class math(commands.Cog):

    def __init__(self, client):
        self.client = client
       


    @commands.command()
    @custom_cooldown(6)
    async def calc(self, ctx, *,args):
        if blcheck(ctx.author.id) is True:
            return
        #h Calculates any equasion you give it. For how to tell it to use a square root or more complicated functions clock [here](https://mathjs.org/docs/reference/functions.html)
    
        if not args:
            return await ctx.send(
                "Please give me something to evaluate.\n"
            
        )
        exprs = str(args).split('\n')
        request = {"expr": exprs,
               "precision": 14}
        async with aiohttp.ClientSession() as session:
            async with session.post(API_ADDR, data=json.dumps(request)) as resp:
                answer = await resp.json()
        if "error" not in answer or "result" not in answer:
            return await ctx.send(
                
                "An unknown error occurred during calculation!"
            )
        if answer["error"]:
            await ctx.reply("The following error occured while calculating:\n`{}`".format(answer["error"]))
            return
        await ctx.send("Result{}:\n```\n{}\n```".format("s" if len(exprs) > 1 else "", "\n".join(answer["result"])))



Cog = math

def setup(client):
    client.add_cog(math(client))

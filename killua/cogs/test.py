import discord
from discord.ext import commands
import aiohttp
import json


API_ADDR = 'http://api.mathjs.org/v4/'

class test(commands.Cog):

    def __init__(self, client):
        self.client = client
       


    @commands.command()
    async def calc(self, ctx):
    
    if not ctx.argd:
        return await ctx.error_reply(
            "Please give me something to evaluate.\n"
            
        )
    exprs = ctx.args.split('\n')
    request = {"expr": exprs,
               "precision": 14}
    async with aiohttp.ClientSession() as session:
        async with session.post(API_ADDR, data=json.dumps(request)) as resp:
            answer = await resp.json()
        if "error" not in answer or "result" not in answer:
            return await ctx.error_reply(
                "Sorry, could not complete your request.\n"
                "An unknown error occurred during calculation!"
            )
        if answer["error"]:
            await ctx.reply("The following error occured while calculating:\n`{}`".format(answer["error"]))
            return
        await ctx.reply("Result{}:\n```\n{}\n```".format("s" if len(exprs) > 1 else "", "\n".join(answer["result"])))


    @commands.command()
    async def test(self, ctx):
        await ctx.send('Test complete (this doesn\'t actually do anything, just means that I am trying to test some stuff!)')

Cog = test

def setup(client):
    client.add_cog(test(client))


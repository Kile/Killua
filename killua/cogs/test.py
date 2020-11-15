import discord
from discord.ext import commands

class test(commands.Cog):

    def __init__(self, client):
        self.client = client

    @commands.command()
    async def test(self, ctx):
        await ctx.send('Test complete (this doesn\'t actually do anything, just means that Killua it out of the emergency state and back!)')

Cog = test

def setup(client):
    client.add_cog(test(client))


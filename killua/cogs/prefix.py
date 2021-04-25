from discord.ext import commands
from killua.functions import custom_cooldown, blcheck
from killua.classes import Guild

class Prefix(commands.Cog):

    def __init__(self, client):
        self.client = client

    @commands.command()
    async def prefix(self, ctx, pref:str=None):
        if blcheck(ctx.author.id):
            return
        #h Change killua's prefix with this command. If you forgot your prefix, mentioning is always a prefix as well
        #u prefix <prefix>
        guild = Guild(ctx.guild.id)

        if ctx.author.guild_permissions.administrator and pref:
            guild.change_prefix(pref)
            return await ctx.send(f'Successfully changed server prefix to `{pref}`!')

        elif ctx.author.guild_permissions.administrator is False and pref:
            return await ctx.send('You need `administrator` permissions to change the server prefix!')

        await ctx.send(f'The current server prefix is `{guild.prefix}`')


Cog = Prefix

def setup(client):
    client.add_cog(Prefix(client))
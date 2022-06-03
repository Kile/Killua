from discord.ext import commands
import discord
from typing import List
from datetime import datetime

from killua.utils.checks import check
from killua.utils.classes import User, Guild #lgtm [py/unused-import]
from killua.static.enums import Category, Activities, Presences
from killua.static.cards import Card #lgtm [py/unused-import]
from killua.static.constants import teams, guilds, blacklist, presence as pr, items, updates, UPDATE_CHANNEL, GUILD_OBJECT #lgtm [py/unused-import]

class DevStuff(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.version_cache = []

    async def version_autocomplete(
        self,
        _: discord.Interaction,
        current: str,
    ) -> List[discord.app_commands.Choice[str]]:

        if self.version_cache is None:
            current = updates.find_one({'_id':'current'})
            all_versions = [x["version"] for x in updates.find_one({"_id": "log"})["past_updates"]]

            if "version" in current:
                all_versions.append(current["version"])

            self.version_cache = all_versions

        return [
            discord.app_commands.Choice(name=v, value=v)
            for v in self.version_cache if current.lower() in v.lower()
        ]

    @commands.hybrid_group()
    async def dev(self, _: commands.Context):
        """A collection of commands regarding the development side of Killua"""
        ...

    #Eval command, unnecessary with the jsk extension but useful for database stuff
    @commands.is_owner()
    @commands.command(aliases=['exec'], extras={"category":Category.OTHER}, usage="eval <code>", hidden=True, with_app_command=False)
    async def eval(self, ctx: commands.Context, *, code):
        """Standart eval command, owner restricted"""
        try:
            await ctx.channel.send(f'```py\n{eval(code)}```')
        except Exception as e:
            await ctx.channel.send(str(e))

    @commands.is_owner()
    @commands.command(extras={"category":Category.OTHER}, usage="say <text>", hidden=True, with_app_command=False)
    async def say(self, ctx: commands.Context, *, content):
        """Let's Killua say what is specified with this command. Possible abuse leads to this being restricted"""

        await ctx.message.delete()
        await ctx.send(content, reference=ctx.message.reference)

    @commands.is_owner()
    @dev.command(aliases=["publish-update", "pu"], extras={"category":Category.OTHER}, usage="publish_update <version> <text>", hidden=True)
    @discord.app_commands.guilds(GUILD_OBJECT)
    async def publish_update(self, ctx: commands.Context, version: str, *, update):
        """Allows me to publish Killua updates in a handy formart"""

        old = updates.find_one({'_id':'current'})
        old_version = old["version"] if "version" in old else "No version"

        if version in [*[old_version],*[x["version"] for x in updates.find_one({"_id": "log"})["past_updates"]]]:
            return await ctx.send("This is an already existing version")

        embed = discord.Embed.from_dict({
            'title': f'Killua Update `{old_version}` -> `{version}`',
            'description': update,
            'color': 0x1400ff,
            'footer': {'text': f'Update by {ctx.author}', 'icon_url': str(ctx.author.avatar.url)},
            'image': {'url': 'https://cdn.discordapp.com/attachments/780554158154448916/788071254917120060/killua-banner-update.png'}
        })

        data = {'version': version, 'description': update, 'published_on': datetime.utcnow(), 'published_by': ctx.author.id}
        updates.update_one({'_id': 'current'}, {'$set': data})
        updates.update_one({'_id': 'log'}, {'$push': {'past_updates': data}})
        self.version_cache.append(version)

        await ctx.send("Published new update " + f"`{old_version}` -> `{version}`", ephemeral=True)
        if self.client.is_dev: # We do not want to accidentally publish a message when testing
            return
        channel = self.client.get_channel(UPDATE_CHANNEL)
        msg = await channel.send(content= '<@&795422783261114398>', embed=embed)
        await ctx.message.delete()
        await msg.publish()

    @check()
    @dev.command(extras={"category":Category.OTHER}, usage="update <version(optional)>")
    @discord.app_commands.autocomplete(version=version_autocomplete)
    async def update(self, ctx: commands.Context, version:str=None):
        """Allows you to view current and past updates"""
        if version is None:
            data = updates.find_one({'_id': 'current'})
        else:
            d = [x for x in updates.find_one({'_id': 'log'})['past_updates'] if x['version'] == version]
            if len(d) == 0:
                return await ctx.send('Invalid version!')
            data = d[0]
            
        author = await self.client.fetch_user(data["published_by"])
        embed = discord.Embed.from_dict({
            'title': f'Infos about version `{data["version"]}`',
            'description': str(data["description"]),
            'color': 0x1400ff,
            'footer': {'icon_url': str(author.avatar.url), 'text': f'Published on {data["published_on"].strftime("%b %d %Y %H:%M:%S")}'}
        })
        await ctx.send(embed=embed)

    @commands.is_owner() 
    @dev.command(extras={"category":Category.OTHER}, usage="blacklist <user_id>", hidden=True)
    @discord.app_commands.guilds(GUILD_OBJECT)
    async def blacklist(self, ctx: commands.Context, id: int, *,reason = None):
        """Blacklisting bad people like Hisoka. Owner restricted"""
        try:
            user = self.client.get_user(id) or await self.client.fetch_user(id)
        except Exception as e:
            return await ctx.send(e)
        # Inserting the bad person into my database
        blacklist.insert_one({'id': id, 'reason': reason or "No reason provided", 'date': datetime.utcnow()})
        await ctx.send(f'Blacklisted user `{user}` for reason: {reason}')
        
    @commands.is_owner()
    @dev.command(extras={"category":Category.OTHER}, usage="whitelist <user_id>", hidden=True)
    @discord.app_commands.guilds(GUILD_OBJECT)
    async def whitelist(self, ctx: commands.Context, id: int):
        """Whitelists a user. Owner restricted"""

        try:
            user = self.client.get_user(id) or await self.client.fetch_user(id)
        except Exception as e:
            return await ctx.send(e)

        blacklist.delete_one({'id': id})
        await ctx.send(f'Successfully whitelisted `{user}`')

    @commands.is_owner()
    @dev.command(aliases=['st', 'pr', 'status'], extras={"category":Category.OTHER}, usage="pr <text>", hidden=True)
    @discord.app_commands.guilds(GUILD_OBJECT)
    async def presence(self, ctx: commands.Context, text: str, activity: Activities = None, presence: Presences = None):
        """Changes the presence of Killua. Owner restricted"""

        if text == '-rm':
            pr.update_many({}, {'$set': {'text': None, 'activity': None, 'presence': None}})
            await ctx.send('Done! reset Killua\'s presence', ephemeral=True)
            return await self.client.update_presence()

        pr.update_many({}, {'$set': {'text': text, 'presence': presence.name if presence else None, 'activity': activity.name if activity else None}})
        await self.client.update_presence()
        await ctx.send(f'Successfully changed Killua\'s status to `{text}`! (I hope people like it >-<)', ephemeral=True)



Cog = DevStuff

async def setup(client):
    await client.add_cog(DevStuff(client))

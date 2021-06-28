import discord 
from discord.ext import commands
from pymongo import MongoClient
from datetime import datetime
import math
import asyncio
from killua.classes import Guild
from killua.constants import guilds

class Tag():
    def __init__(self, guild_id:int, tag_name:str):
        guild = guilds.find_one({'id': guild_id})
        if guild is None:
            self.found = False
            return
        if not 'tags' in guild:
            self.found = False
            return

        self.tags:list = guild['tags']
        if not tag_name.lower() in [r[0] for r in self.tags]:
            self.found = False
            return

        indx:int = [r[0] for r in self.tags].index(tag_name.lower())
        tag = self.tags[indx]

        self.guild_id = guild_id
        self.found = True
        self.name = tag[1]['name'] # By saving it that way it is non case sensitive when searching but keeps case sensitivity when displayed
        self.created_at = tag[1]['created_at']
        self.owner = tag[1]['owner']
        self.content = tag[1]['content']
        self.uses = tag[1]['uses']

    def update(self, new_content):
        indx:int = [r[0] for r in self.tags].index(self.name.lower())
        self.tags[indx][1]['content'] = new_content
        guilds.update_one({'id': self.guild_id}, {'$set': {'tags': self.tags}})
        return 

    def delete(self):
        indx:int = [r[0] for r in self.tags].index(self.name.lower())
        self.tags.remove(self.tags[indx])
        guilds.update_one({'id': self.guild_id}, {'$set': {'tags': self.tags}})
        return
    
    def add_use(self):
        indx:int = [r[0] for r in self.tags].index(self.name.lower())
        self.tags[indx][1]['uses'] = self.tags[indx][1]['uses']+1
        guilds.update_one({'id': self.guild_id}, {'$set': {'tags': self.tags}})
        return

class Member():

    def __init__(self, user_id:int, guild_id:int):
        guild = guilds.find_one({'id': guild_id})

        if guild is None:
            self.has_tags = False
            return

        if not 'tags' in guild:
            self.has_tags = False
            return

        tags:list = guild['tags']
        if not user_id in [r[1]['owner'] for r in tags]:
            self.has_tags = False
            return

        owned_tags:list = []
        for x in tags:
            owned_tags.append([x[1]['name'], [x[1]['uses']]])

        self.tags = owned_tags
        self.has_tags = True

class Tags(commands.Cog):

    def __init__(self, client):
        self.client = client

    @commands.group()
    async def tag(self, ctx):
        if not Guild(ctx.guild.id).is_premium:
            await ctx.send('This command group is currently only a premium feature. To enable your guild to use it, become a Patreon (https://patreon.com/kilealkuri) and join the support server')
            raise Exception("tag command used on non premium guild")
            
        if not ctx.guild:
            await ctx.send('Not usable in dms')
            raise Exception("tag command used on non premium guild")

    @tag.command()
    async def create(self, ctx, *, tag_name:str):
        #h Create a tag with this command! After first using the command it will ask you for the content of the tag
        #u tag create <tag_name>
        guild = guilds.find_one({'id': ctx.guild.id})
        member = Member(ctx.author.id, ctx.guild.id)
        if not Tag(ctx.guild.id, tag_name).found is False:
            tag = Tag(ctx.guild.id, tag_name)
            user = self.client.fetch_user(tag.owner)
            return await ctx.send(f'This tag already exists and is owned by {user}')

        if 'tags' in guild:
            tags = guild['tags']
        else:
            tags = []

        if len(tags) >= 50:
            return await ctx.send('Your server has reached the limit of tags!')
        if member.has_tags:
            if len(member.tags) > 15:
                return await ctx.send('You can\'t own more than 15 tags on a guild, consider deleting one')
        if len(tag_name) > 30:
            return await ctx.send('The tag title has too many characters!')
        
        ms = await ctx.send('What should the description of the tag be?')

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        try:
            msg = await self.client.wait_for('message', check=check, timeout=120)
        except asyncio.TimeoutError:
            await ms.delete()
            return await ctx.send('Too late, aborting...', delete_after=5)
        else:
            await ms.delete()
            await msg.delete()
            if len(msg.content) > 2000:
                return await ctx.send('Too many characters!')
            tags.append([tag_name.lower(), {'name': tag_name, 'created_at': datetime.now(), 'owner': ctx.author.id, 'content': msg.content, 'uses': 0}])
            guilds.update_one({'id': ctx.guild.id}, {'$set': {'tags': tags}})
            return await ctx.send(f'Sucesfully created tag `{tag_name}`')

    @tag.command()
    async def delete(self, ctx, *, tag_name:str):
        #h Delete a tag you own with this command or any tag if you have manage build permissions
        #u tag delete <tag_name>
        tag = Tag(ctx.guild.id, tag_name)

        if tag is None:
            return await ctx.send('A tag with that name does not exist!')

        if ctx.channel.permissions_for(ctx.author).manage_guild is False and not ctx.author.id == tag.owner:
            return await ctx.send('You need to be tag owner or have the `manage server` permission to delete tags!')

        tag.delete()
        await ctx.send(f'Sucessfully deleted tag `{tag.name}`')

    @tag.command()
    async def edit(self, ctx, *, tag_name:str):
        #h Chose wrong tag description? Edit a tag's description with this command (only if you own it)
        #u tag edit <tag_name>
        tag = Tag(ctx.guild.id, tag_name)

        if tag.found is False:
            return await ctx.send('A tag with that name does not exist!')

        if not ctx.author.id == tag.owner:
            return await ctx.send('You need to be tag owner to edit this tag!')

        ms = await ctx.send('What would you like the new description to be?')

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        try:
            msg = await self.client.wait_for('message', check=check, timeout=120)
        except asyncio.TimeoutError:
            await ms.delete()
            return await ctx.send('Too late, aborting...', delete_after=5)
        else:
            await ms.delete()
            await msg.delete()
            tag.update(msg.content)
            return await ctx.send(f'Sucesfully updated tag `{tag.name}`')

    @tag.command()
    async def get(self, ctx, *, tag_name:str):
        #h Get the content of any tag
        #u tag get <tag_name>
        tag = Tag(ctx.guild.id, tag_name)
        if tag.found is False:
            return await ctx.send('This tag doesn\'t exist')
        tag.add_use()
        return await ctx.send(tag.content, allowed_mentions=discord.AllowedMentions.none(), reference=ctx.message)
    
    @tag.command()
    async def info(self, ctx, *, tag_name:str):
        #h Get information about any tag
        #u tag info <tag_name>
        tag = Tag(ctx.guild.id, tag_name.lower())
        if tag.found is False:
            return await ctx.send('There is no tag with that name!')
        guild = guilds.find_one({'id': ctx.guild.id})
        owner = await self.client.fetch_user(tag.owner)
        s = sorted(zip([x[0] for x in guild['tags']], [x[1]['uses'] for x in guild['tags']]))
        rank = [x[0] for x in s].index(tag_name.lower())+1
        embed = discord.Embed.from_dict({
            'title': f'Information about tag "{tag.name}"',
            'description': f'**Tag owner:** `{str(owner)}`\n\n**Created on**: `{tag.created_at.strftime("%b %d %Y %H:%M:%S")}`\n\n**Uses:** `{tag.uses}`\n\n**Tag rank:** `{rank}`',
            'color': 0x1400ff,
            'thumbnail': {'url': str(owner.avatar_url)}
        })
        await ctx.send(embed=embed)
    
    @tag.command(aliases=['list'])
    async def l(self, ctx, page:int=1):
        #h Get a list of tags on the current server sorted by uses
        #u tag list
        guild = guilds.find_one({'id': ctx.guild.id})
        if not 'tags' in guild:
            return await ctx.send('Seems like this server doesn\'t have any tags!')

        s = sorted(zip([x[1]['name'] for x in guild['tags']], [x[1]['uses'] for x in guild['tags']]))

        if len(guild['tags']) == 0:
            return await ctx.send('Seems like this server doesn\'t have any tags!')
    
        return await paginator(self, ctx, [f'Tag `{n}` with `{u}` uses' for n, u in s], page if page and page > 0 and page <= len(guild['tags']) else 1, guild=ctx.guild, first_time=True)

    @tag.command()
    async def user(self, ctx, user:discord.Member, amount:int=None):
        #h Get the tags a user own sorted by uses
        #u tag user <user>
        member = Member(user.id, ctx.guild.id)
        if member.has_tags is False:
            return await ctx.send('This user currently does not have any tags!')
        z = sorted(zip([x[1] for x in member.tags], [x[0] for x in member.tags]), reverse=True)
        g:list = []
        for i in z:
            uses, name = i
            g.append(f'`{name}` with `{uses}` uses')
        
        return await paginator(self, ctx, g, 1, user, first_time=True)

async def paginator(self, ctx, content:list, page:int, user:discord.Member=None, guild:discord.Guild=None, msg=None, first_time=False):
    
    max_pages = math.ceil(len(content)/10)

    if len(content)-page*10+10 > 10:
        final_tags = content[page*10-10:-(len(content)-page*10)]
    elif len(content)-page*10+10 <= 10:
        final_tags = content[-(len(content)-page*10+10):]

    embed = discord.Embed.from_dict({
        'title': f'Top tags owned by {user.name}' if user else f'Top tags of guild {guild.name}',
        'description': '\n'.join(final_tags),
        'color': 0x1400ff,
        'thumbnail': {'url': str(user.avatar_url) if user else str(guild.icon_url)}
    })

    if first_time:
        msg = await ctx.send(embed=embed)
        #ultra backwards arrow
        await msg.add_reaction('\U000023ea')
        #arrow backwards
        await msg.add_reaction('\U000025c0')
        #stop button 
        await msg.add_reaction('\U000023f9')
        #arrow forwards
        await msg.add_reaction('\U000025b6')
        #ultra forwards arrow
        await msg.add_reaction('\U000023e9')
    else:
        await msg.edit(embed=embed)

    def check(reaction, u):
        #Checking if everything is right, the bot's reaction does not count
        return u == ctx.author and reaction.message.id == msg.id and u != ctx.me and reaction.emoji in ['\U000023e9', '\U000025b6', '\U000023f9', '\U000025c0', '\U000023ea']
    try:
        reaction, u = await self.client.wait_for('reaction_add', timeout=120, check=check)
    except asyncio.TimeoutError:
        try:
            await msg.remove_reaction('\U000023ea', ctx.me)
            await msg.remove_reaction('\U000025c0', ctx.me)
            await msg.remove_reaction('\U000023f9', ctx.me)
            await msg.remove_reaction('\U000025b6', ctx.me)
            await msg.remove_reaction('\U000023e9', ctx.me)
            return
        except discord.HTTPException:
            pass
        return
    else:
        if reaction.emoji == '\U000023e9':
            #ultra forward emoji
            try:
                await msg.remove_reaction('\U000023e9', ctx.author)
            except discord.HTTPException:
                pass
            return await paginator(self, ctx, content, max_pages, user, guild, msg)

        if reaction.emoji == '\U000025b6':
            #forward emoji
            try:
                await msg.remove_reaction('\U000025b6', ctx.author)
            except discord.HTTPException:
                pass
            return await paginator(self, ctx, content, 1 if page == max_pages else page+1, user, guild, msg)

        if reaction.emoji in ['\U000023f9', '\U0000fe0f']:
            #stop button
            await msg.delete()
            return

        if reaction.emoji == '\U000025c0':
            #backwards emoji
            try:
                await msg.remove_reaction('\U000025c0', ctx.author)
            except discord.HTTPException:
                pass
            return await paginator(self, ctx, content, max_pages if page == 1 else page-1, user, guild, msg)

        if reaction.emoji == '\U000023ea':
            #ultra backwards emoji
            try:
                await msg.remove_reaction('\U000023ea', ctx.author)
            except discord.HTTPException:
                pass
            return await paginator(self, ctx, content, 1, user, guild, msg)

Cog = Tags

def setup(client):
    client.add_cog(Tags(client))

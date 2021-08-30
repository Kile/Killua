import discord 
from discord.ext import commands
from datetime import datetime
import math
import asyncio
from killua.classes import Guild, Category
from killua.constants import guilds
from killua.checks import check
from killua.paginator import Paginator

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

    def update(self, new_content) -> None:
        indx:int = [r[0] for r in self.tags].index(self.name.lower())
        self.tags[indx][1]['content'] = new_content
        guilds.update_one({'id': self.guild_id}, {'$set': {'tags': self.tags}})

    def delete(self) -> None:
        indx:int = [r[0] for r in self.tags].index(self.name.lower())
        self.tags.remove(self.tags[indx])
        guilds.update_one({'id': self.guild_id}, {'$set': {'tags': self.tags}})
    
    def add_use(self) -> None:
        indx:int = [r[0] for r in self.tags].index(self.name.lower())
        self.tags[indx][1]['uses'] = self.tags[indx][1]['uses']+1
        guilds.update_one({'id': self.guild_id}, {'$set': {'tags': self.tags}})

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

    def _build_embed(self, ctx:commands.Context, content:list, page:int, user:discord.User=None) -> discord.Embed:

        if len(content)-page*10+10 > 10:
            final_tags = content[page*10-10:-(len(content)-page*10)]
        elif len(content)-page*10+10 <= 10:
            final_tags = content[-(len(content)-page*10+10):]

        embed = discord.Embed.from_dict({
            'title': f'Top tags owned by {user.name}' if user else f'Top tags of guild {ctx.guild.name}',
            'description': '\n'.join(final_tags),
            'color': 0x1400ff,
            'thumbnail': {'url': str(user.avatar.url) if user else str(ctx.guild.icon.url)}
            })
        return embed

    @commands.guild_only()
    @check()
    @commands.group(hidden=True, extras={"category":Category.TAGS})
    async def tag(self, ctx):
        if not Guild(ctx.guild.id).is_premium:
            view = discord.ui.View()
            view.add_item(discord.ui.Button(style=discord.ButtonStyle.grey, label="Premium", url="https://patreon.com/kilealkuri"))
            await ctx.send("This command group is currently only a premium feature. To enable your guild to use it, become a Patreon!", view=view)
            raise commands.CommandNotFound() # I raise this error because it is the only one I ignore in the error handler. Hacky but whatever

    @tag.command(extras={"category":Category.TAGS}, usage="create <tag_name>")
    async def create(self, ctx, *, tag_name:str):
        """Create a tag with this command! After first using the command it will ask you for the content of the tag"""
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
            return await ctx.send(f'Successfully created tag `{tag_name}`')

    @tag.command(extras={"category":Category.TAGS}, usage="delete <tag_name>")
    async def delete(self, ctx, *, tag_name:str):
        """Delete a tag you own with this command or any tag if you have manage build permissions"""
        tag = Tag(ctx.guild.id, tag_name)

        if tag is None:
            return await ctx.send('A tag with that name does not exist!')

        if ctx.channel.permissions_for(ctx.author).manage_guild is False and not ctx.author.id == tag.owner:
            return await ctx.send('You need to be tag owner or have the `manage server` permission to delete tags!')

        tag.delete()
        await ctx.send(f'Successfully deleted tag `{tag.name}`')

    @tag.command(extras={"category":Category.TAGS}, usage="edit <tag_name>")
    async def edit(self, ctx, *, tag_name:str):
        """Chose wrong tag description? Edit a tag's description with this command (only if you own it)"""
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
            return await ctx.send(f'Successfully updated tag `{tag.name}`')

    @tag.command(extras={"category":Category.TAGS}, usage="get <tag_name>")
    async def get(self, ctx, *, tag_name:str):
        """Get the content of any tag"""
        tag = Tag(ctx.guild.id, tag_name)
        if tag.found is False:
            return await ctx.send('This tag doesn\'t exist')
        tag.add_use()
        return await ctx.send(tag.content, allowed_mentions=discord.AllowedMentions.none(), reference=ctx.message.reference or ctx.message)
    
    @tag.command(extras={"category":Category.TAGS}, usage="info <tag_name>")
    async def info(self, ctx, *, tag_name:str):
        """Get information about any tag"""
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
            'thumbnail': {'url': str(owner.avatar.url)}
        })
        await ctx.send(embed=embed)
    
    @tag.command(aliases=['list'], extras={"category":Category.TAGS}, usage="list")
    async def l(self, ctx, p:int=1):
        """Get a list of tags on the current server sorted by uses"""
        guild = guilds.find_one({'id': ctx.guild.id})
        if not 'tags' in guild:
            return await ctx.send('Seems like this server doesn\'t have any tags!')

        s = sorted(zip([x[1]['name'] for x in guild['tags']], [x[1]['uses'] for x in guild['tags']]))

        if len(guild['tags']) == 0:
            return await ctx.send('Seems like this server doesn\'t have any tags!')

        if math.ceil(len(guild["tags"])/10) < p:
            return await ctx.send("Invalid page")

        tags = [f'Tag `{n}` with `{u}` uses' for n, u in s]

        if len(guild['tags']) <= 10:
            return await ctx.send(embed=self._build_embed(ctx, tags, p))

        def make_embed(page, embed, pages):
            return self._build_embed(ctx, tags, page)
    
        await Paginator(ctx, tags, func=make_embed, max_pages=math.ceil(len(tags)/10)).start()

    @tag.command(extras={"category":Category.TAGS}, usage="user <user>")
    async def user(self, ctx, user:discord.Member, amount:int=None):
        """Get the tags a user own sorted by uses"""
        member = Member(user.id, ctx.guild.id)
        if member.has_tags is False:
            return await ctx.send('This user currently does not have any tags!')
        z = sorted(zip([x[1] for x in member.tags], [x[0] for x in member.tags]), reverse=True)
        g:list = []
        for i in z:
            uses, name = i
            g.append(f'`{name}` with `{uses}` uses')
        if len(g) <= 10:
            return await ctx.send(embed=self._build_embed(ctx, g, 1, user))

        def make_embed(page, embed, pages):
            return self._build_embed(ctx, pages, page, user)

        await Paginator(ctx, g, func=make_embed, max_pages=math.ceil(len(g)/10)).start()

Cog = Tags

def setup(client):
    client.add_cog(Tags(client))

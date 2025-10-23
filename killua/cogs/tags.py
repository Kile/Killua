import discord
from discord.ext import commands
from datetime import datetime
from typing import List, Optional
import math
from dataclasses import dataclass, field

from killua.bot import BaseBot
from killua.static.constants import DB
from killua.static.enums import Category
from killua.utils.classes import Guild
from killua.utils.checks import check
from killua.utils.paginator import Paginator


@dataclass
class Tag:
    found: bool
    tags: list = field(default_factory=list)
    name: Optional[str] = None
    created_at: Optional[datetime] = None
    owner: Optional[int] = None
    content: Optional[str] = None
    uses: Optional[int] = None
    guild_id: Optional[int] = None
    indx: Optional[int] = None

    @classmethod
    async def new(cls, guild_id: int, tag_name: str) -> "Tag":
        raw = await DB.guilds.find_one({"id": guild_id})
        if raw is None:
            return Tag(found=False)
        if "tags" not in raw:
            return Tag(found=False)
        if tag_name.lower() not in [r[0] for r in raw["tags"]]:
            return Tag(found=False)

        indx = [r[0] for r in raw["tags"]].index(tag_name.lower())
        tag = raw["tags"][indx]
        return Tag(
            found=True,
            indx=indx,
            guild_id=guild_id,
            tags=raw["tags"],
            # By saving it that way it is non case sensitive when searching but keeps case sensitivity when displayed
            name=tag[1]["name"],
            created_at=tag[1]["created_at"],
            owner=tag[1]["owner"],
            content=tag[1]["content"],
            uses=tag[1]["uses"],
        )

    async def update(self, new_content) -> None:
        self.tags[self.indx][1]["content"] = new_content
        await DB.guilds.update_one({"id": self.guild_id}, {"$set": {"tags": self.tags}})

    async def delete(self) -> None:
        self.tags.pop(self.indx)
        await DB.guilds.update_one({"id": self.guild_id}, {"$set": {"tags": self.tags}})

    async def add_use(self) -> None:
        self.tags[self.indx][1]["uses"] = self.tags[self.indx][1]["uses"] + 1
        await DB.guilds.update_one({"id": self.guild_id}, {"$set": {"tags": self.tags}})

    async def transfer(self, to: int) -> None:
        """Transfers the ownership of a tag to the new id"""
        self.tags[self.indx][1]["owner"] = to
        await DB.guilds.update_one({"id": self.guild_id}, {"$set": {"tags": self.tags}})


@dataclass
class Member:
    has_tags: bool
    tags: list = field(default_factory=list)

    @classmethod
    async def new(cls, user_id: int, guild_id: int) -> "Member":
        raw = await DB.guilds.find_one({"id": guild_id})
        if raw is None:
            return Member(has_tags=False)
        if "tags" not in raw:
            return Member(has_tags=False)

        tags: list = raw["tags"]
        if user_id not in [r[1]["owner"] for r in tags]:
            return Member(has_tags=False)

        owned_tags: list = []
        for x in tags:
            owned_tags.append([x[1]["name"], [x[1]["uses"]]])

        return Member(has_tags=True, tags=owned_tags)


class Tags(commands.Cog):

    def __init__(self, client: BaseBot):
        self.client = client
        self._init_menus()

    def _init_menus(self) -> None:
        menus = []
        menus.append(
            discord.app_commands.ContextMenu(
                name="tags",
                callback=self.client.callback_from_command(self.user, message=False),
                allowed_installs=discord.app_commands.AppInstallationType(
                    guild=True, user=True
                ),
                allowed_contexts=discord.app_commands.AppCommandContext(guild=True),
            )
        )

        for menu in menus:
            self.client.tree.add_command(menu)

    def _build_embed(
        self, ctx: commands.Context, content: list, page: int, user: discord.User = None
    ) -> discord.Embed:

        if len(content) - page * 10 + 10 > 10:
            final_tags = content[page * 10 - 10 : -(len(content) - page * 10)]
        elif len(content) - page * 10 + 10 <= 10:
            final_tags = content[-(len(content) - page * 10 + 10) :]

        embed = discord.Embed.from_dict(
            {
                "title": (
                    f"Top tags owned by {user.name}"
                    if user
                    else f"Top tags of guild {ctx.guild.name}"
                ),
                "description": "\n".join(final_tags),
                "color": 0x3E4A78,
                "thumbnail": {
                    "url": str(user.avatar.url) if user else str(ctx.guild.icon.url)
                },
            }
        )
        return embed

    async def tag_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> List[discord.app_commands.Choice[str]]:
        """Returns a list of tags that match the message."""
        guild = await DB.guilds.find_one({"id": interaction.guild.id})
        if "tags" not in guild:
            return []

        tags = guild["tags"]

        return [
            discord.app_commands.Choice(name=t[1]["name"], value=t[1]["name"])
            for t in tags
            if current.lower() in t[0] or current in t[0]
        ][:25]

    @commands.hybrid_group(hidden=True, extras={"category": Category.TAGS})
    async def tag(self, _: commands.Context):
        """Tag commands. Only usable in premium guilds."""
        ...

    @check()
    @commands.guild_only()
    @tag.command(
        extras={"category": Category.TAGS, "id": 92}, usage="create <tag_name>"
    )
    @discord.app_commands.describe(name="The name of the tag you want to create")
    async def create(self, ctx: commands.Context, *, name: str):
        """Create a tag with this command"""
        guild = await DB.guilds.find_one({"id": ctx.guild.id})
        member = await Member.new(ctx.author.id, ctx.guild.id)

        if (tag := await Tag.new(ctx.guild.id, name)).found is not False:
            user = ctx.guild.get_member(tag.owner)
            return await ctx.send(
                f"This tag already exists and is owned by {user or '`user left`'}", allowed_mentions=discord.AllowedMentions.none()
            )

        if "tags" in guild:
            tags = guild["tags"]
        else:
            tags = []

        if len(tags) >= 10 and not (await Guild.new(ctx.guild.id)).is_premium:
            return await ctx.send(
                "Your server has reached the limit of tags! Buy premium to up to 250 tags!"
            )

        if member.has_tags:
            if len(member.tags) > 50:
                return await ctx.send(
                    "You can't own more than 15 tags on a guild, consider deleting one"
                )

        if len(name) > 30:
            return await ctx.send("The tag title has too many characters!")

        content = await self.client.get_text_response(
            ctx,
            "What should the description of the tag be?",
            timeout=600,
            min_length=1,
            max_length=2000,
        )
        if not content:
            return

        if len(content) > 2000:
            return await ctx.send("Too many characters!")

        tags.append(
            [
                name.lower(),
                {
                    "name": name,
                    "created_at": datetime.now(),
                    "owner": ctx.author.id,
                    "content": content,
                    "uses": 0,
                },
            ]
        )
        await DB.guilds.update_one({"id": ctx.guild.id}, {"$set": {"tags": tags}})

        return await ctx.send(f"Successfully created tag `{name}`", allowed_mentions=discord.AllowedMentions.none())

    @check()
    @commands.guild_only()
    @tag.command(
        extras={"category": Category.TAGS, "id": 93}, usage="delete <tag_name>"
    )
    @discord.app_commands.describe(name="The name of the tag you want to delete")
    @discord.app_commands.autocomplete(name=tag_autocomplete)
    async def delete(self, ctx: commands.Context, *, name: str):
        """Delete a tag you own with this command or any tag if you have manage guild permissions"""
        tag = await Tag.new(ctx.guild.id, name)

        if tag.found is False:
            return await ctx.send("A tag with that name does not exist!")

        if (
            ctx.channel.permissions_for(ctx.author).manage_guild is False
            and ctx.author.id != tag.owner
        ):
            return await ctx.send(
                "You need to be tag owner or have the `manage server` permission to delete tags!"
            )

        await tag.delete()
        await ctx.send(f"Successfully deleted tag `{tag.name}`", allowed_mentions=discord.AllowedMentions.none())

    @check()
    @commands.guild_only()
    @tag.command(extras={"category": Category.TAGS, "id": 94}, usage="edit <tag_name>")
    @discord.app_commands.describe(name="The name of the tag you want to edit")
    @discord.app_commands.autocomplete(name=tag_autocomplete)
    async def edit(self, ctx: commands.Context, *, name: str):
        """Chose wrong tag description? Edit a tag's description with this command"""
        tag = await Tag.new(ctx.guild.id, name)

        if tag.found is False:
            return await ctx.send("A tag with that name does not exist!")

        if ctx.author.id != tag.owner:
            return await ctx.send("You need to be tag owner to edit this tag!")

        content = await self.client.get_text_response(
            ctx,
            "What should the new description to be?",
            timeout=600,
            min_length=1,
            max_length=2000,
        )

        if len(content) > 2000:
            return await ctx.send("Too many characters!")

        await tag.update(content)
        return await ctx.send(f"Successfully updated tag `{tag.name}`", allowed_mentions=discord.AllowedMentions.none())

    @check()
    @commands.guild_only()
    @tag.command(
        extras={"category": Category.TAGS, "id": 95}, usage="transfer <user> <tag_name>"
    )
    @discord.app_commands.describe(
        user="The user to tranfer the tag ownership to",
        name="The name of the tag you want to transfer",
    )
    @discord.app_commands.autocomplete(name=tag_autocomplete)
    async def transfer(self, ctx: commands.Context, user: discord.Member, *, name: str):
        """Transfer a tag you own to another user"""
        tag = await Tag.new(ctx.guild.id, name)

        if tag.found is False:
            return await ctx.send(
                "A tag with that name does not exist!", ephemeral=True
            )

        if ctx.author.id != tag.owner:
            return await ctx.send(
                "You need to be tag owner to transfer this tag!", ephemeral=True
            )

        await tag.transfer(user.id)
        return await ctx.send(
            f"Successfully transferred tag `{tag.name}` to {user}",
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @check()
    @commands.guild_only()
    @tag.command(extras={"category": Category.TAGS, "id": 96}, usage="get <tag_name>")
    @discord.app_commands.describe(name="The name of the tag you want look at")
    @discord.app_commands.autocomplete(name=tag_autocomplete)
    async def get(self, ctx: commands.Context, *, name: str):
        """Get the content of any tag"""
        tag = await Tag.new(ctx.guild.id, name)
        if tag.found is False:
            return await ctx.send("This tag doesn't exist")
        await tag.add_use()
        return await ctx.send(
            tag.content,
            allowed_mentions=discord.AllowedMentions.none(),
            reference=ctx.message.reference or ctx.message,
        )

    @check()
    @commands.guild_only()
    @tag.command(extras={"category": Category.TAGS, "id": 97}, usage="info <tag_name>")
    @discord.app_commands.describe(name="The name of the tag to get info about")
    @discord.app_commands.autocomplete(name=tag_autocomplete)
    async def info(self, ctx: commands.Context, *, name: str):
        """Get information about any tag"""
        tag = await Tag.new(ctx.guild.id, name.lower())
        if tag.found is False:
            return await ctx.send("There is no tag with that name!")

        guild = await DB.guilds.find_one({"id": ctx.guild.id})
        owner = self.client.get_user(tag.owner) or await self.client.fetch_user(
            tag.owner
        )

        s = sorted(
            zip([x[0] for x in guild["tags"]], [x[1]["uses"] for x in guild["tags"]])
        )
        rank = [x[0] for x in s].index(name.lower()) + 1
        embed = discord.Embed.from_dict(
            {
                "title": f'Information about tag "{tag.name}"',
                "description": f"**Tag owner:** `{str(owner)}`\n\n**Created on**: <t:{int(tag.created_at.timestamp())}>\n\n**Uses:** `{tag.uses}`\n\n**Tag rank:** `{rank}`",
                "color": 0x3E4A78,
                "thumbnail": {"url": str(owner.avatar.url)},
            }
        )
        await ctx.send(embed=embed)

    @check()
    @commands.guild_only()
    @tag.command(
        aliases=["l"], extras={"category": Category.TAGS, "id": 98}, usage="list"
    )
    @discord.app_commands.describe(page="The page of the tag list you want to view")
    async def list(self, ctx: commands.Context, page: int = 1):
        """Get a list of tags on the current server sorted by uses"""
        guild = await DB.guilds.find_one({"id": ctx.guild.id})
        if "tags" not in guild:
            return await ctx.send("Seems like this server doesn't have any tags!")

        s = sorted(
            zip(
                [x[1]["name"] for x in guild["tags"]],
                [x[1]["uses"] for x in guild["tags"]],
            )
        )

        if len(guild["tags"]) == 0:
            return await ctx.send("Seems like this server doesn't have any tags!")

        if math.ceil(len(guild["tags"]) / 10) < page:
            return await ctx.send("Invalid page")

        tags = [f"Tag `{n}` with `{u}` uses" for n, u in s]

        if len(guild["tags"]) <= 10:
            return await ctx.send(embed=self._build_embed(ctx, tags, page))

        def make_embed(page, *_):
            return self._build_embed(ctx, tags, page)

        await Paginator(
            ctx, tags, func=make_embed, max_pages=math.ceil(len(tags) / 10)
        ).start()

    @check()
    @commands.guild_only()
    @tag.command(extras={"category": Category.TAGS, "id": 99}, usage="user <user>")
    @discord.app_commands.describe(user="User you want to see tags of")
    async def user(self, ctx: commands.Context, user: discord.Member):
        """Get the tags a user own sorted by uses"""
        if hasattr(
            ctx, "invoked_by_context_menu"
        ):  # user is a string if invoked by a context menu
            user = await self.client.find_user(ctx, user)

        member = await Member.new(user.id, ctx.guild.id)
        if member.has_tags is False:
            return await ctx.send(
                "This user currently does not have any tags!", ephemeral=True
            )
        z = sorted(
            zip([x[1] for x in member.tags], [x[0] for x in member.tags]), reverse=True
        )
        g: list = []
        for i in z:
            uses, name = i
            g.append(f"`{name}` with `{uses}` uses")
        if len(g) <= 10:
            return await ctx.send(
                embed=self._build_embed(ctx, g, 1, user),
                ephemeral=hasattr(ctx, "invoked_by_context_menu"),
            )

        def make_embed(page, _, pages):
            return self._build_embed(ctx, pages, page, user)

        await Paginator(
            ctx,
            g,
            func=make_embed,
            max_pages=math.ceil(len(g) / 10),
            ephemeral=hasattr(ctx, "invoked_by_context_menu"),
        ).start()


Cog = Tags

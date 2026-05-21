from ..types import *
from ...utils.classes import *
from ..testing import Testing, test
from ...cogs.tags import Tags, Tag
from ...utils.classes.guild import Guild as KilluaGuild
from ...utils.test_db import TestingDatabase
from ..types.permissions import Permissions

from datetime import datetime
from unittest.mock import patch

from ..harnesses import (
    assert_embed_title,
    embed_at,
    embed_footer_page,
    press_paginator_button,
)


class TestingTags(Testing):
    requires_command = True

    _menus_registered = False

    def __init__(self):
        if not TestingTags._menus_registered:
            TestingTags._menus_registered = True
        else:
            Tags._init_menus = lambda self: None
        super().__init__(cog=Tags)
        self.base_channel._has_permission = Permissions(manage_guild=True)

    def _seed_guild(self, tags=None):
        """Seed KilluaGuild cache and mock DB. tags=None omits the key from the DB doc."""
        guild_id = self.base_guild.id
        tag_list = tags if tags is not None else []

        KilluaGuild.cache.pop(guild_id, None)
        KilluaGuild.cache[guild_id] = KilluaGuild(
            id=guild_id, prefix="k!", tags=tag_list
        )

        coll = "guilds"
        TestingDatabase.db.setdefault(coll, [])
        TestingDatabase.db[coll] = [
            d for d in TestingDatabase.db[coll] if d.get("id") != guild_id
        ]
        doc = {
            "_id": f"guild_{guild_id}",
            "id": guild_id,
            "prefix": "k!",
            "badges": [],
            "approximate_member_count": self.base_guild.member_count,
        }
        if tags is not None:
            doc["tags"] = tag_list
        TestingDatabase.db[coll].append(doc)

    def _make_tag(self, name="test", content="test content", owner=None, uses=0):
        return {
            "name": name,
            "content": content,
            "owner": owner or self.base_author.id,
            "created_at": datetime.now(),
            "uses": uses,
        }


class Get(TestingTags):

    def __init__(self):
        super().__init__()

    @test
    async def tag_not_found(self) -> None:
        self._seed_guild(tags=[])
        await self.command(self.cog, self.base_context, name="nonexistent")
        assert (
            self.base_context.result.message.content == "This tag doesn't exist"
        ), self.base_context.result.message.content

    @test
    async def tag_found(self) -> None:
        tag_data = self._make_tag(name="hello", content="world")
        self._seed_guild(tags=[tag_data])
        await self.command(self.cog, self.base_context, name="hello")
        assert (
            self.base_context.result.message.content == "world"
        ), self.base_context.result.message.content


class Delete(TestingTags):

    def __init__(self):
        super().__init__()

    @test
    async def tag_not_found(self) -> None:
        self._seed_guild(tags=[])
        await self.command(self.cog, self.base_context, name="nonexistent")
        assert (
            self.base_context.result.message.content
            == "A tag with that name does not exist!"
        ), self.base_context.result.message.content

    @test
    async def not_owner_no_perms(self) -> None:
        other_id = self.base_author.id + 1
        tag_data = self._make_tag(name="secret", owner=other_id)
        self._seed_guild(tags=[tag_data])
        original = self.base_channel.permissions_for
        self.base_channel.permissions_for = lambda member: Permissions(manage_guild=False, send_messages=True)
        await self.command(self.cog, self.base_context, name="secret")
        self.base_channel.permissions_for = original
        assert (
            self.base_context.result.message.content
            == "You need to be tag owner or have the `manage server` permission to delete tags!"
        ), self.base_context.result.message.content

    @test
    async def delete_own_tag(self) -> None:
        tag_data = self._make_tag(name="mine")
        self._seed_guild(tags=[tag_data])
        await self.command(self.cog, self.base_context, name="mine")
        assert (
            self.base_context.result.message.content
            == "Successfully deleted tag `mine`"
        ), self.base_context.result.message.content


class Info(TestingTags):

    def __init__(self):
        super().__init__()

    @test
    async def tag_not_found(self) -> None:
        self._seed_guild(tags=[])
        await self.command(self.cog, self.base_context, name="nonexistent")
        assert (
            self.base_context.result.message.content
            == "There is no tag with that name!"
        ), self.base_context.result.message.content

    @test
    async def tag_info_displayed(self) -> None:
        tag_data = self._make_tag(name="hello", content="world", uses=5)
        self._seed_guild(tags=[tag_data])
        await self.command(self.cog, self.base_context, name="hello")
        assert (
            self.base_context.result.message.embeds
        ), self.base_context.result.message.embeds
        assert (
            "hello" in self.base_context.result.message.embeds[0].title
        ), self.base_context.result.message.embeds[0].title


class List(TestingTags):

    def __init__(self):
        super().__init__()

    @test
    async def no_tags(self) -> None:
        self._seed_guild()
        await self.command(self.cog, self.base_context)
        assert (
            self.base_context.result.message.content
            == "Seems like this server doesn't have any tags!"
        ), self.base_context.result.message.content

    @test
    async def has_tags(self) -> None:
        tag_data = self._make_tag(name="hello", uses=3)
        self._seed_guild(tags=[tag_data])
        await self.command(self.cog, self.base_context)
        assert (
            self.base_context.result.message.embeds
        ), self.base_context.result.message.embeds
        assert (
            "Top tags of guild" in self.base_context.result.message.embeds[0].title
        ), self.base_context.result.message.embeds[0].title

    @test
    async def list_paginator_next_page(self) -> None:
        """Paginator: tag list with >10 tags advances with next button."""
        tags = [self._make_tag(name=f"t{i}", uses=i, content="c") for i in range(25)]
        self._seed_guild(tags=tags)
        self.base_context.timeout_view = False

        async def _press_next(ctx):
            await press_paginator_button(
                ctx.current_view,
                "next",
                context=ctx,
                message=ctx.result.message,
            )
            ctx.current_view.stop()

        _prev_rtv = self.base_context.respond_to_view
        self.base_context.respond_to_view = _press_next
        try:
            with patch("killua.bot.randint", return_value=100):
                await self.command(self.cog, self.base_context)
        finally:
            self.base_context.respond_to_view = _prev_rtv
        emb = self.base_context.result.message.embeds[0]
        fp = embed_footer_page(emb)
        if fp is not None:
            assert fp == (2, 3), fp
        assert "`t" in emb.description, emb.description


class Transfer(TestingTags):

    def __init__(self):
        super().__init__()
        self.base_context.command = self.command

    @test
    async def transfer_success(self) -> None:
        recipient = DiscordMember(
            id=self.base_author.id + 1000,
            username="Recipient",
        )
        self.base_guild.members = [self.base_author, recipient]
        tag_data = self._make_tag(name="handoff", content="payload")
        self._seed_guild(tags=[tag_data])

        await self.command(
            self.cog,
            self.base_context,
            user=recipient,
            name="handoff",
        )

        content = self.base_context.result.message.content
        assert "Successfully transferred tag `handoff`" in content, content
        assert "Recipient" in content, content

    @test
    async def tag_not_found(self) -> None:
        self._seed_guild(tags=[])
        recipient = DiscordMember(id=self.base_author.id + 2000, username="R2")
        self.base_guild.members = [self.base_author, recipient]

        await self.command(
            self.cog,
            self.base_context,
            user=recipient,
            name="missingtag",
        )

        assert (
            "does not exist" in self.base_context.result.message.content.lower()
        ), self.base_context.result.message.content

    @test
    async def not_owner(self) -> None:
        recipient = DiscordMember(id=self.base_author.id + 3000, username="R3")
        self.base_guild.members = [self.base_author, recipient]
        tag_data = self._make_tag(name="locked", owner=self.base_author.id + 9999)
        self._seed_guild(tags=[tag_data])

        await self.command(
            self.cog,
            self.base_context,
            user=recipient,
            name="locked",
        )

        assert (
            "tag owner" in self.base_context.result.message.content.lower()
        ), self.base_context.result.message.content


class Edit(TestingTags):

    def __init__(self):
        super().__init__()

    @test
    async def tag_not_found(self) -> None:
        self._seed_guild(tags=[])
        await self.command(self.cog, self.base_context, name="missing")
        assert (
            self.base_context.result.message.content
            == "A tag with that name does not exist!"
        )

    @test
    async def not_owner(self) -> None:
        tag_data = self._make_tag(name="owned", owner=self.base_author.id + 999)
        self._seed_guild(tags=[tag_data])
        await self.command(self.cog, self.base_context, name="owned")
        assert (
            self.base_context.result.message.content
            == "You need to be tag owner to edit this tag!"
        )

    @test
    async def updates_description(self) -> None:
        tag_data = self._make_tag(name="editable", content="old text")
        self._seed_guild(tags=[tag_data])

        async def _text_response(ctx, prompt, **kwargs):
            return "new description"

        self.cog.client.get_text_response = _text_response
        await self.command(self.cog, self.base_context, name="editable")
        assert (
            self.base_context.result.message.content
            == "Successfully updated tag `editable`"
        )
        updated = await Tag.new(self.base_guild.id, "editable")
        assert updated.content == "new description"


class User(TestingTags):

    def __init__(self):
        super().__init__()

    @test
    async def member_has_no_tags(self) -> None:
        other = DiscordMember(id=self.base_author.id + 4000, username="NoTags")
        self._seed_guild(tags=[self._make_tag(name="other", owner=self.base_author.id)])
        await self.command(self.cog, self.base_context, user=other)
        assert (
            self.base_context.result.message.content
            == "This user currently does not have any tags!"
        )

    @test
    async def lists_owned_tags(self) -> None:
        self._seed_guild(
            tags=[
                self._make_tag(name="alpha", owner=self.base_author.id, uses=10),
                self._make_tag(name="beta", owner=self.base_author.id, uses=3),
            ]
        )
        await self.command(self.cog, self.base_context, user=self.base_author)
        emb = embed_at(self.base_context)
        assert_embed_title(emb, "Top tags owned by")
        assert "`alpha` with `10` uses" in (emb.description or "")
        assert "`beta` with `3` uses" in (emb.description or "")


class Create(TestingTags):

    def __init__(self):
        super().__init__()

    @test
    async def tag_already_exists(self) -> None:
        tag_data = self._make_tag(name="existing", content="old")
        self._seed_guild(tags=[tag_data])

        await self.command(self.cog, self.base_context, name="existing")

        assert (
            "already exists" in self.base_context.result.message.content
        ), self.base_context.result.message.content

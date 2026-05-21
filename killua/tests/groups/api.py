"""Mocked IPCRoutes handler tests (no ZMQ poll loop)."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import discord
from discord.ext import commands
from PIL import Image

from ..testing import Testing, test, collect_test_classes
from ..types import Bot
from ...cogs.api import IPCRoutes, NewsMessage
from ...static.constants import DB, NEWS_CHANNEL, POST_CHANNEL, UPDATE_CHANNEL
from ...utils.classes import User


class TestingApi(Testing):
    _ipc: IPCRoutes | None = None

    def __init__(self) -> None:
        from discord.ext.commands.view import StringView

        from ..types import (
            Bot as TestBot,
            Context,
            DiscordGuild,
            DiscordMember,
            Message,
            TestResult,
            TextChannel,
        )

        if TestingApi._ipc is None:
            TestingApi._ipc = IPCRoutes(TestBot)
        self.base_guild = DiscordGuild()
        self.base_channel = TextChannel(guild=self.base_guild)
        self.base_author = DiscordMember()
        self.base_message = Message(
            author=self.base_author, channel=self.base_channel
        )
        self.base_context = Context(
            message=self.base_message, bot=TestBot, view=StringView("testing")
        )
        self.result = TestResult()
        self.cog = TestingApi._ipc

    @property
    def all_tests(self):
        return collect_test_classes(self.__class__)


class _ApiTests(TestingApi):
    pass


class NewsMessageTests(_ApiTests):
    @test
    async def make_view_update_type(self) -> None:
        DB.news.db["news"] = [
            {
                "_id": "prev",
                "type": "update",
                "published": True,
                "version": "1.0.0",
                "timestamp": datetime(2020, 1, 1),
            }
        ]
        msg = NewsMessage.from_data(
            Bot,
            {
                "_id": "n2",
                "title": "T",
                "content": "Body",
                "author": str(self.base_author.id),
                "type": "update",
                "version": "2.0.0",
                "timestamp": datetime(2021, 1, 1),
                "images": [],
                "links": {"docs": "https://example.com"},
            },
        )
        view, files = await msg._make_view(include_ping=False)
        assert view is not None

    @test
    async def invalid_news_type_ping_raises(self) -> None:
        msg = NewsMessage.from_data(
            Bot,
            {
                "_id": "x",
                "title": "t",
                "content": "c",
                "author": "1",
                "type": "invalid",
                "timestamp": datetime.now(),
            },
        )
        try:
            _ = msg.relevant_ping
            assert False
        except ValueError:
            pass

    @test
    async def from_data_round_trip(self) -> None:
        data = {
            "_id": "n1",
            "title": "T",
            "content": "C",
            "author": 1,
            "type": "news",
            "version": "1.0",
            "images": [],
            "links": {},
            "notify_users": [],
            "timestamp": datetime.now(),
        }
        msg = NewsMessage.from_data(Bot, data)
        assert msg.id == "n1"
        assert msg.title == "T"
        assert msg._type == "news"

    @test
    async def from_id_missing_raises(self) -> None:
        DB.news.db["news"] = []
        try:
            await NewsMessage.from_id(Bot, "missing")
            assert False
        except ValueError:
            pass

    @test
    async def from_id_returns_instance(self) -> None:
        DB.news.db["news"] = [
            {
                "_id": "nid",
                "title": "Hi",
                "content": "Body",
                "author": self.base_author.id,
                "type": "update",
                "timestamp": datetime.now(),
            }
        ]
        msg = await NewsMessage.from_id(Bot, "nid")
        assert isinstance(msg, NewsMessage)
        assert msg.title == "Hi"

    @test
    async def relevant_channel_ids(self) -> None:
        assert NewsMessage.relevant_channel_id("news") == NEWS_CHANNEL
        assert NewsMessage.relevant_channel_id("post") == POST_CHANNEL
        assert NewsMessage.relevant_channel_id("other") == UPDATE_CHANNEL

    @test
    async def relevant_ping_roles(self) -> None:
        msg = NewsMessage.from_data(
            Bot,
            {
                "_id": "x",
                "title": "t",
                "content": "c",
                "author": "1",
                "type": "post",
                "timestamp": datetime.now(),
            },
        )
        assert msg.relevant_ping is not None


class IpcHandlerTests(_ApiTests):
    @test
    async def heartbeat(self) -> None:
        ipc = self.cog
        assert await ipc.heartbeat({}) == {"status": "ok"}

    @test
    async def jsonify_helpers(self) -> None:
        ipc = self.cog
        out = ipc.jsonify(
            {
                "when": datetime(2020, 1, 1),
                "id": 1234567890123456789,
                "nested": [{"t": datetime(2021, 2, 2)}],
            }
        )
        assert isinstance(out["when"], str)
        assert isinstance(out["id"], str)

    @test
    async def make_grey_and_crop(self) -> None:
        ipc = self.cog
        img = Image.new("RGBA", (32, 32), (255, 0, 0, 128))
        grey = ipc.make_grey(img)
        assert grey.mode == "RGBA"
        circ = ipc.crop_to_circle(img.copy())
        assert circ.size == (32, 32)

    @test
    async def download_image(self) -> None:
        ipc = self.cog
        buf = BytesIO()
        Image.new("RGB", (8, 8), "blue").save(buf, format="PNG")
        buf.seek(0)

        class Resp:
            status = 200

            async def read(self):
                return buf.getvalue()

        ipc.client.session.get = AsyncMock(return_value=Resp())
        im = await ipc.download("http://example.test/x.png")
        assert im.size == (8, 8)

    @test
    async def stats(self) -> None:
        ipc = self.cog
        info = MagicMock()
        info.approximate_user_install_count = 5
        ipc.client.application_info = AsyncMock(return_value=info)
        DB.teams.db["teams"] = [{"id": 1}, {"id": 2}, {"id": 3}]
        res = await ipc.stats({})
        assert res["guilds"] == len(ipc.client.guilds)
        assert res["registered_users"] == 3

    @test
    async def commands_format(self) -> None:
        ipc = self.cog
        with patch.object(
            ipc.client, "get_raw_formatted_commands", return_value=[]
        ):
            assert await ipc.commands({}) == {}

    @test
    async def user_get_basic_details(self) -> None:
        ipc = self.cog
        uid = self.base_author.id
        res = await ipc.user_get_basic_details({"user_id": uid})
        assert "display_name" in res

    @test
    async def user_info_with_email(self) -> None:
        ipc = self.cog
        uid = self.base_author.id
        await User.new(uid)
        res = await ipc.user_info(
            {"user_id": uid, "email": "a@b.c", "from_admin": True}
        )
        assert res["email"] == "a@b.c"

    @test
    async def discord_application_auth(self) -> None:
        ipc = self.cog
        uid = self.base_author.id
        await ipc.discord_application_authorized({"user": {"id": uid}})
        user = await User.new(uid)
        assert user.id == uid

    @test
    async def discord_application_deauth(self) -> None:
        ipc = self.cog
        uid = self.base_author.id
        await User.new(uid)
        await ipc.discord_application_deauthorized({"user": {"id": uid}})

    @test
    async def news_save_published(self) -> None:
        ipc = self.cog
        DB.news.db["news"] = []
        with patch.object(ipc, "_send_discord_message", AsyncMock(return_value=999)):
            res = await ipc.news_save(
                {
                    "title": "Pub",
                    "content": "C",
                    "type": "news",
                    "author": str(self.base_author.id),
                    "published": True,
                    "notify_users": [],
                }
            )
        assert res["message_id"] == 999

    @test
    async def news_save_draft(self) -> None:
        ipc = self.cog
        DB.news.db["news"] = []
        res = await ipc.news_save(
            {
                "title": "T",
                "content": "C",
                "type": "news",
                "author": str(self.base_author.id),
                "published": False,
                "notify_users": [],
            }
        )
        assert res["news_id"]
        assert res["message_id"] is None

    @test
    async def news_delete_missing_raises(self) -> None:
        ipc = self.cog
        DB.news.db["news"] = []
        try:
            await ipc.news_delete({"news_id": "missing"})
            assert False, "expected ValueError"
        except ValueError:
            pass

    @test
    async def news_delete_with_message(self) -> None:
        ipc = self.cog
        DB.news.db["news"] = [
            {"_id": "d2", "type": "news", "messageId": 12345, "published": True}
        ]
        with patch.object(ipc, "_delete_discord_message", AsyncMock()):
            res = await ipc.news_delete({"news_id": "d2"})
        assert res["status"] == "deleted"

    @test
    async def get_discord_user(self) -> None:
        ipc = self.cog
        uid = self.base_author.id
        user = MagicMock()
        user.display_name = "Tester"
        user.name = "tester"
        user.avatar.url = "https://example.com/a.png"
        user.created_at = datetime.now()
        ipc.client.get_user = MagicMock(return_value=user)
        res = await ipc.get_discord_user({"user": uid})
        assert res["name"] == "Tester"

    @test
    async def top_empty(self) -> None:
        ipc = self.cog
        DB.teams.db["teams"] = []
        assert await ipc.top({}) == []

    @test
    async def vote_handler(self) -> None:
        ipc = self.cog
        uid = self.base_author.id
        await User.new(uid)
        usr = MagicMock()
        usr.send = AsyncMock()
        ipc.client.get_user = MagicMock(return_value=usr)
        ipc.client.fetch_user = AsyncMock(return_value=usr)
        with patch.object(ipc, "streak_image", AsyncMock(return_value=BytesIO(b"x"))):
            await ipc.vote({"user": uid, "isWeekend": False})

    @test
    async def guild_editable(self) -> None:
        ipc = self.cog
        gid = self.base_guild.id
        ipc.client.get_guild = MagicMock(
            side_effect=lambda x: self.base_guild if x == gid else None
        )
        res = await ipc.guild_editable({"guild_ids": [gid, 999999]})
        assert gid in res["editable"]

    @test
    async def guild_info_and_edit(self) -> None:
        from ...utils.classes.guild import Guild as KilluaGuild

        ipc = self.cog
        gid = self.base_guild.id
        ipc.client.get_guild = MagicMock(return_value=self.base_guild)
        await KilluaGuild.new(gid)
        res = await ipc.guild_info({"guild_id": gid})
        assert "prefix" in res
        edit = await ipc.guild_edit({"guild_id": gid, "prefix": "k?"})
        assert edit["success"] is True

    @test
    async def news_edit_flow(self) -> None:
        ipc = self.cog
        DB.news.db["news"] = [
            {
                "_id": "e1",
                "title": "Old",
                "content": "C",
                "type": "news",
                "author": self.base_author.id,
                "published": False,
                "timestamp": datetime.now(),
            }
        ]
        res = await ipc.news_edit(
            {"news_id": "e1", "title": "New", "content": "C", "type": "news"}
        )
        assert res["news_id"] == "e1"

    @test
    async def register_login_first_time(self) -> None:
        ipc = self.cog
        uid = self.base_author.id
        u = await User.new(uid)
        user = MagicMock()
        user.send = AsyncMock()
        with patch.object(u, "register_login", AsyncMock(return_value=True)):
            with patch.object(u, "add_lootbox", AsyncMock()):
                with patch.object(u, "add_jenny", AsyncMock()):
                    await ipc._register_login(user, u)

    @test
    async def user_info_requires_id(self) -> None:
        ipc = self.cog
        try:
            await ipc.user_info({})
            assert False
        except ValueError:
            pass

    @test
    async def commands_payload(self) -> None:
        ipc = self.cog
        res = await ipc.commands({})
        assert isinstance(res, dict)

    @test
    async def user_get_basic_details(self) -> None:
        ipc = self.cog
        ipc.client.get_user = MagicMock(return_value=self.base_author)
        res = await ipc.user_get_basic_details({"user_id": self.base_author.id})
        assert res["display_name"] == self.base_author.display_name

    @test
    async def user_get_basic_details_fetch_fallback(self) -> None:
        ipc = self.cog
        user = MagicMock()
        user.display_name = "Fetched"
        user.avatar = None
        ipc.client.get_user = MagicMock(return_value=None)
        ipc.client.fetch_user = AsyncMock(return_value=user)
        res = await ipc.user_get_basic_details({"user_id": 999888777})
        assert res["display_name"] == "Fetched"
        assert res["avatar_url"] is None

    @test
    async def user_get_basic_details_invalid_id(self) -> None:
        ipc = self.cog
        try:
            await ipc.user_get_basic_details({"user_id": "not-a-number"})
            assert False
        except ValueError:
            pass

    @test
    async def news_save_publishes_message(self) -> None:
        ipc = self.cog
        DB.news.db["news"] = []
        with patch.object(ipc, "_send_discord_message", AsyncMock(return_value=4242)):
            res = await ipc.news_save(
                {
                    "title": "Launch",
                    "content": "Body",
                    "type": "news",
                    "author": self.base_author.id,
                    "published": True,
                    "notify_users": [],
                }
            )
        assert res["message_id"] == 4242

    @test
    async def guild_tag_create_success(self) -> None:
        from ...cogs.tags import Tags
        from ...utils.classes.guild import Guild as KilluaGuild

        ipc = self.cog
        gid = self.base_guild.id
        ipc.client.get_guild = MagicMock(return_value=self.base_guild)
        await KilluaGuild.new(gid)
        with patch.object(
            Tags, "initial_new_tag_validation", AsyncMock(return_value=None)
        ):
            with patch.object(Tags, "_validate_tag_details", return_value=None):
                res = await ipc.guild_tag_create(
                    {
                        "guild_id": gid,
                        "name": "tag-a",
                        "content": "hello",
                        "user_id": self.base_author.id,
                    }
                )
        assert res["success"] is True

    @test
    async def guild_tag_delete_success(self) -> None:
        from ...utils.classes.guild import Guild as KilluaGuild

        ipc = self.cog
        gid = self.base_guild.id
        ipc.client.get_guild = MagicMock(return_value=self.base_guild)
        guild = await KilluaGuild.new(gid)
        guild.tags = [
            {
                "name": "remove-me",
                "content": "bye",
                "owner": self.base_author.id,
                "uses": 0,
                "created_at": datetime.now(),
            }
        ]
        await guild._update_val("tags", guild.tags)
        KilluaGuild.cache.pop(gid, None)
        res = await ipc.guild_tag_delete({"guild_id": gid, "name": "remove-me"})
        assert res["success"] is True

    @test
    async def guild_tag_edit_success(self) -> None:
        from ...cogs.tags import Tags
        from ...utils.classes.guild import Guild as KilluaGuild

        ipc = self.cog
        gid = self.base_guild.id
        ipc.client.get_guild = MagicMock(return_value=self.base_guild)
        guild = await KilluaGuild.new(gid)
        guild.tags = [
            {
                "name": "edit-me",
                "content": "old",
                "owner": self.base_author.id,
                "uses": 0,
                "created_at": datetime.now(),
            }
        ]
        await guild._update_val("tags", guild.tags)
        KilluaGuild.cache.pop(gid, None)
        with patch.object(Tags, "_validate_tag_details", return_value=None):
            res = await ipc.guild_tag_edit(
                {
                    "guild_id": gid,
                    "name": "edit-me",
                    "content": "new text",
                }
            )
        assert res["success"] is True

    @test
    async def guild_tag_edit_rename(self) -> None:
        from ...cogs.tags import Tags
        from ...utils.classes.guild import Guild as KilluaGuild

        ipc = self.cog
        gid = self.base_guild.id
        ipc.client.get_guild = MagicMock(return_value=self.base_guild)
        guild = await KilluaGuild.new(gid)
        guild.tags = [
            {
                "name": "rename-me",
                "content": "old",
                "owner": self.base_author.id,
                "uses": 0,
                "created_at": datetime.now(),
            }
        ]
        await guild._update_val("tags", guild.tags)
        KilluaGuild.cache.pop(gid, None)
        with patch.object(Tags, "_validate_tag_details", return_value=None):
            res = await ipc.guild_tag_edit(
                {
                    "guild_id": gid,
                    "name": "rename-me",
                    "new_name": "renamed",
                    "content": "new body",
                    "new_owner": self.base_author.id + 1,
                }
            )
        assert res["success"] is True

    @test
    async def news_edit_publish(self) -> None:
        ipc = self.cog
        DB.news.db["news"] = [
            {
                "_id": "pub1",
                "title": "Draft",
                "content": "C",
                "type": "news",
                "author": self.base_author.id,
                "published": False,
                "timestamp": datetime.now(),
            }
        ]
        with patch.object(ipc, "_send_discord_message", AsyncMock(return_value=5555)):
            res = await ipc.news_edit(
                {"news_id": "pub1", "published": True, "title": "Draft", "content": "C", "type": "news"}
            )
        assert res["message_id"] == 5555

    @test
    async def news_edit_unpublish(self) -> None:
        ipc = self.cog
        DB.news.db["news"] = [
            {
                "_id": "unpub1",
                "title": "Live",
                "content": "C",
                "type": "news",
                "author": self.base_author.id,
                "published": True,
                "messageId": 7777,
                "timestamp": datetime.now(),
            }
        ]
        with patch.object(ipc, "_delete_discord_message", AsyncMock()):
            res = await ipc.news_edit(
                {"news_id": "unpub1", "published": False, "title": "Live", "content": "C", "type": "news"}
            )
        assert res["message_id"] is None

    @test
    async def guild_tag_delete_not_found(self) -> None:
        from ...utils.classes.guild import Guild as KilluaGuild

        ipc = self.cog
        gid = self.base_guild.id
        ipc.client.get_guild = MagicMock(return_value=self.base_guild)
        await KilluaGuild.new(gid)
        res = await ipc.guild_tag_delete({"guild_id": gid, "name": "missing-tag"})
        assert res["success"] is False

    @test
    async def news_edit_updates_published_message(self) -> None:
        ipc = self.cog
        DB.news.db["news"] = [
            {
                "_id": "live1",
                "title": "Live",
                "content": "C",
                "type": "news",
                "author": self.base_author.id,
                "published": True,
                "messageId": 8888,
                "timestamp": datetime.now(),
            }
        ]
        with patch.object(ipc, "_edit_discord_message", AsyncMock()):
            res = await ipc.news_edit(
                {"news_id": "live1", "title": "Updated", "content": "C", "type": "news"}
            )
        assert res["news_id"] == "live1"

    @test
    async def delete_discord_message(self) -> None:
        from ...static.constants import NEWS_CHANNEL

        ipc = self.cog
        channel = MagicMock()
        message = MagicMock()
        message.delete = AsyncMock()
        channel.fetch_message = AsyncMock(return_value=message)
        ipc.client.get_channel = MagicMock(return_value=channel)
        await ipc._delete_discord_message("news", "12345")
        message.delete.assert_awaited_once()
        ipc.client.get_channel.assert_called_with(NEWS_CHANNEL)


from ...utils.topgg import (
    TOPGG_ANNOUNCEMENTS_URL,
    TOPGG_METRICS_URL,
    post_announcement,
    post_metrics,
)


class _MockTopggResponse:
    def __init__(self, status: int = 200, body: str = "") -> None:
        self.status = status
        self._body = body

    async def text(self) -> str:
        return self._body

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args) -> None:
        return None


def _mock_topgg_session(session, *, status: int = 200, body: str = "") -> MagicMock:
    mock_request = MagicMock(return_value=_MockTopggResponse(status, body))
    session.request = mock_request
    return mock_request


class TopggAnnouncementTests(_ApiTests):
    def _news_item(self, *, news_type="news", title="Launch", content="Body text here"):
        return {
            "_id": "topgg1",
            "title": title,
            "content": content,
            "type": news_type,
            "author": self.base_author.id,
            "timestamp": datetime.now(),
            "notify_users": [],
        }

    @test
    async def normalize_token_strips_quotes_and_bearer_prefix(self) -> None:
        from killua.utils.topgg import _normalize_token

        assert _normalize_token('"abc"') == "abc"
        assert _normalize_token("'abc'") == "abc"
        assert _normalize_token("Bearer xyz") == "xyz"
        assert _normalize_token("  token  ") == "token"

    @test
    async def publish_posts_announcement(self) -> None:
        ipc = self.cog
        mock_request = _mock_topgg_session(ipc.client.session)
        with patch("killua.utils.topgg._token", return_value="test-token"):
            await ipc._publish_topgg_announcement(self._news_item())
        mock_request.assert_called_once()
        method, url = mock_request.call_args.args[:2]
        assert method == "POST"
        assert url == TOPGG_ANNOUNCEMENTS_URL
        assert mock_request.call_args.kwargs["json"] == {
            "title": "News: Launch",
            "content": "Body text here",
        }
        assert (
            mock_request.call_args.kwargs["headers"]["Authorization"]
            == "Bearer test-token"
        )

    @test
    async def publish_prefixes_type_in_title(self) -> None:
        ipc = self.cog
        mock_request = _mock_topgg_session(ipc.client.session)
        with patch("killua.utils.topgg._token", return_value="test-token"):
            await ipc._publish_topgg_announcement(
                self._news_item(news_type="update", title="v2.0")
            )
        assert mock_request.call_args.kwargs["json"]["title"] == "Update: v2.0"

    @test
    async def publish_truncates_long_title(self) -> None:
        ipc = self.cog
        mock_request = _mock_topgg_session(ipc.client.session)
        long_title = "x" * 200
        with patch("killua.utils.topgg._token", return_value="test-token"):
            await ipc._publish_topgg_announcement(
                self._news_item(title=long_title, content="Body text here")
            )
        title = mock_request.call_args.kwargs["json"]["title"]
        assert len(title) == 100
        assert title.endswith("...")
        assert title.startswith("News: ")

    @test
    async def publish_truncates_long_content_with_link(self) -> None:
        ipc = self.cog
        mock_request = _mock_topgg_session(ipc.client.session)
        long_content = "word " * 500
        with patch("killua.utils.topgg._token", return_value="test-token"):
            await ipc._publish_topgg_announcement(
                self._news_item(title="Launch", content=long_content)
            )
        content = mock_request.call_args.kwargs["json"]["content"]
        assert len(content) <= 2000
        assert content.endswith("Read the rest at https://killua.dev/news/topgg1")
        assert long_content not in content

    @test
    async def format_topgg_title_and_content_helpers(self) -> None:
        ipc = self.cog
        assert IPCRoutes._format_topgg_title("news", "Hi") == "News: Hi"
        assert len(IPCRoutes._format_topgg_title("news", "t" * 200)) == 100
        msg = NewsMessage.from_data(
            ipc.client,
            self._news_item(content="short"),
        )
        assert IPCRoutes._format_topgg_content(msg, "short") == "short"
        long_body = "a" * 2500
        formatted = IPCRoutes._format_topgg_content(msg, long_body)
        assert len(formatted) == 2000
        assert formatted.endswith(f"Read the rest at {msg.url}")

    @test
    async def publish_skips_without_token(self) -> None:
        ipc = self.cog
        mock_request = _mock_topgg_session(ipc.client.session)
        with patch("killua.utils.topgg._token", return_value=None):
            await ipc._publish_topgg_announcement(self._news_item())
        mock_request.assert_not_called()

    @test
    async def publish_skips_in_dev(self) -> None:
        ipc = self.cog
        mock_request = _mock_topgg_session(ipc.client.session)
        ipc.client.is_dev = True
        try:
            with patch("killua.utils.topgg._token", return_value="test-token"):
                await ipc._publish_topgg_announcement(self._news_item())
            mock_request.assert_not_called()
        finally:
            ipc.client.is_dev = False

    @test
    async def post_metrics_uses_v1_patch(self) -> None:
        ipc = self.cog
        mock_request = _mock_topgg_session(ipc.client.session, status=204)
        with patch("killua.utils.topgg._token", return_value="test-token"):
            ok = await post_metrics(
                ipc.client.session, server_count=420, shard_count=2
            )
        assert ok is True
        method, url = mock_request.call_args.args[:2]
        assert method == "PATCH"
        assert url == TOPGG_METRICS_URL
        assert mock_request.call_args.kwargs["json"] == {
            "server_count": 420,
            "shard_count": 2,
        }

    @test
    async def post_metrics_returns_false_on_http_error(self) -> None:
        ipc = self.cog
        _mock_topgg_session(
            ipc.client.session,
            status=401,
            body='{"title":"Unauthorized"}',
        )
        with patch("killua.utils.topgg._token", return_value="test-token"):
            ok = await post_metrics(ipc.client.session, server_count=1)
        assert ok is False

    @test
    async def news_save_published_posts_topgg(self) -> None:
        ipc = self.cog
        DB.news.db["news"] = []
        mock_request = _mock_topgg_session(ipc.client.session)
        with patch("killua.utils.topgg._token", return_value="test-token"):
            with patch.object(ipc, "_send_discord_message", AsyncMock(return_value=4242)):
                await ipc.news_save(
                    {
                        "title": "Launch",
                        "content": "Published body text",
                        "type": "post",
                        "author": self.base_author.id,
                        "published": True,
                        "notify_users": [],
                    }
                )
        mock_request.assert_called_once()
        assert mock_request.call_args.kwargs["json"]["title"] == "Post: Launch"

    @test
    async def news_edit_first_publish_posts_topgg(self) -> None:
        ipc = self.cog
        DB.news.db["news"] = [
            {
                "_id": "pub-topgg",
                "title": "Draft",
                "content": "Going live now",
                "type": "news",
                "author": self.base_author.id,
                "published": False,
                "timestamp": datetime.now(),
                "notify_users": [],
            }
        ]
        mock_request = _mock_topgg_session(ipc.client.session)
        with patch("killua.utils.topgg._token", return_value="test-token"):
            with patch.object(ipc, "_send_discord_message", AsyncMock(return_value=5555)):
                await ipc.news_edit(
                    {
                        "news_id": "pub-topgg",
                        "published": True,
                        "title": "Draft",
                        "content": "Going live now",
                        "type": "news",
                    }
                )
        mock_request.assert_called_once()
        assert mock_request.call_args.kwargs["json"]["title"] == "News: Draft"

    @test
    async def news_edit_update_does_not_repost_topgg(self) -> None:
        ipc = self.cog
        DB.news.db["news"] = [
            {
                "_id": "live-topgg",
                "title": "Live",
                "content": "Already published",
                "type": "news",
                "author": self.base_author.id,
                "published": True,
                "messageId": 8888,
                "timestamp": datetime.now(),
                "notify_users": [],
            }
        ]
        mock_request = _mock_topgg_session(ipc.client.session)
        with patch("killua.utils.topgg._token", return_value="test-token"):
            with patch.object(ipc, "_edit_discord_message", AsyncMock()):
                await ipc.news_edit(
                    {
                        "news_id": "live-topgg",
                        "title": "Updated title",
                        "content": "Already published",
                        "type": "news",
                    }
                )
        mock_request.assert_not_called()

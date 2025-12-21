from unittest.mock import AsyncMock, MagicMock, patch
from ..types import *
from ...utils.classes import *
from ..testing import Testing, test
from ...cogs.message import Message

class TestingMessage(Testing):
    def __init__(self):
        super().__init__(cog=Message)

class Stats(TestingMessage):
    def __init__(self):
        super().__init__()
    
    @test
    async def leaderboard_renders(self) -> None:
        # mock member
        member = MagicMock()
        member.id = 42
        member.mention = "<@42>"
        member.display_name = "TestUser"

        # mock interaction
        interaction = MagicMock()
        interaction.guild.id = 123
        interaction.guild.name = "Test Guild"
        interaction.guild.get_member = MagicMock(return_value=member)
        interaction.guild.fetch_member = AsyncMock(side_effect=Exception())
        interaction.followup.send = AsyncMock()
        interaction.response.defer = AsyncMock()
        interaction.user.display_name = "Tester"

        # mock guild
        mock_guild = MagicMock()
        mock_guild.id = 123
        mock_guild.get_top_senders = AsyncMock(return_value=[(1, 100), (2, 80), (3, 60)])
        mock_guild.get_total_messages = AsyncMock(return_value=240)

        with patch("killua.utils.classes.guild.Guild.new", AsyncMock(return_value=mock_guild)):
            await self.cog.stats.callback(self.cog, interaction, user=None, limit=3)

        interaction.followup.send.assert_awaited()
        sent_embed = interaction.followup.send.call_args.kwargs.get("embed")
        assert sent_embed is not None, "Expected an embed to be sent"

    @test
    async def user_with_no_messages(self) -> None:
        # mock interaction
        interaction = MagicMock()
        interaction.guild.id = 123
        interaction.user.display_name = "Tester"
        interaction.followup.send = AsyncMock()
        interaction.response.defer = AsyncMock()

        # mock member with no messages
        member = MagicMock()
        member.id = 42
        member.mention = "<@42>"
        member.display_name = "TestUser"

        # mock guild with no messages for this user
        mock_guild = MagicMock()
        mock_guild.id = 123
        mock_guild.get_message_count = MagicMock(return_value=0)
        mock_guild.get_user_rank = AsyncMock(return_value=None)
        mock_guild.get_total_messages = AsyncMock(return_value=0)

        with patch("killua.utils.classes.guild.Guild.new", AsyncMock(return_value=mock_guild)):
            await self.cog.stats.callback(self.cog, interaction, user=member, limit=10)

        interaction.followup.send.assert_awaited()
        sent_embed = interaction.followup.send.call_args.kwargs.get("embed")
        assert sent_embed is not None and "No Messages" in sent_embed.fields[0].name, "Expected 'No Messages' field in embed"

    @test
    async def user_with_messages(self) -> None:
        # mock interaction
        interaction = MagicMock()
        interaction.guild.id = 123
        interaction.user.display_name = "Tester"
        interaction.followup.send = AsyncMock()
        interaction.response.defer = AsyncMock()

        # mock member with messages
        member = MagicMock()
        member.id = 42
        member.mention = "<@42>"
        member.display_name = "TestUser"

        # mock guild with messages for this user
        mock_guild = MagicMock()
        mock_guild.id = 123
        mock_guild.get_message_count = MagicMock(return_value=50)
        mock_guild.get_user_rank = AsyncMock(return_value=5)
        mock_guild.get_total_messages = AsyncMock(return_value=200)

        with patch("killua.utils.classes.guild.Guild.new", AsyncMock(return_value=mock_guild)):
            await self.cog.stats.callback(self.cog, interaction, user=member, limit=10)

        interaction.followup.send.assert_awaited()
        sent_embed = interaction.followup.send.call_args.kwargs.get("embed")
        assert sent_embed is not None, "Expected an embed to be sent"
        field_names = [field.name for field in sent_embed.fields]
        assert "Messages Sent" in field_names, "Expected 'Messages Sent' field in embed"
        assert "Rank" in field_names, "Expected 'Rank' field in embed"
        assert "Percentage of Total Messages" in field_names, "Expected 'Percentage of Total Messages' field in embed"

    @test
    async def leaderboard_no_messages(self) -> None:
        # mock interaction
        interaction = MagicMock()
        interaction.guild.id = 123
        interaction.user.display_name = "Tester"
        interaction.followup.send = AsyncMock()
        interaction.response.defer = AsyncMock()

        # mock guild with no messages
        mock_guild = MagicMock()
        mock_guild.id = 123
        mock_guild.get_top_senders = AsyncMock(return_value=[])
        mock_guild.get_total_messages = AsyncMock(return_value=0)

        with patch("killua.utils.classes.guild.Guild.new", AsyncMock(return_value=mock_guild)):
            await self.cog.stats.callback(self.cog, interaction, user=None, limit=10)

        interaction.followup.send.assert_awaited()
        sent_embed = interaction.followup.send.call_args.kwargs.get("embed")
        assert sent_embed is not None, "Expected an embed to be sent"
        assert "No message data available" in sent_embed.fields[0].value, "Expected 'No message data available' message in embed"
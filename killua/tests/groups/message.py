from unittest.mock import AsyncMock, MagicMock, patch
from ..types import *
from ...utils.classes import *
from ..testing import Testing, test
from ...cogs.message import Message
from ...utils.test_db import TestingDatabase

class TestingMessage(Testing):
    def __init__(self):
        super().__init__(cog=Message)

class Stats(TestingMessage):
    def __init__(self):
        super().__init__()

    @test
    async def user_with_no_messages(self) -> None:
        guild = await Guild.new(self.base_guild.id)
        await guild.toggle_message_tracking() # enable tracking
        
        member = DiscordMember(guild=self.base_guild)
        user = await User.new(member.id)
        await user.toggle_message_tracking() # enable tracking

        interaction = ArgumentInteraction(context=self.base_context, guild=self.base_guild)
        
        await self.cog.stats.callback(self.cog, interaction, user=member)

        assert interaction.followup.sent[0]["embeds"][0] is not None, "Expected an embed to be sent"
        field_names = [field.name for field in interaction.followup.sent[0]["embeds"][0].fields]
        assert "No Messages" in field_names or any("no" in name.lower() for name in field_names), "Expected 'No Messages' field in embed"

    @test
    async def user_with_messages(self) -> None:
        guild = await Guild.new(self.base_guild.id)
        await guild.toggle_message_tracking() # enable tracking
        
        member = DiscordMember(guild=self.base_guild)
        user = await User.new(member.id)
        await user.toggle_message_tracking() # enable tracking

        guild.message_stats[member.id] = 50

        interaction = ArgumentInteraction(context=self.base_context, guild=self.base_guild)
        
        await self.cog.stats.callback(self.cog, interaction, user=member)

        sent_embed = interaction.followup.sent[0]["embeds"][0]
        assert sent_embed is not None, "Expected an embed to be sent"
        field_names = [field.name for field in sent_embed.fields]
        assert "Messages Sent" in field_names, "Expected 'Messages Sent' field in embed"
        assert "Rank" in field_names, "Expected 'Rank' field in embed"
        assert "Percentage of Total Messages" in field_names, "Expected 'Percentage of Total Messages' field in embed"

    @test
    async def user_opted_out(self) -> None:
        guild = await Guild.new(self.base_guild.id)
        await guild.toggle_message_tracking() # enable tracking
        
        member = DiscordMember(guild=self.base_guild)
        user = await User.new(member.id)

        interaction = ArgumentInteraction(context=self.base_context, guild=self.base_guild)
        
        await self.cog.stats.callback(self.cog, interaction, user=member)


        message = interaction.followup.sent[0]["content"]
        assert "disabled" in message.lower(), "Expected tracking disabled message"

class Leaderboard(TestingMessage):
    def __init__(self):
        super().__init__()
    
    @test
    async def leaderboard_renders(self) -> None:
        guild = await Guild.new(self.base_guild.id)
        await guild.toggle_message_tracking() # enable tracking
        
        member = DiscordMember(guild=self.base_guild)
        user = await User.new(member.id)
        await user.toggle_message_tracking() # enable tracking

        guild.message_stats = {1: 100, 2: 80, 3: 60}

        interaction = ArgumentInteraction(context=self.base_context, guild=self.base_guild)

        await self.cog.leaderboard.callback(self.cog, interaction, limit=3)

        sent_embed = interaction.followup.sent[0]["embeds"][0]
        assert sent_embed is not None, "Expected an embed to be sent"

    @test
    async def leaderboard_no_messages(self) -> None:
        guild = await Guild.new(self.base_guild.id)
        await guild.toggle_message_tracking() # enable tracking
        
        member = DiscordMember(guild=self.base_guild)
        user = await User.new(member.id)
        await user.toggle_message_tracking() # enable tracking

        interaction = ArgumentInteraction(context=self.base_context, guild=self.base_guild)

        await self.cog.leaderboard.callback(self.cog, interaction, limit=3)

        sent_embed = interaction.followup.sent[0]["embeds"][0]
        assert sent_embed is not None, "Expected an embed to be sent"
        assert "No message data available" in sent_embed.fields[0].value, "Expected 'No message data available' message in embed"

    @test
    async def leaderboard_guild_opted_out(self) -> None:
        guild = await Guild.new(self.base_guild.id)
        
        member = DiscordMember(guild=self.base_guild)
        user = await User.new(member.id)
        await user.toggle_message_tracking() # enable tracking

        interaction = ArgumentInteraction(context=self.base_context, guild=self.base_guild)

        await self.cog.leaderboard.callback(self.cog, interaction, limit=3)

        message = interaction.followup.sent[0]["content"]
        assert "disabled" in message.lower(), "Expected tracking disabled message"
class User_Tracking(TestingMessage):
    def __init__(self):
        super().__init__()
    
    @test
    async def toggle_tracking_enable(self) -> None:
        user = await User.new(self.base_author.id)

        interaction = ArgumentInteraction(context=self.base_context, guild=self.base_guild)
        interaction.user = self.base_author
        
        await self.cog.user_tracking.callback(self.cog, interaction)

        assert interaction.response.is_done() or len(interaction.followup.sent) > 0, "Expected a response"
        
        user_after = await User.new(self.base_author.id)
        assert user_after.message_tracking_enabled == True, "Expected tracking to be enabled"

    @test
    async def toggle_tracking_disable_with_confirmation(self) -> None:
        user = await User.new(self.base_author.id)
        await user.toggle_message_tracking() # enable tracking
        
        guild = await Guild.new(self.base_guild.id)
        await guild.toggle_message_tracking()
        guild.message_stats[self.base_author.id] = 50

        interaction = ArgumentInteraction(context=self.base_context, guild=self.base_guild)
        interaction.user = self.base_author
        
        # mock the confirm view acceptance
        with patch("killua.cogs.message.ConfirmView") as MockView:
            mock_view_instance = MagicMock()
            mock_view_instance.value = True 
            mock_view_instance.wait = AsyncMock()
            MockView.return_value = mock_view_instance
            
            await self.cog.user_tracking.callback(self.cog, interaction)

        # confirmation view response
        assert interaction.response.is_done(), "Expected confirmation prompt"
        
        # after confirmation, followup is sent
        assert len(interaction.followup.sent) > 0, "Expected followup message after confirmation"

    @test
    async def toggle_tracking_disable_cancelled(self) -> None:
        user = await User.new(self.base_author.id)
        await user.toggle_message_tracking()  # enable tracking

        guild = await Guild.new(self.base_guild.id)
        await guild.toggle_message_tracking()
        guild.message_stats[self.base_author.id] = 50
        
        interaction = ArgumentInteraction(context=self.base_context, guild=self.base_guild)
        interaction.user = self.base_author
        
        # mock the confirm view cancellation
        with patch("killua.cogs.message.ConfirmView") as MockView:
            mock_view_instance = MagicMock()
            mock_view_instance.value = False  # User cancels
            mock_view_instance.wait = AsyncMock()
            MockView.return_value = mock_view_instance
            
            await self.cog.user_tracking.callback(self.cog, interaction)

        # Should show confirmation view
        assert interaction.response.is_done(), "Expected confirmation prompt"
        
        # tracking should still be enabled after cancellation
        user_after = await User.new(self.base_author.id)
        assert user_after.message_tracking_enabled == True, "Expected tracking to still be enabled after cancel"
        assert guild.get_message_count(self.base_author.id) == 50, "Expected message count to remain unchanged after cancel"
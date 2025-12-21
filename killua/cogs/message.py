import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from killua.bot import BaseBot
from killua.utils.classes.guild import Guild
from killua.utils.classes.user import User
from killua.utils.views import ConfirmView

TRACKING_SINCE = "2025-12-21"  # The date message tracking was added MUST BE UPDATED IF DEPLOYED

class Message(commands.GroupCog, group_name="message"):
    """Cog to handle stats commands"""

    def __init__(self, client: BaseBot):
        self.client = client

    @app_commands.command(name="stats", description="Get message stats for a user in this guild")
    @app_commands.describe(
        user="View stats for a specific user",
    )
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 5.0)
    async def stats(
        self, 
        interaction: discord.Interaction, 
        user: discord.Member = None,
    ):
        """View message stats for a user or top users in the guild."""
        await interaction.response.defer()

        guild = await Guild.new(interaction.guild.id)
        if not guild.message_tracking_enabled:
            await interaction.followup.send("❌ Message tracking is disabled for this server.", ephemeral=True)
            return

        if not user:
            user = interaction.user

        member = await User.new(user.id)
        if not member.message_tracking_enabled:
            await interaction.followup.send(f"❌ {user.mention} has disabled message tracking for their account.", ephemeral=True)
            return
    
        await self._show_user_stats(interaction, guild, user)

    @app_commands.command(name="leaderboard", description="Show the message leaderboard for this guild")
    @app_commands.describe(
        limit="Number of top users to display (max 25)",
    )
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 10.0)
    async def leaderboard(
        self,
        interaction: discord.Interaction,
        limit: int = 10,
    ):
        """Display the message leaderboard for this guild."""
        await interaction.response.defer()

        guild = await Guild.new(interaction.guild.id)
        if not guild.message_tracking_enabled:
            await interaction.followup.send("❌ Message tracking is disabled for this server.", ephemeral=True)
            return
        await self._show_leaderboard(interaction, guild, limit)

    @app_commands.command(name="server_tracking", description="Toggle message tracking for this server")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    async def server_tracking(
        self,
        interaction: discord.Interaction,
    ):
        """Toggle message tracking for this server"""
        await interaction.response.defer(ephemeral=True)

        guild = await Guild.new(interaction.guild.id)

        if guild.message_tracking_enabled:
            embed = discord.Embed(
                title="⚠️ Warning",
                description="Disabling message tracking will remove all message counts from this server's stats and leaderboards. Are you sure you want to proceed?",
                color=discord.Color.orange()
            )
            view = ConfirmView(interaction.user.id)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            await view.wait()

            if not view.value:
                return # cancelled

        new_status = await guild.toggle_message_tracking()
        if new_status:
            embed = discord.Embed(
                title="✅ Message Tracking Enabled",
                description="Message tracking has been enabled for this server. Future messages from users who have enabled message tracking will be counted in stats and leaderboards.",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="❌ Message Tracking Disabled",
                description="Message tracking has been disabled for this server. All message counts have been removed from stats and leaderboards.",
                color=discord.Color.red()
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="user_tracking", description="Toggle message tracking for your account")
    @app_commands.checks.cooldown(1, 10.0)
    async def user_tracking(
        self,
        interaction: discord.Interaction,
    ):
        """Toggle message tracking for your account"""
        user = await User.new(interaction.user.id)

        if user.message_tracking_enabled:
            embed = discord.Embed(
                title="⚠️ Warning",
                description="Disabling message tracking will remove your message counts from all guild leaderboards and stats. Are you sure you want to proceed?",
                color=discord.Color.orange()
            )
            view = ConfirmView(interaction.user.id)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            await view.wait()

            if not view.value:
                return # cancelled

        new_status = await user.toggle_message_tracking()

        if new_status:
            embed = discord.Embed(
                title="✅ Message Tracking Enabled",
                description="You have enabled message tracking for your account. Your future messages will be counted in guild stats and leaderboards.",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="❌ Message Tracking Disabled",
                description="You have disabled message tracking for your account. Your message counts have been removed from all guild stats and leaderboards.",
                color=discord.Color.red()
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    async def _show_user_stats(
        self, 
        interaction: discord.Interaction, 
        guild: Guild, 
        member: discord.Member
    ):
        """Display stats for a specific user"""
        message_count = guild.get_message_count(member.id)
        rank = await guild.get_user_rank(member.id)
        total_messages = await guild.get_total_messages()

        embed = discord.Embed(
                title="📊 Message Stats",
                description=f"Stats for {member.mention} in **{interaction.guild.name}**",
                color=discord.Color.blue()
            )

        if message_count == 0:
            embed.add_field(
                name="No Messages",
                value=f"{member.mention} has not sent any messages in this guild.",
                inline=False
            )
        else:
            percentage = (message_count / total_messages) * 100 if total_messages > 0 else 0

            embed.add_field(name="Messages Sent", value=f"{message_count:,}", inline=True)
            embed.add_field(name="Rank", value=f"#{rank}", inline=True)
            embed.add_field(name="Percentage of Total Messages", value=f"{percentage:.2f}%", inline=True)
            
        embed.set_footer(text=f"Tracking since {TRACKING_SINCE} • Requested by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        await interaction.followup.send(embed=embed)
    
    async def _show_leaderboard(
        self,
        interaction: discord.Interaction,
        guild: Guild,
        limit: int
    ):
        """Display the message leaderboard for the guild"""
        
        if limit < 1 or limit > 25:
            await interaction.followup.send("❌ Limit must be between 1 and 25.", ephemeral=True)
            return
        
        top_senders = await guild.get_top_senders(limit)
        total_messages = await guild.get_total_messages()

        embed = discord.Embed(
                title="📊 Message Leaderboard",
                description=f"Top {limit} message senders in **{interaction.guild.name}**",
                color=discord.Color.blue()
            )

        if not top_senders:
            embed.add_field(
                name="No Data",
                value="No message data available for this guild.",
                inline=False
            )
        else:
            leaderboard = ""
            for rank, (user_id, message_count) in enumerate(top_senders, start=1):
                member = interaction.guild.get_member(user_id)
                if member is None:
                    try:
                        member = await interaction.guild.fetch_member(user_id)
                    except (discord.NotFound, discord.HTTPException):
                        pass
                member_name = member.display_name if member else f"User ID {user_id}"
                percentage = (message_count / total_messages) * 100 if total_messages > 0 else 0

                medal = f"#{rank}"
                if rank == 1:
                    medal = "🥇 "
                elif rank == 2:
                    medal = "🥈 "
                elif rank == 3:
                    medal = "🥉 "

                leaderboard += f"**{medal}**- {member_name}: {message_count:,} messages ({percentage:.2f}%)\n"

            embed.add_field(name="Leaderboard", value=leaderboard, inline=False)

        embed.set_footer(text="Tracking since {TRACKING_SINCE} • Requested by " + interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        await interaction.followup.send(embed=embed)

    @stats.error
    async def stats_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError
    ):
        """Error handler for the stats command"""
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"⏳ This command is on cooldown. Please try again in {error.retry_after:.1f} seconds.",
                ephemeral=True
            )
        else:
            raise error
        
Cog = Message
import discord
from discord.ext import commands
from typing import List, Union
from datetime import datetime

from killua.bot import BaseBot
from killua.utils.converters import TimeConverter
from killua.utils.checks import check
from killua.utils.classes import Guild
from killua.static.enums import Category

Choice = discord.app_commands.Choice


class Moderation(commands.GroupCog, group_name="mod"):

    def __init__(self, client: BaseBot):
        self.client = client

    async def check_perms(
        self, ctx: commands.Context, member: discord.Member
    ) -> Union[None, discord.Message]:
        if member == ctx.me:
            return await ctx.send("Hey!", ephemeral=True)

        if member == ctx.author:
            return await ctx.send(
                f"You can't {ctx.command.name} yourself!", ephemeral=True
            )

        if ctx.author.top_role < member.top_role:
            return await ctx.send(
                f"You can't {ctx.command.name} someone with a higher role than you",
                ephemeral=True,
            )

        if ctx.me.top_role < member.top_role:
            return await ctx.send(
                f"My role needs to be moved higher up to grant me permission to {ctx.command.name} this person",
                ephemeral=True,
            )
        return None

    @check()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    @commands.hybrid_command(
        extras={"category": Category.MODERATION, "id": 61}, usage="ban <user> <reason>"
    )
    @discord.app_commands.describe(
        member="The member to ban",
        delete_days="The number of days worth of messages to delete",
        config="The options on notifying the user",
        reason="The reason for the ban",
    )
    @discord.app_commands.choices(
        config=[
            Choice(name="Send no dm", value=0),
            Choice(name="Send dm on ban", value=1),
            Choice(name="Send dm on ban with acting moderator", value=2),
        ]
    )
    async def ban(
        self,
        ctx: commands.Context,
        member: str,
        delete_days: int = 1,
        config: Choice[
            int
        ] = 1,  # This is unusable with message commands either way so I am not making it compatible
        *,
        reason: str = None,
    ):
        """Bans a user from the server."""
        try:
            member = await commands.MemberConverter().convert(ctx, member)
        except commands.MemberNotFound:
            if member.isdigit():
                try:
                    await ctx.guild.ban(discord.Object(id=member))
                    user = self.client.get_user(member) or await self.client.fetch_user(
                        member
                    )
                    return await ctx.send(
                        f":hammer: Banned **{user}** because of: ```\n{reason or 'No reason provided'}```Operating moderator: **{ctx.author}**"
                    )
                except discord.HTTPException:
                    return await ctx.send(
                        "Something went wrong! Did you specify a valid user id?",
                        ephemeral=True,
                    )
            else:
                return await ctx.send("Invalid user!", ephemeral=True)

        r = await self.check_perms(ctx, member)
        if r:
            return

        if config in [1, 2]:
            try:
                await member.send(
                    f"You have been banned from {ctx.guild.name} because of: ```\n{reason or 'No reason provided'}```"
                    + f" by `{ctx.author}`"
                    if config == 2
                    else ""
                )
            except discord.HTTPException:
                pass

        await member.ban(reason=reason, delete_message_days=delete_days)
        await ctx.send(
            f":hammer: Banned **{member}** because of: ```\n{reason or 'No reason provided'}```Operating moderator: **{ctx.author}**"
        )

    @check()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True, view_audit_log=True)
    @commands.hybrid_command(
        extras={"category": Category.MODERATION, "id": 62}, usage="unban <user>"
    )
    @discord.app_commands.describe(member="The member to be unbanned")
    async def unban(self, ctx: commands.Context, *, member: str):
        """Unbans a user by ID or by username, meaning `unban k1le` will also work"""
        if member.isdigit():
            try:
                user = discord.Object(id=int(member))
                await ctx.guild.unban(user)
                await ctx.send(
                    f":ok_hand: Unbanned user with id **{member}**\nOperating moderator: **{ctx.author}**"
                )
            except discord.HTTPException as e:
                if e.code == 10013:
                    return await ctx.send(f"No user with the user ID {member} found")
                if e.code == 10026:
                    return await ctx.send("The user is not currently banned")
        else:
            async for ban in ctx.guild.bans(
                limit=100
            ):
                if ban.user.name == member:
                    await ctx.guild.unban(ban)
                    return await ctx.send(
                        f":ok_hand: Unbanned {ban.user.mention}\nOperating moderator: **{ctx.author}**"
                    )
            return await ctx.send("User is not currently banned (are you sure it is the username and not display name?)")

    @check()
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    @commands.hybrid_command(
        extras={"category": Category.MODERATION, "id": 63}, usage="kick <user> <reason>"
    )
    @discord.app_commands.describe(
        member="The member to be kicked", reason="The reason for the kick"
    )
    @discord.app_commands.choices(
        config=[
            Choice(name="Send no dm", value=0),
            Choice(name="Send dm on kick", value=1),
            Choice(name="Send dm on kick with acting moderator", value=2),
        ]
    )
    async def kick(
        self,
        ctx: commands.Context,
        member: discord.Member,
        config: Choice[
            int
        ] = 1,  # This is unusable with message commands either way so I am not making it compatible
        *,
        reason: str = None,
    ):
        """Kicks a user from the server."""

        r = await self.check_perms(ctx, member)
        if r:
            return

        if config in [1, 2]:
            try:
                await member.send(
                    f"You have been kicked from {ctx.guild.name} because of: ```\n{reason or 'No reason provided'}```"
                    + f" by `{ctx.author}`"
                    if config == 2
                    else ""
                )
            except discord.HTTPException:
                pass

        await member.kick(reason=reason or "No reason provided")
        await ctx.send(
            f":hammer: Kicked **{member}** because of: ```\n{reason or 'No reason provided'}```Operating moderator: **{ctx.author}**"
        )

    async def shush_autocomplete(
        self, _: discord.Interaction, current: str
    ) -> List[Choice[TimeConverter]]:
        """
        Autocomplete for shush command
        """
        times = ["1m", "5m", "10m", "30m", "1h", "12h", "1d", "7d"]
        return list(
            [
                Choice(name=opt, value=opt)
                for opt in times
                if opt.lower().startswith(current.lower())
            ]
        )

    @check()
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    @commands.hybrid_command(
        extras={"category": Category.MODERATION, "id": 64},
        usage="shush <time> <reason>",
    )
    @discord.app_commands.describe(
        member="The member to be shushed",
        time="The time until the shush expires",
        reason="Reason for the shush",
    )
    @discord.app_commands.autocomplete(time=shush_autocomplete)
    async def shush(
        self,
        ctx: commands.Context,
        member: discord.Member,
        time: TimeConverter,
        *,
        reason: str = None,
    ):
        """\U0001f90f Timeout a user for a specified time"""

        r = await self.check_perms(ctx, member)
        if r:
            return

        await member.timeout(time, reason=reason or "No reason provided")
        await ctx.send(
            f":pinching_hand: Timeouted {member} until <t:{int((datetime.now() + time).timestamp())}:R> for: ```\n{reason or 'No reason provided'}```Operating moderator: **{ctx.author}**"
        )

    @check()
    @commands.hybrid_command(
        extras={"category": Category.MODERATION, "id": 65},
        usage="unshush <user> <reason(optional)>",
    )
    @discord.app_commands.describe(
        member="The member to be unshushed", reason="The reason for the unshush"
    )
    async def unshush(
        self, ctx: commands.Context, member: discord.Member, *, reason: str = None
    ):
        """\U0001f444 Removes a timeout from a user"""

        r = await self.check_perms(ctx, member)
        if r:
            return

        if not member.is_timed_out():
            return await ctx.send("This user is not timed out", ephemeral=True)

        await member.timeout(None, reason=reason)

        await ctx.send(f":lips: Removed the timeout from {member}")

    @check()
    @commands.hybrid_command(
        extras={"category": Category.MODERATION, "id": 66},
        usage="prefix <new_prefix(optional)>",
    )
    @discord.app_commands.describe(prefix="The new message command prefix")
    async def prefix(self, ctx: commands.Context, prefix: str = None):
        """Change Killua's prefix with this command."""

        guild = await Guild.new(ctx.guild.id)

        if ctx.author.guild_permissions.administrator and prefix:
            await guild.change_prefix(prefix)
            return await ctx.send(
                f"Successfully changed server prefix to `{prefix}`!",
                allowed_mentions=discord.AllowedMentions.none(),
            )

        elif ctx.author.guild_permissions.administrator is False and prefix:
            return await ctx.send(
                "You need `administrator` permissions to change the server prefix!"
            )

        await ctx.send(
            f"The current server prefix is `{guild.prefix}`",
            allowed_mentions=discord.AllowedMentions.none(),
        )


Cog = Moderation

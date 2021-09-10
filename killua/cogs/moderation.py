import discord 
import asyncio
from discord.utils import find
from discord.ext import commands
from killua.checks import check
from killua.classes import Category, Guild
import typing

class Moderation(commands.Cog):

    def __init__(self, client):
        self.client = client
    
    async def check_perms(self, ctx, member):
        if member == ctx.me:
            return await ctx.send('Hey!')
      
        if member == ctx.author:
            return await ctx.send(f'You can\'t {ctx.command.name} yourself!')

        if ctx.author.top_role < member.top_role:
                return await ctx.send(f'You can\'t {ctx.command.name} someone with a higher role than you')

        if ctx.me.top_role < member.top_role:
            return await ctx.send(f'My role needs to be moved higher up to grant me permission to {ctx.command.name} this person')
        return None

    @check()
    @commands.command(extras={"category":Category.MODERATION}, usage="ban <user> <reason>")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx, member: typing.Union[discord.Member, int], *,reason=None):
        """What you would expect of a ban command, bans a user and deletes all their messages of the last 24 hours, optional reason"""
    
        if isinstance(member, int):
            try:
                await ctx.guild.ban(discord.Object(id=member))
                user = self.client.get_user(member) or await self.client.fetch_user(member)
                return await ctx.send(f':hammer: Banned **{user}** because of: ```\n{reason or "No reason provided"}```Operating moderator: **{ctx.author}**')
            except discord.HTTPException:
                return await ctx.send("Something went wrong! Did you specify a valid user id?")

        r = await self.check_perms(ctx, member)
        if r: return

        try:
            await member.send(f'You have been banned from {ctx.guild.name} because of: ```\n{reason or "No reason provided"}```by `{ctx.author}`')
        except discord.HTTPException:
            pass

        await member.ban(reason=reason, delete_message_days=1)
        await ctx.send(f':hammer: Banned **{member}** because of: ```\n{reason or "No reason provided"}```Operating moderator: **{ctx.author}**')
   
    
    @check()
    @commands.command(extras={"category":Category.MODERATION}, usage="unban <user>")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True, view_audit_log=True)
    async def unban(self, ctx, *, member:typing.Union[int, str]):
        """Unbans a user by ID **or**, which is unique, by tag, meaning k!unban Kile#0606 will work"""
        banned_users = await ctx.guild.bans()
    
        if isinstance(member, int):
            try:
                user = discord.Object(id=int(member))
                await ctx.guild.unban(user)
                await ctx.send(f':ok_hand: Unbanned user with id **{member}**\nOperating moderator: **{ctx.author}**')
            except discord.HTTPException as e:
                if e.code == 10013:
                    return await ctx.send(f'No user with the user ID {member} found')
                if e.code == 10026:
                    return await ctx.send('The user is not currently banned')

        else:
            data = member.split("#")
            if len(data) != 2:
                return await ctx.send("Invalid user specified! (Did you not use the User#0000 format or does the user have a # in their name?)")
            member_name, member_discriminator = data
    
            loopround = 0

            for ban_entry in banned_users:
                bannedtotal = len(banned_users)
                user = ban_entry.user
        
                if (user.name, user.discriminator) == (member_name, member_discriminator):
                    await ctx.guild.unban(user)
                    return await ctx.send(f':ok_hand: Unbanned {user.mention}\nOperating moderator: **{ctx.author}**')

                loopround = loopround+1
                if loopround == bannedtotal:
                    return await ctx.send('User is not currently banned')

    @check()
    @commands.command(extras={"category":Category.MODERATION}, usage="kick <user> <reason>")
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *,reason=None):
        """What you would expect of a kick command, kicks a user, optional reason"""

        r = await self.check_perms(ctx, member)
        if r:
            return
        try:
            await member.send(f'You have been kicked from {ctx.guild.name} because of: ```\n{reason or "No reason provided"}```by `{ctx.author}`')
        except discord.HTTPException:
            pass

        await member.kick(reason=reason or "No reason provided")
        await ctx.send(f':hammer: Kicked **{member}** because of: ```\n{reason or "No reason provided"}```Operating moderator: **{ctx.author}**')
        
    @check()
    @commands.command(extras={"category":Category.MODERATION}, usage="mute <time/u> <reason>")
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def mute(self, ctx, member: discord.Member, timem=None, *,reason=None):
        """Mutes a user for the specified duration or unlimited. Requirements: You need to have a role named `muted` (Case insensitve) set up already (Deny this role permission to send messages in every channel)"""

        r = await self.check_perms(ctx, member)
        if r:
            return

        muted = find(lambda r: r.name.lower() == 'muted', ctx.guild.roles)

        if muted is None:
            return await ctx.send('There is no rule called `muted` so I can\'t mute that user')

        if muted in member.roles:
            return await ctx.send("This user is already muted!")

        if muted > ctx.me.top_role:
            return await ctx.send('I need to be moved on top of the muted role or higher')
        
        if timem:
            if (digit:=timem.isdigit()) or timem.lower() in ["standart", "unlimited", "u", "s"]:

                if digit and (int(timem) > 1440 or int(timem) < 0):
                    return await ctx.send('The most time a user can be muted is a day or unlimited and the least is a minute')

                await member.add_roles(muted, reason=reason or "No reason provided")
                try:
                    await member.send(f'You have been muted in {ctx.guild.name} for the duration of {timem if digit else "`unlimited`"} minute{"s" if (digit and int(timem) !=1) or not digit else ""} by `{ctx.author}`. Reason: ```\n{reason or "No reason provided"}```')
                except discord.HTTPException:
                    pass

                await ctx.send(f':pinching_hand: Muted **{member}** for {timem if digit else "`unlimited`"} minute{"s" if (digit and int(timem) !=1) or not digit else ""}. Reason:```\n{reason or "No reason provided"}``` Operating moderator: **{ctx.author}**')
                    
                if digit: # in case a time was specified
                    await asyncio.sleep(int(timem) * 60)
                    try:
                        await member.remove_roles(muted, reason='Mute time expired')
                        await member.send(f'You have been unmuted in {ctx.guild.name}, reason: mute time expired')
                    except discord.HTTPException:
                        pass
                return
            else:
                reason = (timem + " " + (reason or ""))

        await member.add_roles(muted, reason=reason or "No reason")
        try:
            await member.send(f'You have been muted in {ctx.guild.name} by `{ctx.author}`. Reason: ```\n{reason or "No reason provided"}```')  
        except discord.HTTPException:
            pass
        await ctx.send(f':pinching_hand: Muted **{member}**. Reason:```\n{reason or "No reason provided"}``` Operating moderator: **{ctx.author}**')    
        
    @check()                  
    @commands.command(extras={"category":Category.MODERATION}, usage="unmute <user> <reason(optional)>")
    async def unmute(self, ctx, member: discord.Member, *, reason=None):
        """Unmutes a user if they have a `muted` (case insensitve) role"""

        r = await self.check_perms(ctx, member)
        if r:
            return

        muted = find(lambda r: r.name.lower() == 'muted', ctx.guild.roles)

        if muted is None:
            return await ctx.send('There is no rule called `muted` (Case insensitive) so I can\'t unmute that user')

        if muted > ctx.me.top_role:
            return await ctx.send('I need to be moved on top of the muted role or higher')

        if not muted in member.roles:
            return await ctx.send("This user is not currently muted")

        await member.remove_roles(muted, reason=reason or "No reason provided")
        try:
            await member.send(f'You have been unmuted in {ctx.guild.name} by `{ctx.author}`. Reason: ```\n{reason or "No reason provided"}```')  
        except discord.HTTPException:
            pass
        return await ctx.send(f':lips: Unmuted **{member}** Reason:```\n{reason or "No reason provided"}``` Operating moderator: **{ctx.author}**')

    @check()
    @commands.command(extras={"category":Category.MODERATION}, usage="prefix <new_prefix(optional)>")
    async def prefix(self, ctx, pref:str=None):
        """Change Killua's prefix with this command. If you forgot your prefix, mentioning is always a prefix as well"""

        guild = Guild(ctx.guild.id)

        if ctx.author.guild_permissions.administrator and pref:
            guild.change_prefix(pref)
            return await ctx.send(f'Successfully changed server prefix to `{pref}`!', allowed_mentions=discord.AllowedMentions.none())

        elif ctx.author.guild_permissions.administrator is False and pref:
            return await ctx.send('You need `administrator` permissions to change the server prefix!')

        await ctx.send(f'The current server prefix is `{guild.prefix}`', allowed_mentions=discord.AllowedMentions.none())


Cog = Moderation        
              
def setup(client):
    client.add_cog(Moderation(client))

import discord 
import asyncio
from discord.utils import find
from discord.ext import commands
from killua.functions import check
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
    @commands.command()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx, member: typing.Union[discord.Member, int], *,reason=None):
        #h What you would expect of a ban command, bans a user and deletes all their messages of the last 24 hours, optional reason
        #u ban <user> <reason>
    
        if isinstance(member, int):
            try:
                await ctx.guild.ban(discord.Object(id=member))
                user = await self.client.fetch_user(member)
                return await ctx.send(f':hammer: Banned **{user}** because of: ```\n{reason or "No reason provided"}```Operating moderator: **{ctx.author}**')
            except Exception as e:
                return await ctx.send(e)

        r = await self.check_perms(ctx, member)
        if r:
            return
        try:
            await member.send(f'You have been banned from {ctx.guild.name} because of: ```\n{reason or "No reason provided"}```by `{ctx.author}`')
        except discord.HTTPException:
            pass

        await member.ban(reason=reason, delete_message_days=1)
        await ctx.send(f':hammer: Banned **{member}** because of: ```\n{reason or "No reason provided"}```Operating moderator: **{ctx.author}**')
   
    
    @check()
    @commands.command()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True, view_audit_log=True)
    async def unban(self, ctx, *, member:typing.Union[str, int]):
        #t 1 hour
        #h Unbans a user by ID **or**, which is unique, by tag, meaning k!unban Kile#0606 will work :3
        #u unban <user>
        banned_users = await ctx.guild.bans()
    
        if isinstance(member, int):
            try:
                user = discord.Object(id=int(member))
                await ctx.guild.unban(user)
                await ctx.send(f':ok_hand: Unbanned **{user}**\nOperating moderator: **{ctx.author}**')
            except discord.HTTPException as e:
                if e.code == 10013:
                    return await ctx.send(f'No user with the user ID {member} found')
                if e.code == 10026:
                    return await ctx.send('The user is not currently banned')

        else:
            member_name, member_discriminator = member.split("#")
    
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
    @commands.command()
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *,reason=None):

        #h What you would expect of a kick command, kicks a user, optional reason
        #u kick <user> <reason>
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
    @commands.command()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def mute(self, ctx, member: discord.Member, timem=None, *,reason=None):

        #h Mutes a user for the specified duration or unlimited. Requirements: You need to have a role named `muted` (Case insensitve) set up already (Deny this role permission to send messages in every channel)
        #u mute <user> <time/u> <reason> 

        r = await self.check_perms(ctx, member)
        if r:
            return

        muted = find(lambda r: r.name.lower() == 'muted', ctx.guild.roles)

        if muted > ctx.me.top_role:
            return await ctx.send('I need to be moved on top of the muted role or higher')

        if muted is None:
            return await ctx.send('There is no rule called `muted` so I can\'t mute that user')
        
        if timem:
            string = False

            if timem.isdigit() is True:
                pass

            else:
                if timem.lower() == 'unlimited' or timem.lower() == 'standart' or timem.lower() == 'u' or timem.lower() == 's':
                    string = True
                else:
                    return await ctx.send('The `time`argument needs to be an integer between 1440 and null or `unlimited`')

            if string is True:
                await member.add_roles(muted, reason=reason or "No reason provided")
                try:
                    await member.send(f'You have been muted in {ctx.guild.name} for the duration of `unlimited` minutes by `{ctx.author}`. Reason: ```\n{reason or "No reason provided"}```')
                except discord.HTTPException:
                    pass

                return await ctx.send(f':pinching_hand: Muted **{member}** for  `unlimited` minutes. Reason:```\n{reason or "No reason provided"}``` Operating moderator: **{ctx.author}**')

            if int(timem) > 1440 or int(timem) < 0:
                return await ctx.send('The most time a user can be muted is a day or unlimited')
                    
            await member.add_roles(muted, reason=reason or "No reason") 
                    
            try:
                await member.send(f'You have been muted in {ctx.guild.name} for the duration of `{timem}` minutes by `{ctx.author}`')
            except discord.HTTPException:
                pass
            await ctx.send(f':pinching_hand: Muted **{member}** for  `{timem}` minutes. Reason:```\n{reason or "No reason provided"}``` Operating moderator: **{ctx.author}**')
            await asyncio.sleep(int(timem) * 60)

            try:
                await member.remove_roles(muted, reason='Mute time expired')
                await member.send(f'You have been unmuted in {ctx.guild.name}, reason: mute time expired')
            except discord.HTTPException:
                pass
        else:
            await member.add_roles(muted,reason=reason or "No reason")
            try:
                await member.send(f'You have been muted in {ctx.guild.name} for the duration of `unlimited` minutes by `{ctx.author}`. Reason: ```\n{reason or "No reason provided"}```')  
            except discord.HTTPException:
                pass
            await ctx.send(f':pinching_hand: Muted **{member}** for  `unlimited` minutes. Reason:```\n{reason or "No reason provided"}``` Operating moderator: **{ctx.author}**')    
        
    @check()                  
    @commands.command()
    async def unmute(self, ctx, member: discord.Member, *, reason=None):

        #h Unmutes a user if they have a `muted` (case insensitve) role
        #u unmute <user> <reason(optional)>
        r = await self.check_perms(ctx, member)
        if r:
            return

        muted = find(lambda r: r.name.lower() == 'muted', ctx.guild.roles)

        if muted > ctx.me.top_role:
            return await ctx.send('I need to be moved on top of the muted role or higher')

        if muted is None:
            return await ctx.send('There is no rule called `muted` (Case insensitive) so I can\'t unmute that user')

        if not muted in member.roles:
            return await ctx.send("This user is not currently muted")

        await member.remove_roles(muted, reason=reason or "No reason provided")
        try:
            await member.send(f'You have been unmuted in {ctx.guild.name} by `{ctx.author}`. Reason: ```\n{reason or "No reason provided"}```')  
        except discord.HTTPException:
            pass
        return await ctx.send(f':lips: Unmuted **{member}** Reason:```\n{reason or "No reason provided"}``` Operating moderator: **{ctx.author}**')


Cog = Moderation        
              
def setup(client):
    client.add_cog(Moderation(client))

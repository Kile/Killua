import discord 
import asyncio
from discord.ext import commands


class moderation(commands.Cog):


  def __init__(self, client):
    self.client = client
    
  @commands.command()
  async def ban(self, ctx, member: discord.Member, *,reason=None):
    #t 30 minutes
    #h What you would expect of a ban command, bans a user and deletes all their messages of the last 24 hours, optional reason
    
    if member.id == 756206646396452975:
            return await ctx.send('Hey!')

    if ctx.channel.permissions_for(ctx.author).ban_members == False:
        return await ctx.send('Nice try but you don\'t have the required permission (`ban members`) to execute this command')
      
    if member.id == ctx.author.id:
        return await ctx.send('You can\'t ban yourself!')

    if ctx.author.top_role < member.top_role:
        return await ctx.send('You can\'t ban someone with a higher role than you')

    if ctx.me.top_role < member.top_role:
        return await ctx.send('My role needs to be moved higher up to grant me permission to ban this person')

    if ctx.channel.permissions_for(ctx.me).ban_members == False:
        return await ctx.send('I don\t have the permission to ban members yet')
        
    try:
        await member.send(f'You have been banned from {ctx.guild.name} because of: ```\n{reason}```by `{ctx.author}`')
    except discord.Forbidden:
        pass

    await member.ban(reason=reason, delete_message_days=1)
    await ctx.send(f':hammer: Banned **{member}** because of: ```\n{reason}```Operating moderator: **{ctx.author}**')
    
    

  @commands.command()
  async def unban(self, ctx, *, member):
    #t 1 hour
    #h Unbans a user by ID **or**, which is unique, by tag, meaning k!unban Kile#0606 will work :3
    banned_users = await ctx.guild.bans()

    if ctx.channel.permissions_for(ctx.author).ban_members == False:
        return await ctx.send('You do not have the permission to unban users')

    if ctx.channel.permissions_for(ctx.me).ban_members == False:
            return await ctx.send('I don\t have the permission to unban members yet, make sure you give me the permission `ban members`')

    if ctx.channel.permissions_for(ctx.me).view_audit_log == False:
            return await ctx.send('I don\t have the permission to view the audit log yet, make sure you give me the permission `view audit log`')

    
    try:
        int(member)
        try:
            user = discord.Object(id=int(member))
            if user is None:
                return await ctx.send(f'No user with the user ID {member} found')
            try:
                await ctx.guild.unban(user)
            except discord.NotFound:
                return await ctx.send('The user is not currently banned')
            await ctx.send(f':ok_hand: Unbanned **{user}**\nOperating moderator: **{ctx.author}**')
        except Exception as e:
            await ctx.send(e)
    except Exception:
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
              
  @commands.command()
  async def kick(self, ctx, member: discord.Member, *,reason=None):
    #t 10 minutes
    #h What you would expect of a kick command, kicks a user, optional reason
    #c Literally copy pasted ban command and changed a view things
   
    if member.id == 756206646396452975:
        return await ctx.send('Hey!')

    if ctx.channel.permissions_for(ctx.author).kick_members == False:
        return await ctx.send('Nice try but you don\'t have the required permission (`kick members`) to execute this command')

    if member.id == ctx.author.id:
        return await ctx.send('You can\'t kick yourself!')

    if ctx.author.top_role < member.top_role:
        return await ctx.send('You can\'t kick someone with a higher role than you')

    if ctx.me.top_role < member.top_role:
        return await ctx.send('My role needs to be moved higher up to grant me permission to kick this person')

    if ctx.channel.permissions_for(ctx.me).kick_members == False:
        return await ctx.send('I don\t have the permission to kick members yet')

    try:
        await member.send(f'You have been kicked from {ctx.guild.name} because of: ```\n{reason}```by `{ctx.author}`')
    except discord.Forbidden:
        pass

    await member.kick(reason=reason)
    await ctx.send(f':hammer: Kicked **{member}** because of: ```\n{reason}```Operating moderator: **{ctx.author}**')

        
        
  @commands.command()
  async def mute(self, ctx, member: discord.Member, timem=None, *,reason=None):

    if member.id == ctx.me.id:
        return await ctx.send('Hey!')

    if ctx.channel.permissions_for(ctx.author).manage_roles == False:
        return await ctx.send('Nice try but you don\'t have the required permission (`manage roles`) to execute this command')

    if member.id == ctx.author.id:
        return await ctx.send('You can\'t mute yourself!')

    if ctx.author.top_role < member.top_role:
        return await ctx.send('You can\'t mute someone with a higher role than you')

    if ctx.me.top_role < member.top_role:
        return await ctx.send('My role needs to be moved higher up to grant me permission to mute this person')

    if ctx.channel.permissions_for(ctx.me).manage_roles == False:
        return await ctx.send('I don\t have the permission to assign roles yet')

    muted = discord.utils.get(ctx.guild.roles, name='muted')

    if muted > ctx.me.top_role:
        return await ctx.send('I need to be moved on top of the muted role or higher')

    if muted is None:
        return await ctx.send('There is no rule called `muted` (Case sensitive!) so I can\'t mute that user')
        
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
            except discord.Forbidden:
                pass

            return await ctx.send(f':pinching_hand: Muted **{member}** for  `unlimited` minutes. Reason:```\n{reason or "No reason provided"}``` Operating moderator: **{ctx.author}**')

        if int(timem) > 1440 or int(timem) < 0:
            return await ctx.send('The most time a user can be muted is a day or unlimited')

                    
        await member.add_roles(muted, reason=reason or "No reason") 
                    
        try:
            await member.send(f'You have been muted in {ctx.guild.name} for the duration of `{timem}` minutes by `{ctx.author}`')
        except discord.Forbidden:
            pass
        await ctx.send(f':pinching_hand: Muted **{member}** for  `{timem}` minutes. Reason:```\n{reason or "No reason provided"}``` Operating moderator: **{ctx.author}**')

        await asyncio.sleep(int(timem) * 60)

        try:
            await member.remove_roles(muted, reason='Mute time expired')
            await member.send(f'You have been unmuted in {ctx.guild.name}, reason: mute time expired')
        except discord.Forbidden:
            pass
    else:
        await member.add_roles(muted,reason=reason or "No reason")
        try:
            await member.send(f'You have been muted in {ctx.guild.name} for the duration of `unlimited` minutes by `{ctx.author}`. Reason: ```\n{reason or "No reason provided"}```')  
        except discord.Forbidden:
            pass
        await ctx.send(f':pinching_hand: Muted **{member}** for  `unlimited` minutes. Reason:```\n{reason or "No reason provided"}``` Operating moderator: **{ctx.author}**')    
        
                           
  @commands.command()
  async def unmute(self, ctx, member: discord.Member, *, reason=None):

    if ctx.channel.permissions_for(ctx.author).manage_roles == False:
        return await ctx.send('Nice try but you don\'t have the required permission (`manage roles`) to execute this command')

    if ctx.author.top_role < member.top_role:
        return await ctx.send('You can\'t unmute someone with a higher role than you')

    if ctx.me.top_role < member.top_role:
        return await ctx.send('My role needs to be moved higher up to grant me permission to unmute this person')

    if ctx.channel.permissions_for(ctx.me).manage_roles == False:
        return await ctx.send('I don\t have the permission to assign roles yet')

    muted = discord.utils.get(ctx.guild.roles, name='muted')

    if muted > ctx.me.top_role:
        return await ctx.send('I need to be moved on top of the muted role or higher')

    if muted is None:
        return await ctx.send('There is no rule called `muted` (Case sensitive!) so I can\'t mute that user')

    await member.remove_roles(muted, reason=reason or "No reason provided")
    try:
        await member.send(f'You have been unmuted in {ctx.guild.name} by `{ctx.author}`. Reason: ```\n{reason or "No reason provided"}```')  
    except discord.Forbidden:
        pass
    return await ctx.send(f':lips: Unmuted **{member}** Reason:```\n{reason or "No reason provided"}``` Operating moderator: **{ctx.author}**')



Cog = moderation

              
              
def setup(client):
  client.add_cog(moderation(client))

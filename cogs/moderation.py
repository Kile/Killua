import discord 
from discord.ext import commands


class moderation(commands.Cog):


  def __init__(self, client):
    self.client = client
    
  @commands.command()
  async def ban(self, ctx, member: discord.Member, *,reason=None):
    #t 30 minutes
    #h What you would expect of a ban command, bans a user and deletes all their messages of the last 24 hours, optional reason

    if ctx.channel.permissions_for(ctx.author).ban_members == True:
        if member.id == self.client.id:
            return await ctx.send('Hey!')
      
        if member.id == ctx.author.id:
            return await ctx.send('You can\'t ban yourself!')

        if ctx.author.top_role < member.top_role:
            return await ctx.send('You can\'t ban someone with a higher role than you')

        if ctx.me.top_role < member.top_role:
            return await ctx.send('My role needs to be moved higher up to grant me permission to ban this person')

        if ctx.channel.permissions_for(ctx.me).ban_members == False:
            return await ctx.send('I don\t have the permission to ban members yet')

        await member.send(f'You have been banned from {ctx.guild.name} because of: ```\n{reason}```by `{ctx.author}`')
        await member.ban(reason=reason, delete_message_days=1)
        await ctx.send(f':hammer: Banned **{member}** because of: ```\n{reason}```Operating moderator: **{ctx.author}**')
    else:
        await ctx.send('Nice try but you don\'t have the required permission (`ban members`) to execute this command')
    

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
                await ctx.send(f':ok_hand: Unbanned {user.mention}\nOperating moderator: **{ctx.author}**')

            loopround = loopround+1
            if loopround == bannedtotal:
                return await ctx.send('User is not currently banned')
              
  @commands.command()
  async def kick(self, ctx, member: discord.Member, *,reason=None):
    #t 10 minutes
    #h What you would expect of a kick command, kicks a user, optional reason
    #c Literally copy pasted ban command and changed a view things

    if ctx.channel.permissions_for(ctx.author).kick_members == True:

        if member.id == self.client.id:
            return await ctx.send('Hey!')

        if member.id == ctx.author.id:
            return await ctx.send('You can\'t kick yourself!')

        if ctx.author.top_role < member.top_role:
            return await ctx.send('You can\'t kick someone with a higher role than you')

        if ctx.me.top_role < member.top_role:
            return await ctx.send('My role needs to be moved higher up to grant me permission to kick this person')

        if ctx.channel.permissions_for(ctx.me).kick_members == False:
            return await ctx.send('I don\t have the permission to kick members yet')

        await member.send(f'You have been kicked from {ctx.guild.name} because of: ```\n{reason}```by `{ctx.author}`')
        await member.kick(reason=reason)
        await ctx.send(f':hammer: Kicked **{member}** because of: ```\n{reason}```Operating moderator: **{ctx.author}**')
    else:
        await ctx.send('Nice try but you don\'t have the required permission (`kick members`) to execute this command')

              
              
def setup(client):
  client.add_cog(moderation(client))

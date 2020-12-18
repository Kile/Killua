import discord
from discord.ext.commands.cooldowns import BucketType
from discord.ext import commands
from functions import custom_cooldown, blcheck


class support(commands.Cog):

  def __init__(self, client):
    self.client = client
    
  @commands.command()
  @commands.cooldown(rate=1, per=3600, type=commands.BucketType.guild)
  async def bug(self, ctx, command=None, *, bug=None):
    if blcheck(ctx.author.id) is True:
        return
    #h Report Killua bugs with this command! For more info on how to report a bug, use `k!bug`.
    #t 1 hour
    if command and bug:
        
        try:
            func = self.client.get_command(command.lower()).callback
        except AttributeError:
            if command.lower != 'other':
                return ctx.send('Command not found. To report bugs not bound to a command, use `other` here')

        if bug is None:
            return await ctx.send('Please tell us what exactly the with the provided command is. For more info on how to do that, use `k!bug`')

        if command.lower() == 'other':
            matter = f'Bug regarding no spefific command'
        else:
            matter = f'Bug regarding the command `{command.lower()}`'

        embed = discord.Embed.from_dict({
            'title': f'Bug report from guild {ctx.guild.name} (ID: {ctx.guild.id})',
            'description': f'''{matter}  \n\n**Provided information:**\n\n{bug}\n\nReported by **{ctx.author}**''',
            'color': 0x1400ff
        })
        
        channel = self.client.get_channel(757201547204493381)

        message = await channel.send(embed=embed)
        await message.add_reaction('\U00002705')
        await message.add_reaction('\U0000274c')

        await ctx.send(':white_check_mark: thanks for reporting a bug! The bug will be looked at as soon as possible!')
    else:
        ctx.command.reset_cooldown(ctx)
        embed = discord.Embed.from_dict({
            'title': f'Bug reporting',
            'description': f'''Report a Killua bug by providing the command where the bug occurs, if it is no command use `other`
        
        After that please describe what should happen and what in reality happens, also how to reproduce the bug. Example:
        
        ```css
k!bug ban Expectation: when I provide no reason the bot says 'no reason' Reality: The bot says 'None' as the reason
        
Reproduction: ban a member without providing a reason```''',
            'color': 0xc21a1a
        })

        await ctx.send(embed=embed)
        
Cog = support

def setup(client):
  client.add_cog(support(client))

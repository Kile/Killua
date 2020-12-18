import discord
from discord.ext import commands
from killua.functions import custom_cooldown, blcheck


class simplereplies(commands.Cog):

  def __init__(self, client):
    self.client = client
    
  @commands.command()
  async def patreon(self, ctx):
    if blcheck(ctx.author.id) is True:
      return
    #c :3
    #t 30 minutes
    #h Get infos about my Patreon and feel free to donate for some perks!
    embed = discord.Embed.from_dict({
        'title': '**Support Killua**',
        'thumbnail':{
            'url': 'https://cdn.discordapp.com/avatars/758031913788375090/e44c0de4678c544e051be22e74bc502d.png?size=1024'},
        'description': 'Hey, do you have too much money? I have a solution for that! I now have a Patreon account where you can donate to support me and get special stuff, helping with building Killua. Not that I expect anyone to do this, but I have it set up now.\n\n https://www.patreon.com/KileAlkuri',
        'color': 0x1400ff
    })
    await ctx.send(embed=embed)
    
  @commands.command()
  async def info(self, ctx):
    if blcheck(ctx.author.id) is True:
      return
    embed = discord.Embed(
        title = 'Info',
        description = ' This is Killua, Kile\'s bot version 0.4.1, the first features simply include ~this command, `k!ping`, `k!hi`, `k!invite`, `k!hug <user>` and `k!topic`, relatively self-explanatory, also a team mode already implemented but not yet finsihed\n I hope to be adding a lot more soon while I figure Python out on the go\n\n **Last time restarted:**\n '+ str(self.client.startup_datetime.strftime('%Y-%m-%d-%H:%M:%S')),
        color = 0x1400ff
    )
    await ctx.send(embed=embed) 
    #c help command
    #t 20 minutes, constantly updating
    #h Gives you some outdated infos about Killua
    
  @commands.command()
  async def invite(self, ctx):
    if blcheck(ctx.author.id) is True:
      return
    #t 5 minutes
    #h Allows you to invite Killua to any guild you have at least `manage server` permissions. **Do it**
    embed = discord.Embed(
        title = 'Invite',
        description = 'Invite the bot to your server [here](https://discord.com/oauth2/authorize?client_id=756206646396452975&scope=bot&permissions=1574431991). Thank you a lot for supporting my Beta phase!',
        color = 0x1400ff
    )
    await ctx.send(embed=embed) 
    
  @commands.command()
  async def guilds(self, ctx):
    if blcheck(ctx.author.id) is True:
      return
    #r user ID: 606162661184372736 or 383790610727043085
    #t 15 minutes
    #h Shows a list of the guilds Killua is on
    if ctx.author.id == 606162661184372736 or ctx.author.id == 383790610727043085:
        embed = discord.Embed(
            title = 'Guilds',
            description = '\n'.join([guild.name for guild in self.client.guilds]),
            color = 0x1400ff
        )
        await ctx.send(embed=embed)
        
  @commands.command()
  @custom_cooldown(6)
  async def permissions(self, ctx):
    if blcheck(ctx.author.id) is True:
      return
    #t 30 min
    #h Displays the permissions Killua has and has not, useful for checking if Killua has the permissions he needs
    perms = ctx.me.guild_permissions
    permissions = '\n'.join([f"{v} {n}" for n, v in perms])
    prettier = permissions.replace('_', ' ').replace('True', '<:CheckMark:771754620673982484>').replace('False', '<:x_:771754157623214080>')
    embed = discord.Embed.from_dict({
            'title': 'Bot permissions',
            'description': prettier,
            'color': 0x1400ff,
            'thumbnail': {'url': str(ctx.me.avatar_url)}
        })
    await ctx.send(embed=embed)
    

Cog = simplereplies

    
def setup(client):
  client.add_cog(simplereplies(client))

import discord
from discord.ext import commands
from killua.functions import custom_cooldown, blcheck


class SimpleReplies(commands.Cog):

  def __init__(self, client):
    self.client = client
    
  @commands.command()
  async def patreon(self, ctx):
    if blcheck(ctx.author.id) is True:
      return
    #c :3
    #t 30 minutes
    #h Get infos about my Patreon and feel free to donate for some perks!
    #u patreon
    embed = discord.Embed.from_dict({
        'title': '**Support Killua**',
        'thumbnail':{
            'url': 'https://cdn.discordapp.com/avatars/758031913788375090/e44c0de4678c544e051be22e74bc502d.png?size=1024'},
        'description': 'Hey, do you have too much money? I have a solution for that! I now have a Patreon account where you can donate to support me and get special stuff, helping with building Killua. Not that I expect anyone to do this, but I have it set up now. Make sure you are on my server before you become a Patreon so you get the perks!\n\n https://www.patreon.com/KileAlkuri',
        'color': 0x1400ff
    })
    await ctx.send(embed=embed)
    
  @commands.command(aliases=['stats'])
  async def info(self, ctx):
    if blcheck(ctx.author.id) is True:
      return
    now = datetime.datetime.now()
    diff = now - self.client.startup_datetime
    t = f'{diff.days} days, {int((diff.seconds/60)/60)} hours, {int(diff.seconds/60)-(int((diff.seconds/60)/60)*60)} minutes and {int(diff.seconds)-(int(diff.seconds/60)*60)} seconds'
    embed = discord.Embed.from_dict({
      'title': f'Infos about {ctx.me.name}',
      'description': f'This is Killua, a bot designed to be a fun multipurpose bot themed after the hxh character Killua. I started this bot when I started learning Python (You can see when on Killua\'s status). This means I am unexperienced and have to go over old buggy code again and again in the process. Thank you all for helping me out by testing Killua, please consider leaving feedback with `k!fb`\n\n**__Bot stats__**\n__Bot uptime:__ `{t}`\n__Bot users:__ `{len(self.client.users)}`\n__Bot guilds:__ `{len(self.client.guilds)}`\n__Bot commands:__ `{len(self.client.commands)}`\n__Owner id:__ `{self.client.owner_id}`\n__Latency:__ `{int(self.client.latency*100)}` ms',
      'color': 0x1400ff,
        'thumbnail': {'url': str(ctx.me.avatar_url)}
    })
    await ctx.send(embed=embed) 
    #c info command
    #t 20 minutes, constantly updating
    #h Gives you some outdated infos about Killua
    #u info
    
  @commands.command()
  async def invite(self, ctx):
    if blcheck(ctx.author.id) is True:
      return
    #t 5 minutes
    #h Allows you to invite Killua to any guild you have at least `manage server` permissions. **Do it**
    #u invite
    embed = discord.Embed(
        title = 'Invite',
        description = 'Invite the bot to your server [here](https://discord.com/oauth2/authorize?client_id=756206646396452975&scope=bot&permissions=268723414). Thank you a lot for supporting me!',
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
    #u permissions
    perms = ctx.me.guild_permissions
    permissions = '\n'.join([f"{v} {n}" for n, v in perms])
    prettier = permissions.replace('_', ' ').replace('True', '<:CheckMark:771754620673982484>').replace('False', '<:x_:771754157623214080>')
    embed = discord.Embed.from_dict({
            'title': 'Bot permissions',
            'description': prettier,
            'color': 0x1400ff,
            'thumbnail': {'url': str(ctx.me.avatar_url)}
        })
    try:
      await ctx.send(embed=embed)
    except: # If embed permission is denied
      await ctx.send('__Bot permissions__\n\n')

  @commands.command()
  async def vote(self, ctx):
    #u vote
    #h Gived you the links you need if you want to support Killua by voting
    if blcheck(ctx.author.id) is True:
        return
    await ctx.send('Thanks for supporting Killua! Vote for him here: https://top.gg/bot/756206646396452975/vote \nAnd here: https://discordbotlist.com/bots/killua/upvote')

    

Cog = SimpleReplies

    
def setup(client):
  client.add_cog(SimpleReplies(client))

import discord
import inspect
import pymongo
import json
from json import loads
from pymongo import MongoClient
from discord.ext import commands
from killua.functions import custom_cooldown, blcheck
with open('config.json', 'r') as config_file:
	config = json.loads(config_file.read())

cluster = MongoClient(config['mongodb'])
db = cluster['Killua']
server = db['guilds']
generaldb = cluster['general']
blacklist = generaldb['blacklist']

class Help(commands.Cog):

  def __init__(self, client):
    self.client = client
    
  @commands.command()
  async def help(self, ctx, group=None, *,command=None):
    if blcheck(ctx.author.id) is True:
      return
  #h This command is the one hopefully letting you know what Killua can do and what his features are, I hope you like how it looks!
  #t 2 hours
  #c 155 lines, help (bad codering)
  #u help <group/command> <command(if command was previous argument)>
    pref = self.client.command_prefix(self.client, ctx.message)[2]
    if group is None and command is None:
            
        embed = discord.Embed.from_dict({
            'title': 'Bot commands',
            'description': f'''Current server Prefix: `{pref}`
Command groups for {ctx.me.name}:
:tools: `Moderation`
:clown: `Fun`
:trophy: `Economy`
:scroll: `todo`
<:card_number_46:811776158966218802>  `Cards`
<:killua_wink:769919176110112778> `Other`
            
To see a groups commands, use```css\nhelp <groupname>```
For more info to a specific command, use
```css\nhelp command <commandname>```

[Support server](https://discord.gg/be4nvwq7rZ)
[Source code](https://github.com/Kile/Killua)
Website: https://killua.dev (a work in progress)''',
            'color': 0x1400ff,
            'thumbnail': {'url': str(ctx.me.avatar_url)}
            })
        await ctx.send(embed=embed)
    elif group:
        if group.lower() in ['moderation', 'fun', 'economy', 'other', 'command', 'todo', 'cards']:
            if command and group.lower() == 'command':
                try:
                    func = self.client.get_command(command).callback
                    code = inspect.getsource(func)
                    linecount = code.splitlines()

                    restricted = ''
                    desc = 'No description yet'


                    for item in linecount:
                        first, middle, last = item.partition("#h")
                        firstr, middler, lastr = item.partition("#r")
                        firstu, middleu, lastu = item.partition("#u")
                        if lastr is None or lastr == '':
                            restricted = ''
                        else:
                            retricted = f'\n\nCommand restricted to: {lastr}'

                        if last and last != '")':
                            desc = last
                        
                    embed = discord.Embed.from_dict({
                        'title': f'Info about command `k!{command}`',
                        'description': f'{desc} {restricted}\nUsage:```markdown\n{pref}{lastu}\n```',
                        'color': 0x1400ff,
                        'thumbnail': {'url': str(ctx.me.avatar_url)}
                        })
                    await ctx.send(embed=embed)                    

                except Exception as e:
                    await ctx.send('Command not found')
            else:
                embed = commands(group, pref)
                embed.color = 0x1400ff
                embed.set_thumbnail(url= str(ctx.me.avatar_url))
                await ctx.send(embed=embed)
        else:
            await ctx.send('Not a valid group, please make sure you know what groups are available')

'''function commands
Input:
commandgroup: The group specified using the command

Returns:
embed: Embed with a list of the commands in that group

Purpose:
To get the right command without having a giant help command
'''

def commands(commandgroup, pref:str):
    if commandgroup.lower() == 'command':
        embed = discord.Embed.from_dict({'description': 'You need to input a command to see it\'s information'
            })
        return embed

    if commandgroup.lower() == 'moderation':
        embed = discord.Embed.from_dict({
            'title': 'Moderation commands',
            'description': '`prefix`, `ban`, `kick`, `unban`, `mute`, `unmute`',
            'footer': {'text': f'For more info to a command use {pref}help command <command>'},
            'color': 0x1400ff
        })
        return embed

    if commandgroup.lower() == 'fun':
        embed = discord.Embed.from_dict({
            'title': 'Fun commands',
            'description': '`quote`, `cmm`, `hug`, `pat`, `topic`, `calc`, `translate`, `8ball`, `avatar`, `novel`, `emojaic`, `image`, `rps`, `f`',
            'footer': {'text': f'For more info to a command use {pref}help command <command>'},
            'color': 0x1400ff

        })
        return embed

    if commandgroup.lower() == 'economy':
        embed = discord.Embed.from_dict({

            'title': 'Economy commands',
            'description': '`daily`, `profile`, `give`, `server`, `bal`',
            'footer': {'text': f'For more info to a command use {pref}help command <command>'},
            'color': 0x1400ff


        })
        return embed

    if commandgroup.lower() == 'other':
        embed = discord.Embed.from_dict({
            'title': 'Other commands',
            'description': '`info`, `patreon`, `invite`, `codeinfo`, `permissions`, `bug`, `feedback`',
            'footer': {'text': f'For more info to a command use {pref}help command <command>'},
            'color': 0x1400ff
        })
        return embed

    if commandgroup.lower() == 'todo':
        embed = discord.Embed.from_dict({
            'title': 'todo commands',
            'description': f'**Every command on this list starts with `{pref}todo`**\n\n`create`, `lists`, `shop`, `edit`, `info`, `buy`, `add`, `remove`, `mark`, `invite`, `view`, `kick`, `status`, `name`, `autodelete`, `color`, `thumbnail`, `custom_id`, `assign`, `delete`, `exit`',
            'footer': {'text': f'For more info to a command use {pref}help command <command>'},
            'color': 0x1400ff
        })
        return embed

    if commandgroup.lower() == 'cards':
        embed = discord.Embed.from_dict({
            'title': 'Card commands',
            'description': f'Use `{pref}use booklet` for an introduction\n\n`book`, `shop`, `buy`, `sell`, `swap`, `hunt`, `meet`, `discard`, `use`',
            'footer': {'text': f'For more info to a command use {pref}help command <command>'},
            'color': 0x1400ff
        })
        return embed


Cog = Help

def setup(client):
    client.add_cog(Help(client))

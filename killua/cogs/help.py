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

class h(commands.Cog):

  def __init__(self, client):
    self.client = client
    
  @commands.command()
  async def help(self, ctx, group=None, command=None):
    if blcheck(ctx.author.id) is True:
      return
  #h This command is the one hopefully letting you know what Killua can do and what his features are, I hope you like how it looks!
  #t 2 hours
  #c 155 lines, help
    if group is None and command is None:
        results = server.find({'id': ctx.guild.id})
        for result in results:
            pref = result['prefix']
            
        embed = discord.Embed.from_dict({
            'title': 'Bot commands',
            'description': f'''Current server Prefix: `{pref}`
Command groups for {ctx.me.name}:
:tools: `Moderation`
:clown: `Fun`
:trophy: `Economy`
:scroll: `todo`
<:killua_wink:769919176110112778> `Other`
            
To see a groups commands, use```css\nhelp <groupname>```
For more info to a specific command, use
```css\nhelp command <commandname>```

[Support server](https://discord.gg/be4nvwq7rZ)
Website: https://killua.dev (a work in progress)''',
            'color': 0x1400ff,
            'thumbnail': {'url': str(ctx.me.avatar_url)}
            })
        await ctx.send(embed=embed)
    elif group:
        if group.lower() in ['moderation', 'fun', 'economy', 'other', 'command', 'todo']:
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

                        if lastr is None or lastr == '':
                            restricted = ''
                        else:
                            retricted = f'\n\nCommand restricted to: {lastr}'

                        if last and last != '")':
                            desc = last
                        
                    embed = discord.Embed.from_dict({
                        'title': f'Info about command `k!{command}`',
                        'description': f'{desc} {restricted}',
                        'color': 0x1400ff,
                        'thumbnail': {'url': str(ctx.me.avatar_url)}
                        })
                    await ctx.send(embed=embed)                    

                except Exception as e:
                    await ctx.send('Command not found')
            else:
                embed = commands(group)
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

def commands(commandgroup):
    if commandgroup.lower() == 'command':
        embed = discord.Embed.from_dict({'description': 'You need to input a command to see it\'s information'
            })
        return embed

    if commandgroup.lower() == 'moderation':
        embed = discord.Embed.from_dict({
            'title': 'Moderation commands',
            'description': '''```css\nprefix <string>```
Sets a new prefix for Killua for the server, can only be used by admins
            
```css\nban <@user> <optionalreason>```
Bans a member and deletes their messages of the last 24 hours
            
```css\nunban <userId/Nameandtag>```
Unbans a user with id or something like `Kile#0606`
            
```css\nmute <@user> <optionaltimeinminutes> <optionalreason>```
Mutes a user for the given amount of time or you specify as `unlimited`
            
```css\nunmute <@user> <optionalreason>```
Unmutes a user'''
        })
        return embed

    if commandgroup.lower() == 'fun':
        embed = discord.Embed.from_dict({
            'title': 'Fun commands',
            'description': '''```css\nquote <@user> <text>```
Send a screenshot of a user saying what you defined. Use `-c`ast the start of `text` for compact mode or `-l` for light mode or both

```css\ncmm <text>```
Sends the *Change My Mind* meme with the text you defined

```css\nhug <@user>```
We all need  more hugs in our life, this hugs the user specified

```css\ntopic```
You suck at small talk? Get a topic with this command!

```css\ncalc <mathsstuff>```
Stuck with some math problem or just bored? Use this calculator!
            
```css\ntranslate <sourcelanguage/auto> <targetlanguage> <text>```
Translates given text to the targetlanguage

```css\n8ball <question>```
Killua will answer the provided question

```css\navatar```
What you'd expect from an avatar command, provide a mention or ID

```css\nbook <bookname>```
Get infos about the book providet

```css\nemojaic <user/id/link>```
Changes provided image into emojis (seriously try this one!)

```css\nimage <title>```
Gives you the best DuckDuckGo images for your title

```\nf <type> <user/id/link>```
To get a list with available types just use `k!f`
*heads or tails in plan*
            '''
        })
        return embed

    if commandgroup.lower() == 'economy':
        embed = discord.Embed.from_dict({

            'title': 'Economy commands',
            'description': '''```css\ndaily```
Gives you your daily points

```css\nrps <@user> <optional integer>```
Challenges someone to a game of Rock Paper Scissors. If you specify an amount you play with points and the winner gets them all

```css\nprofile <user_id/mention>```
Shows you info about a specific user, some discord info and some info like how many points they have

```css\ngive <user> <points>```
Give a fellow user some points

```css\nserver```
Gives you infos about the current server'''

        })
        return embed

    if commandgroup.lower() == 'other':
        embed = discord.Embed.from_dict({
            'title': 'Other commands',
            'description': '''```css\ninfo```
Gives you some info about the bot
            
```css\npatreon```
Gives you a link to my Patreon profile, feel free to help me and Killua out a bit <:killua_wink:769919176110112778>
            
```css\ninvite```
Gives you the invite link to the bot
            
```css\ncodeinfo <command>```
Gives you some more insights to a command like how long it took me etc
            
```css\npermissions```
Killua lists his permissions on this server
            
```css\nbug <commandname/other> <bug>```
You can report bugs with this command, abuse or spam will result in being blacklisted

```css\nfb <typeoffeedback> <feedback>```
Send feeback directly to me with this command. Abuse or spam will result in being blacklisted'''
        })
        return embed

    if commandgroup.lower() == 'todo':
        embed = discord.Embed.from_dict({
            'title': 'todo commands',
            'description': '''**Every command on this list starts with `<prefix>todo`**
```css\ncreate```
Creates a todo list in an interactive setup

```css\nlists```
Shows all lists you have permission to view, edit or own

```css\nshop```
Gives you a list of items you can purchase for your todo list

```css\nedit <list_id>```
Brings you in edit mode for the list specified if you have permission, you will have to be in this mode if you want to change anything on your todo list

```css\nadd <thing>```
Let\'s you add a todo task to the list you are currently in

```css\nremove <todo_number>```
Removes a task from your todo list you are currently in

```css\nmark <todo_number> <comment>```
Mark a todo task with a comment like "in progress". If you have specified that todos should be deleted when they are marked as "done" then it will delete todos you mark as "done". To remove a comment, simply type `-rm` instead of the comment

```css\ninvite <mention/user_id> <editor/viewer>```
Invite someone to edit or view your todo list. Viewing permissions only need ot be granted when the list is marked as `private`

```css\nview <id/custom_id>```
Lets you see the todos on a list if permission

```css\nkick <mention/user_id>```
Takes every permission from the user specified, you need to be list owner to use this command

```css\nexit```
Exits the todo list you are currently in

**These are not all todo commands, they are only the most essential. Find all todo commands [here](https://killua.dev/todo-docs)**''',
            'color': 0x1400ff
        })
        return embed

Cog = h

def setup(client):
    client.add_cog(h(client))

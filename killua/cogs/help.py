import discord
import inspect
import pymongo
from pymongo import MongoClient
from discord.ext import commands

cluster = MongoClient('mongodb+srv://Kile:Kile2-#2@cluster0.q9qss.mongodb.net/teams?retryWrites=true&w=majority')
db = cluster['Killua']
server = db['guilds']

class help(commands.Cog):

  def __init__(self, client):
    self.client = client
    
  @commands.command()
  async def help(self, ctx, group=None, command=None):
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
            :trophy: `Economy/teams`
            <:killua_wink:769919176110112778> `Other`
            
            To see a groups commands, use```css\nhelp <groupname>```
            For more info to a specific command, use
            ```css\nhelp command <commandname>```''',
            'color': 0x1400ff,
            'thumbnail': {'url': str(ctx.me.avatar_url)}
            })
        await ctx.send(embed=embed)
    elif group:
        if group.lower() in ['moderation', 'fun', 'economy', 'teams', 'other', 'command']:
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
                    await ctx.send(e)
            else:
                embed = commands(group)
                embed.color = 0x1400ff
                embed.set_thumbnail(url= str(ctx.me.avatar_url))
                await ctx.send(embed=embed)
        else:
            await ctx.send('Not a valid group, please make sure you know what groups are available')



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
            ```css\nk!default pref```
            If you should have forgotten your prefix, run this command to reset it to `k!`
            
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
            ```css\nrps <@user> <optional integer>```
            Challenges someone to a game of Rock Paper Scissors. If you specify an amount you play with points and the winner gets them all
            ```css\nhug <@user>```
            We all need  more hugs in our life, this hugs the user specified
            ```css\ntopic```
            You suck at small talk? Get a topic with this command!
            
            ```css\ntranslate <sourcelanguage/auto> <targetlanguage> <text>```
            Translates given text to the targetlanguage
            *8 ball and heads or tails in plan*
            '''
        })
        return embed

    if commandgroup.lower() == 'economy' or commandgroup.lower() == 'teams':
        embed = discord.Embed.from_dict({
            'title': 'Economy/Teams commands',
            'description': '''**CURRENTLY DISABLED, WILL BE REPLACED SOON**
            
            ```css\nteam <teamname>```
            Lets you join a team to collect points for it. Use `team current` to see your current Team
            ```css\nteaminfo <optional team>```
            Gives you more info about the Team system or individual Teams
            ```css\ndaily```
            Gives you your daily points
            
            ```css\ndaily```
            See how many points you hold on to'''
        })
        return embed

    if commandgroup.lower() == 'other':
        embed = discord.Embed.from_dict({
            'title': 'Other commands',
            'description': '''```css\nhi```
            Replies `Hi username, usertag` I am leaving this in because it was the first Killua command
            ```css\ninfo```
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
            You can report bigs with this command, abuse or spam will result in being blacklisted'''
        })
        return embed

Cog = help

def setup(client):
  client.add_cog(help(client))

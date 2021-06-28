import discord
import inspect
from discord.ext import commands
from killua.functions import check
from killua.constants import COMMANDS
import asyncio

class Help(commands.Cog):

    def __init__(self, client):
        self.client = client

    @check()
    @commands.command()
    async def help(self, ctx, group:str=None, *,command:str=None):
        #h This command is the one hopefully letting you know what Killua can do and what his features are, I hope you like how it looks!
        #u help <group/command> <command(if command was previous argument)>
        pref = self.client.command_prefix(self.client, ctx.message)[2]
        if group is None and command is None:
            
            embed = discord.Embed.from_dict({
                'title': 'Bot commands',
                'description': f'''Current server Prefix: `{pref}`
Command groups for {ctx.me.name}:
:tools: `Moderation`
:clown: `Fun`
:busts_in_silhouette: `actions`
:trophy: `Economy`
:scroll: `todo`
<:card_number_46:811776158966218802>  `Cards`
<:killua_wink:769919176110112778> `Other`
:file_cabinet: `Tags` (Premium only)

To see a groups commands, use```css\nhelp <groupname>```
For more info to a specific command, use
```css\nhelp command <commandname>```
[Support server](https://discord.gg/be4nvwq7rZ)
[Source code](https://github.com/Kile/Killua)
Website: https://killua.dev (a work in progress)''',
                'color': 0x1400ff,
                'thumbnail': {'url': str(ctx.me.avatar_url)}
            })
            try:
                await ctx.reply(embed=embed, allowed_mentions=discord.AllowedMentions.none())
            except discord.Forbidden:
                await ctx.send('Uh oh, something went wrong... I need embed permissions to send the help menu!')
        elif group:
            if group.lower() in [*[k for k in COMMANDS], *['command']]:
                if command and group.lower() == 'command':
                    if self.client.get_command(command.lower()) is None:
                        return await ctx.send('Command not found')

                    r, d, u = command_info(self, command.lower())
                            
                    embed = discord.Embed.from_dict({
                        'title': f'Info about command `k!{command.lower()}`',
                        'description': f'{d} {r}\n\nUsage:```markdown\n{pref}{u}\n```',
                        'color': 0x1400ff,
                        'thumbnail': {'url': str(ctx.me.avatar_url)}
                    })
                    await ctx.reply(embed=embed, allowed_mentions=discord.AllowedMentions.none())                    
                else:
                    await commands(self, ctx, group, pref, 1, first_time=True)
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

async def commands(self, ctx, commandgroup:str, pref:str, page:int, msg:discord.Message=None, first_time:bool=False):
    if commandgroup.lower() == 'command':
        embed = discord.Embed.from_dict({'description': 'You need to input a command to see it\'s information'
            })
        return await ctx.send(embed=embed)

    cmds = COMMANDS[commandgroup.lower()]
    command = cmds[page-1]
    r, d, u = command_info(self, command)

    embed = discord.Embed.from_dict({
        'title': commandgroup.lower() + ' commands',
        'description': f'\nCommand: `{pref}{command}`\n\n{d} {r}\n\nUsage:```markdown\n{pref}{u}\n```',
        'color': 0x1400ff,
        'thumbnail': {'url': str(ctx.me.avatar_url)},
        'footer': {'text': f'{page}/{len(cmds)}'}
    })

    if first_time:
        msg = await ctx.reply(embed=embed, allowed_mentions=discord.AllowedMentions.none())
        #ultra backwards arrow
        await msg.add_reaction('\U000023ea')
        #arrow backwards
        await msg.add_reaction('\U000025c0')
        #stop button 
        await msg.add_reaction('\U000023f9')
        #arrow forwards
        await msg.add_reaction('\U000025b6')
        #ultra forwards arrow
        await msg.add_reaction('\U000023e9')
    else:
        await msg.edit(embed=embed)

    def check(reaction, u):
        #Checking if everything is right, the bot's reaction does not count
        return u == ctx.author and reaction.message.id == msg.id and u != ctx.me and reaction.emoji in ['\U000023e9', '\U000025b6', '\U000023f9', '\U000025c0', '\U000023ea']
    try:
        reaction, u = await self.client.wait_for('reaction_add', timeout=120, check=check)
    except asyncio.TimeoutError:
        try:
            await msg.remove_reaction('\U000023ea', ctx.me)
            await msg.remove_reaction('\U000025c0', ctx.me)
            await msg.remove_reaction('\U000023f9', ctx.me)
            await msg.remove_reaction('\U000025b6', ctx.me)
            await msg.remove_reaction('\U000023e9', ctx.me)
            return
        except discord.HTTPException:
            pass
        return
    else:
        if reaction.emoji == '\U000023e9':
            #ultra forward emoji
            try:
                await msg.remove_reaction('\U000023e9', ctx.author)
            except discord.HTTPException:
                pass
            return await commands(self, ctx, commandgroup, pref, len(cmds), msg)

        if reaction.emoji == '\U000025b6':
            #forward emoji
            try:
                await msg.remove_reaction('\U000025b6', ctx.author)
            except discord.HTTPException:
                pass
            return await commands(self, ctx, commandgroup, pref, 1 if len(cmds) == page else page+1, msg)

        if reaction.emoji in ['\U000023f9', '\U0000fe0f']:
            #stop button
            await msg.delete()
            return

        if reaction.emoji == '\U000025c0':
            #backwards emoji
            try:
                await msg.remove_reaction('\U000025c0', ctx.author)
            except discord.HTTPException:
                pass
            return await commands(self, ctx, commandgroup, pref, len(cmds) if 1 == page else page-1, msg)

        if reaction.emoji == '\U000023ea':
            #ultra backwards emoji
            try:
                await msg.remove_reaction('\U000023ea', ctx.author)
            except discord.HTTPException:
                pass
            return await commands(self, ctx, commandgroup, pref, 1, msg)

""""I have given up on commenting functions"""

def command_info(self, command:str) -> tuple:
    func = self.client.get_command(command).callback
    code = inspect.getsource(func)
    linecount = code.splitlines()

    restricted = ''
    desc = 'No description yet'
    usage = 'Not provided'

    for item in linecount:
        first, middle, last = item.partition("#h")
        firstr, middler, lastr = item.partition("#r")
        firstu, middleu, lastu = item.partition("#u")
        if lastr is None or lastr == '':
            restricted = ''
        else:
            restricted = f'\n\nCommand restricted to: {lastr}'

        if last and last != '")':
            desc = last

        if lastu and lastu != '")':
            if lastu.startswith(' '):
                usage = lastu[1:]
            else:
                usage = lastu

    return restricted, desc, usage

Cog = Help

def setup(client):
    client.add_cog(Help(client))

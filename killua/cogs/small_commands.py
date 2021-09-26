import discord
from discord.ext import commands

import json
import time
from datetime import datetime, timedelta
from random import randint, choice
import math
from typing import Union
from deep_translator import GoogleTranslator, MyMemoryTranslator

from killua.static.constants import TOPICS, ANSWERS, ALIASES, UWUS, stats, teams, PREMIUM_BENEFITS
from killua.utils.checks import check
from killua.utils.classes import Category
from killua.utils.paginator import Paginator

class SmallCommands(commands.Cog):

    def __init__(self, client):
        self.client = client

    def hardcoded_aliases(self, text:str) -> str:
        l = []
        for w in text.split(' '):
            if w.lower() in ALIASES:
                l.append(choice(ALIASES[w.lower()]))
                continue
            l.append(w)
        return ' '.join(l)

    def initial_uwuing(self, text:str) -> str:
        t = []
        for w in text.split(' '):
            chars = [c for c in w]
            if 'r' in chars:
                w = w.replace('r', 'w')
            if 'ng' in chars and randint(1,2) == 1:
                w = w.replace('ng', 'n')
            if 'l' in chars and randint(1,2) == 1:
                w = w.replace('l', 'w')
            t.append(w)
        return ' '.join(t)

    def stuttify(self, text:str, stuttering:int):
        nt = []
        for p, w in enumerate(text.split(' ')):
            if p % 2 == 0:
                if int(len(text.split(' '))*(randint(1, 5)/10))*stuttering*2 < len(text.split(' ')) and len(w) > 2 and w[0] != "\n":
                    nt.append(w[:1]+'-'+w)
                    continue
            nt.append(w)
        return ' '.join(nt) 

    def cuteify(self, text:str, cuteness:int) -> str:
        s = text.split(' ')
        emotes = math.ceil((len([x for x in s if x[-1:] in [',' , '.'] and x[-2:] != '..'])+1)*(cuteness/10))
        t = []
        for p, w in enumerate(s):
            if emotes > 0:
                if (w[-1:] in [',', '.'] and w[-2:] != '..' and randint(1,10) > 5) or p+1 == len(s):
                    t.append(w[:len(w)-(1 if w[-1:] in [',', '.'] else 0)]+' '+choice(UWUS)+(w[-1:] if p != len(s)-1 else ''))
                    emotes = emotes-1
                    continue
            t.append(w)
        return ' '.join(t)

    def build_uwufy(self, text:str, cuteness:int=5, stuttering:int=3) -> str:
        text = self.hardcoded_aliases(text)
        stuttered_text = self.stuttify(self.initial_uwuing(text), stuttering)
        cuteified_text= self.cuteify(stuttered_text, cuteness)
        return cuteified_text

    @check()
    @commands.command(aliases=['uwu', 'owo', 'owofy'], extras={"category":Category.FUN}, usage="uwufy <text>")
    async def uwufy(self, ctx, *, content:str):
        """Uwufy any sentence you want with dis command, have fun >_<"""
        return await self.client.send_message(ctx, self.build_uwufy(content, stuttering=3, cuteness=3))

    @check()
    @commands.command(extras={"category":Category.FUN}, usage="ping")
    async def ping(self, ctx):
        """Standart of seeing if the bot is working"""
        start = time.time()
        msg = await ctx.send('Pong!')
        end = time.time()
        await msg.edit(content = str('Pong in `' + str(1000 * (end - start))) + '` ms')

    @check()
    @commands.command(extras={"category":Category.FUN}, usage="topic")
    async def topic(self, ctx):
        """From a constantly updating list of topics to talk about one is chosen here"""
        await ctx.send(choice(TOPICS))

    @check()
    @commands.command(extras={"category":Category.FUN}, usage="hi")
    async def hi(self, ctx):
        """This is just here because it was Killua's first command and I can't take that from him"""
        await ctx.send("Hello " + str(ctx.author))

    @check()
    @commands.command(name='8ball', extras={"category":Category.FUN}, usage="8ball <question>")
    async def _ball(self, ctx, *, question:str):
        """Ask Killua anything and he will answer"""
        embed = discord.Embed.from_dict({
            'title': f'8ball has spoken 🎱',
            'description': f'You asked:\n```\n{question}\n```\nMy answer is:\n```\n{choice(ANSWERS)}```',
            'footer': {'icon_url': str(ctx.author.avatar.url), 'text': f'Asked by {ctx.author}'},
            'color': 0x1400ff
        })
        await self.client.send_message(ctx, embed=embed)

    @check()
    @commands.command(aliases=['av', 'a'], extras={"category":Category.FUN}, usage="avatar <user(optional)>")
    async def avatar(self, ctx, user: Union[discord.Member, int]=None):
        """Shows the avatar of a user"""
        if not user:
            avatar = str(ctx.author.avatar.url)
            #Showing the avatar of the author if no user is provided
        elif isinstance(user, discord.Member):
            avatar = str(user.avatar.url)
            #If the user args is a mention the bot can just get everything from there
        else:
            try:
                user = self.client.get_user(user) or await self.client.fetch_user(user)
                avatar = str(user.avatar.url)
                #If the args is an integer the bot will try to get a user with the integer as ID
            except discord.NotFound:
                return await ctx.send('Invalid user')

        embed = discord.Embed.from_dict({
            'title': f'Avatar of {user or ctx.author}',
            'image': {'url': avatar},
            'color': 0x1400ff
        })
        await self.client.send_message(ctx, embed=embed)

    @check()
    @commands.command(aliases=["support"], extras={"category":Category.FUN}, usage="patreon")
    async def patreon(self, ctx):
        """Get infos about my Patreon and feel free to donate for some perks!"""
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Get premium", url="https://patreon.com/kilealkuri"))
        embed = discord.Embed.from_dict({
            'title': '**Support Killua**',
            'thumbnail':{'url': 'https://cdn.discordapp.com/avatars/758031913788375090/e44c0de4678c544e051be22e74bc502d.png?size=1024'},
            'description': PREMIUM_BENEFITS,
            'color': 0x1400ff
        })
        await self.client.send_message(ctx, embed=embed, view=view)

    @check()
    @commands.command(aliases=['stats'], extras={"category":Category.FUN}, usage="info")
    async def info(self, ctx):
        """Gives you some infos and stats about Killua"""
        now = datetime.now()
        diff = now - self.client.startup_datetime
        t = f'{diff.days} days, {int((diff.seconds/60)/60)} hours, {int(diff.seconds/60)-(int((diff.seconds/60)/60)*60)} minutes and {int(diff.seconds)-(int(diff.seconds/60)*60)} seconds'
        embed = discord.Embed.from_dict({
            'title': f'Infos about {ctx.me.name}',
            'description': f'This is Killua, a bot designed to be a fun multipurpose bot themed after the hxh character Killua. I started this bot when I started learning Python (You can see when on Killua\'s status). This means I am unexperienced and have to go over old buggy code again and again in the process. Thank you all for helping me out by testing Killua, please consider leaving feedback with `k!fb`\n\n**__Bot stats__**\n__Bot uptime:__ `{t}`\n__Bot users:__ `{len(self.client.users)}`\n__Bot guilds:__ `{len(self.client.guilds)}`\n__Registered users:__ `{teams.count_documents({})}`\n__Bot commands:__ `{len(self.client.commands)}`\n__Owner id:__ `606162661184372736`\n__Latency:__ `{int(self.client.latency*100)}` ms',
            'color': 0x1400ff,
            'thumbnail': {'url': str(ctx.me.avatar.url)}
        })
        await self.client.send_message(ctx, embed=embed)

    @check()
    @commands.command(extras={"category":Category.FUN}, usage="invite")
    async def invite(self, ctx):
        """Allows you to invite Killua to any guild you have at least `manage server` permissions. **Do it**"""
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Invite", url=f"https://discord.com/oauth2/authorize?client_id={self.client.user.id}&scope=bot&permissions=268723414"))
        embed = discord.Embed(
            title = 'Invite',
            description = f'Invite the bot to your server by clicking on the button. Thank you a lot for supporting me!',
            color = 0x1400ff
        )
        await ctx.send(embed=embed, view=view) 

    @check()
    @commands.command(aliases=["perms"], extras={"category":Category.FUN}, usage="permissions")
    async def permissions(self, ctx):
        """Displays the permissions Killua has and has not, useful for checking if Killua has the permissions he needs"""
        permissions = '\n'.join([f"{v} {n}" for n, v in ctx.me.guild_permissions])
        prettier = permissions.replace('_', ' ').replace('True', '<:CheckMark:771754620673982484>').replace('False', '<:x_:771754157623214080>')
        embed = discord.Embed.from_dict({
            'title': 'Bot permissions',
            'description': prettier,
            'color': 0x1400ff,
            'thumbnail': {'url': str(ctx.me.avatar.url)}
        })
        try:
            await ctx.send(embed=embed)
        except discord.Forbidden: # If embed permission is denied
            await ctx.send('__Bot permissions__\n\n'+prettier)

    @check()
    @commands.command(extras={"category":Category.FUN}, usage="vote")
    async def vote(self, ctx):
        """Gived you the links you need if you want to support Killua by voting, you will get sone Jenny as a reward"""
        view = discord.ui.View()
        view.add_item(discord.ui.Button(style=discord.ButtonStyle.grey, url="https://top.gg/bot/756206646396452975/vote", label="top.gg"))
        view.add_item(discord.ui.Button(style=discord.ButtonStyle.grey, url="https://discordbotlist.com/bots/killua/upvote", label="dbl"))
        await ctx.send('Thanks for supporting Killua! Vote for him by clicking on the buttons!', view=view)

    @check()
    @commands.command(extras={"category":Category.FUN}, usage="translate <source_lang> <target_lang> <text>")
    async def translate(self, ctx, source:str, target:str, *,args:str):
        """Translate anything to 20+ languages with this command!"""

        embed = discord.Embed.from_dict({ 'title': f'Translation',
            'description': f'```\n{args}```\n`{source}` -> `{target}`\n',
            'color': 0x1400ff
        })

        try:
            translated = MyMemoryTranslator(source=source.lower(), target=target.lower()).translate(text=args)
            embed.description = embed.description + '\nSucessfully translated by MyMemoryTranslator:'
        except Exception as ge:
            error = f'MyMemoryTranslator error: {ge}\n'
           
            try:
                embed.description = embed.description + '\nSucessfully translated by Google Translator:'
                translated = GoogleTranslator(source=source.lower(), target=target.lower()).translate(text=args)
            except Exception as me:
                error = error + f'Google error: {me}\n'
                return await ctx.send(error)
            
        embed.description = embed.description + f'```\n{translated}```'
        await self.client.send_message(ctx, embed=embed)

    @check()
    @commands.command(extras={"category":Category.FUN}, usage="calc <math>")
    async def calc(self, ctx, *,args=None):
        """Calculates any equation you give it. For how to tell it to use a square root or more complicated functions clock [here](https://mathjs.org/docs/reference/functions.html)"""
        if not args:
            return await ctx.send("Please give me something to evaluate.\n")
        exprs = str(args).split('\n')
        request = {"expr": exprs, "precision": 14}

        r = await self.client.session.post('http://api.mathjs.org/v4/', data=json.dumps(request))
        answer = await r.json()

        if "error" not in answer or "result" not in answer:
            return await ctx.send("An unknown error occurred during calculation!")
        if answer["error"]:
            return await ctx.send("The following error occured while calculating:\n`{}`".format(answer["error"]))
        await self.client.send_message(ctx, "Result{}:\n```\n{}\n```".format("s" if len(exprs) > 1 else "", "\n".join(answer["result"])))

    @check()
    @commands.command(extras={"category":Category.FUN}, usage="usage")
    async def usage(self, ctx):
        """Shows the commands used the most. Added for fun and out of interest"""
        s = stats.find_one({'_id': 'commands'})['command_usage']
        top = sorted(s.items(), key=lambda x: x[1], reverse=True)
        def make_embed(page, embed, pages):
            embed.title = "Top command usage"

            if len(pages)-page*10+10 > 10:
                top = pages[page*10-10:-(len(pages)-page*10)]
            elif len(pages)-page*10+10 <= 10:
                top = pages[-(len(pages)-page*10+10):]

            embed.description = "```\n" + '\n'.join(['#'+str(n+1)+' k!'+k+' with '+str(v)+' uses' for n, (k, v) in enumerate(top, page*10-10)]) + "\n```"
            return embed

        return await Paginator(ctx, top, func=make_embed, max_pages=math.ceil(len(top)/10)).start()

    @check(3600)
    @commands.command(aliases=['fb'], extras={"category":Category.OTHER}, usage="feedback <type> <text>")
    async def feedback(self, ctx, t=None, *, feedback=None):
        """Submit feedback to Killua with this command! For more information on how do send what, use `fb`."""
        if t:
            if not t.lower() in ['topic', '8ball', 'hug', 'apply', 'general', 'idea', 'feature-request', 'complain', 'compliment']:
                ctx.command.reset_cooldown(ctx)
                return await ctx.send(f'Type not found. To see what types of feeback you can submit, use `{self.client.command_prefix(self.client, ctx.message)[2]}fb`')

            if feedback is None:
                return await ctx.send(f'Please tell us what you have to say about the chosen point. For more info use `{self.client.command_prefix(self.client, ctx.message)[2]}fb`')

            embed = discord.Embed.from_dict({
                'title': f'Feedback from guild {ctx.guild.name} (ID: {ctx.guild.id})',
                'description': f'''Type of feedback: `{t}`  \n\n**Provided feedback:**\n\n{feedback}\n\nFeedback by **{ctx.author}, ID: {ctx.author.id}**''',
                'color': 0x1400ff
            })
            
            channel = self.client.get_channel(790002080625983558)

            message = await channel.send(embed=embed)
            await message.add_reaction('\U00002705')
            await message.add_reaction('\U0000274c')

            await ctx.send(':white_check_mark: thanks for sending your feedback! The feedback will be looked at as soon as possible!')
        else:
            ctx.command.reset_cooldown(ctx)
            embed = discord.Embed.from_dict({
                'title': f'Sending feedback',
                'description': f'''Since this bot is in its early stages, feedback of users is of highest importance
            
    You can submit 9 types of feedback:

    `topic` - suggestion for a topic for `{self.client.command_prefix(self.client, ctx.message)[2]}topic`
    `8ball` - suggestion for a response for `{self.client.command_prefix(self.client, ctx.message)[2]}8ball`
    `hug` - submit a hug text or image (Killua only) 
    `apply` - apply for the team, we are looking for artists, programmer, people looking out for the server etc. Of course being part of the team comes with it's advantages
    `general` - you just wanna give general feedback to us, no specific or too many categories for the other options
    `idea` - you have a good idea for a command (like `{self.client.command_prefix(self.client, ctx.message)[2]}novel <booktitle>`, a idea I had today and I wil implement cause it's cool). Please describe it as detailed as possible though
    `feature`-request - request a feature, kinda like idea but idk. Again, lease describe it as detailed as possible
    `complain` - complain about something
    `compliment` -  compliment a feature of Killua

    **This command has a 1 hour cooldown, abuse will lead to blacklisting**
    [Support server](https://discord.gg/be4nvwq7rZ)''',
                'color': 0x1400ff
            })

            await ctx.send(embed=embed)

Cog = SmallCommands

def setup(client):
    client.add_cog(SmallCommands(client))
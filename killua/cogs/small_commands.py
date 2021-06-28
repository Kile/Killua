import discord
from discord.ext import commands
import time
from datetime import datetime, timedelta
import random
from random import randint, choice
import math
import typing
import aiohttp
from deep_translator import GoogleTranslator, MyMemoryTranslator
from killua.functions import check, check
from killua.constants import TOPICS, ANSWERS, ALIASES, UWUS, stats, teams

class SmallCommands(commands.Cog):

    def __init__(self, client):
        self.client = client

    def av(self, user) -> discord.Embed:
        """ Input:
            user: the user to get the avatar from

            Returns:
            embed: an embed with the users avatar

            Purpose: 
            "outsourcing" a bit of the avatar command
        """
        #constructing the avatar embed
        embed = discord.Embed.from_dict({
            'title': f'Avatar of {user}',
            'image': {'url': str(user.avatar_url_as(static_format='png'))},
            'color': 0x1400ff
        })
        return embed

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
                if int(len(text.split(' '))*(randint(1, 5)/10))*stuttering*2 < len(text.split(' ')) and len(w) > 2:
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
                if (w[-1:] in [',', '.'] and w[-2:] != '..' and randint(6,10) > 7) or p+1 == len(s):
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
    @commands.command(aliases=['uwu', 'owo', 'owofy'])
    async def uwufy(self, ctx, *, content:str):
        #h Uwufy any sentence you want with dis command, have fun >_<
        #u uwu <text>
        return await ctx.send(self.build_uwufy(content, stuttering=3, cuteness=3))

    @check()
    @commands.command()
    async def ping(self, ctx):
        #h Standart of seeing if the bot is working
        #u ping
        start = time.time()
        msg = await ctx.send('Pong!')
        end = time.time()
        await msg.edit(content = str('Pong in `' + str(1000 * (end - start))) + '` ms')

    @check()
    @commands.command()
    async def topic(self, ctx):
        #h From a constatnly updating list of topics to talk about one is chosen here
        #u topic
        await ctx.send(random.choice(TOPICS))

    @check()
    @commands.command()
    async def hi(self, ctx):
        #h This is just here because it was Killua's first command and I can't take that from him :3
        #u hi
        await ctx.send("Hello " + str(ctx.author))

    @check()
    @commands.command(aliases=['8ball'])
    async def ball(self, ctx, *, question:str):
        #h Ask Killua anything and he will answer
        #u 8ball <question>
        embed = discord.Embed.from_dict({
            'title': f'8ball has spoken 🎱',
            'description': f'You asked:\n```\n{question}\n```\nMy answer is:\n```\n{random.choice(ANSWERS)}```',
            'footer': {'icon_url': str(ctx.author.avatar_url), 'text': f'Asked by {ctx.author}'},
            'color': 0x1400ff
        })
        await ctx.send(embed=embed)

    @check()
    @commands.command(aliases=['av', 'a'])
    async def avatar(self, ctx, user: typing.Union[discord.Member, int]=None):
        #h Shows the avatar of a user
        #u avatar <user(optional)>
        if not user:
            embed = self.av(ctx.author)
            return await ctx.send(embed=embed)
            #Showing the avatar of the author if no user is provided
        if isinstance(user, discord.Member):
            embed = self.av(user)
            return await ctx.send(embed=embed)
            #If the user args is a mention the bot can just get everything from there
        try:
            newuser = await self.client.fetch_user(user)
            embed = self.av(newuser)
            return await ctx.send(embed=embed)
            #If the args is an integer the bot will try to get a user with the integer as ID
        except discord.NotFound:
            return await ctx.send('Invalid user')

    @check()
    @commands.command()
    async def patreon(self, ctx):
        #h Get infos about my Patreon and feel free to donate for some perks!
        #u patreon
        embed = discord.Embed.from_dict({
            'title': '**Support Killua**',
            'thumbnail':{'url': 'https://cdn.discordapp.com/avatars/758031913788375090/e44c0de4678c544e051be22e74bc502d.png?size=1024'},
            'description': 'Hey, do you have too much money? I have a solution for that! I now have a Patreon account where you can donate to support me and get special stuff, helping with building Killua. Not that I expect anyone to do this, but I have it set up now. Make sure you are on my server before you become a Patreon so you get the perks!\n\n https://www.patreon.com/KileAlkuri',
            'color': 0x1400ff
        })
        await ctx.send(embed=embed)

    @check()
    @commands.command(aliases=['stats'])
    async def info(self, ctx):
        #h Gives you some infos and stats about Killua
        #u info
        now = datetime.now()
        diff = now - self.client.startup_datetime
        t = f'{diff.days} days, {int((diff.seconds/60)/60)} hours, {int(diff.seconds/60)-(int((diff.seconds/60)/60)*60)} minutes and {int(diff.seconds)-(int(diff.seconds/60)*60)} seconds'
        embed = discord.Embed.from_dict({
            'title': f'Infos about {ctx.me.name}',
            'description': f'This is Killua, a bot designed to be a fun multipurpose bot themed after the hxh character Killua. I started this bot when I started learning Python (You can see when on Killua\'s status). This means I am unexperienced and have to go over old buggy code again and again in the process. Thank you all for helping me out by testing Killua, please consider leaving feedback with `k!fb`\n\n**__Bot stats__**\n__Bot uptime:__ `{t}`\n__Bot users:__ `{len(self.client.users)}`\n__Bot guilds:__ `{len(self.client.guilds)}`\n__Registered users:__ `{teams.count_documents({})}`\n__Bot commands:__ `{len(self.client.commands)}`\n__Owner id:__ `606162661184372736`\n__Latency:__ `{int(self.client.latency*100)}` ms',
            'color': 0x1400ff,
            'thumbnail': {'url': str(ctx.me.avatar_url)}
        })
        await ctx.send(embed=embed)

    @check()
    @commands.command()
    async def invite(self, ctx):
        #h Allows you to invite Killua to any guild you have at least `manage server` permissions. **Do it**
        #u invite
        embed = discord.Embed(
            title = 'Invite',
            description = 'Invite the bot to your server [here](https://discord.com/oauth2/authorize?client_id=756206646396452975&scope=bot&permissions=268723414). Thank you a lot for supporting me!',
            color = 0x1400ff
        )
        await ctx.send(embed=embed) 

    @check()
    @commands.command()
    async def permissions(self, ctx):
        #h Displays the permissions Killua has and has not, useful for checking if Killua has the permissions he needs
        #u permissions
        permissions = '\n'.join([f"{v} {n}" for n, v in ctx.me.guild_permissions])
        prettier = permissions.replace('_', ' ').replace('True', '<:CheckMark:771754620673982484>').replace('False', '<:x_:771754157623214080>')
        embed = discord.Embed.from_dict({
            'title': 'Bot permissions',
            'description': prettier,
            'color': 0x1400ff,
            'thumbnail': {'url': str(ctx.me.avatar_url)}
        })
        try:
            await ctx.send(embed=embed)
        except discord.Forbidden: # If embed permission is denied
            await ctx.send('__Bot permissions__\n\n'+prettier)

    @check()
    @commands.command()
    async def vote(self, ctx):
        #u vote
        #h Gived you the links you need if you want to support Killua by voting
        await ctx.send('Thanks for supporting Killua! Vote for him here: https://top.gg/bot/756206646396452975/vote \nAnd here: https://discordbotlist.com/bots/killua/upvote')

    @check()
    @commands.command()
    async def translate(self, ctx, source:str, target:str, *,args:str):
        #h Translate anything to 20+ languages with this command! 
        #u translate <source_lang> <target_lang> <text>

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
        await ctx.send(embed=embed)

    @check()
    @commands.command()
    async def calc(self, ctx, *,args=None):
        #h Calculates any equasion you give it. For how to tell it to use a square root or more complicated functions clock [here](https://mathjs.org/docs/reference/functions.html)
        #u calc <text>
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
        await ctx.send("Result{}:\n```\n{}\n```".format("s" if len(exprs) > 1 else "", "\n".join(answer["result"])))

    @check()
    @commands.command()
    async def usage(self, ctx):
        #h Shows the commands used the most. Added for fun and out of interest
        #u usage
        s = stats.find_one({'_id': 'commands'})['command_usage']
        top = sorted(s.items(), key=lambda x: x[1], reverse=True)[:20]
        prettier = '\n'.join(['#'+str(n+1)+' k!'+k+' with '+str(v)+' uses' for n, (k, v) in enumerate(top)])
        return await ctx.send("```\n"+prettier+"\n```")

Cog = SmallCommands

def setup(client):
    client.add_cog(SmallCommands(client))
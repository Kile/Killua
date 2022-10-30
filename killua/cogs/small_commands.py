import discord
from discord.ext import commands

import json
import time
from datetime import datetime
from random import randint, choice
import math
from typing import List
from urllib.parse import quote


from killua.bot import BaseBot
from killua.static.constants import TOPICS, ANSWERS, ALIASES, UWUS, LANGS, DB, WYR
from killua.utils.interactions import View, Button
from killua.utils.checks import check
from killua.static.enums import Category

class PollSetup(discord.ui.Modal): #lgtm [py/missing-call-to-init]

    def __init__(self, *args, **kwargs):
        super().__init__(title="Poll setup", *args, **kwargs)
        self.add_item(discord.ui.TextInput(label="Question", custom_id="question", max_length=256, style=discord.TextStyle.long, placeholder="Are there more doors or wheels in the world?"))
        self.add_item(discord.ui.TextInput(label="Option 1", custom_id="option:1", max_length=246, placeholder="Doors"))
        self.add_item(discord.ui.TextInput(label="Option 2", custom_id="option:2", max_length=246, placeholder="Wheels"))
        self.add_item(discord.ui.TextInput(label="Option 3", custom_id="option:3", max_length=246, placeholder="Both", required=False))
        self.add_item(discord.ui.TextInput(label="Option 4", custom_id="option:4", max_length=246, placeholder="Neither", required=False))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Called when the modal is submitted"""
        await interaction.response.defer()

class SmallCommands(commands.Cog):

    def __init__(self, client: BaseBot):
        self.client = client
        self._init_menus()

    def _init_menus(self) -> None:
        menus = []
        menus.append(discord.app_commands.ContextMenu(
            name='uwufy',
            callback=self.client.callback_from_command(self.uwufy, message=True),
        ))
        menus.append(discord.app_commands.ContextMenu(
            name='translate',
            callback=self.client.callback_from_command(self.translate, message=True, source="auto"),
        ))

        for menu in menus:
            self.client.tree.add_command(menu)

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

    @commands.hybrid_group()
    async def miscillaneous(self, _: commands.Context):
        """A collection of miscillaneous commands."""
        ...

    @check()
    @miscillaneous.command(aliases=["uwu", "owo", "owofy"], extras={"category":Category.FUN}, usage="uwufy <text>")
    @discord.app_commands.describe(text="The text to uwufy")
    async def uwufy(self, ctx: commands.Context, *, text: str):
        """Uwufy any sentence you want with dis command, have fun >_<"""
        return await self.client.send_message(ctx, self.build_uwufy(text, stuttering=3, cuteness=3))

    @check()
    @miscillaneous.command(extras={"category":Category.FUN}, usage="ping")
    async def ping(self, ctx: commands.Context):
        """Standart of seeing if the bot is working"""
        start = time.time()
        msg = await ctx.send("Pong!")
        end = time.time()
        await msg.edit(content = str("Pong in `" + str(1000 * (end - start))) + "` ms")

    @check()
    @miscillaneous.command(extras={"category":Category.FUN}, usage="topic")
    async def topic(self, ctx: commands.Context):
        """From a constantly updating list of topics to talk about one is chosen here"""
        await ctx.send(choice(TOPICS))

    @check()
    @miscillaneous.command(extras={"category":Category.FUN}, usage="hi")
    async def hi(self, ctx: commands.Context):
        """This is just here because it was Killua's first command and I can't take that from him"""
        await ctx.send("Hello " + str(ctx.author))

    @check()
    @miscillaneous.command(name="8ball", extras={"category":Category.FUN}, usage="8ball <question>")
    @discord.app_commands.describe(question="The question to ask the magic 8 ball")
    async def _ball(self, ctx: commands.Context, *, question: str):
        """Ask Killua anything and he will answer"""
        embed = discord.Embed.from_dict({
            "title": f"8ball has spoken 🎱",
            "description": f"You asked:\n```\n{question}\n```\nMy answer is:\n```\n{choice(ANSWERS)}```",
            "footer": {"icon_url": str(ctx.author.avatar.url), "text": f"Asked by {ctx.author}"},
            "color": 0x1400ff
        })
        await self.client.send_message(ctx, embed=embed)

    @check()
    @miscillaneous.command(aliases=["av", "a"], extras={"category":Category.FUN}, usage="avatar <user(optional)>")
    @discord.app_commands.describe(user="The user to show the avatar of")
    async def avatar(self, ctx: commands.Context, user: str = None):
        """Shows the avatar of a user"""
        if user:
            user = self.client.find_user(ctx, user)
            if not user:
                return await ctx.send("User not found")
        else:
            user = ctx.author

        if not user.avatar:
            return await ctx.send("User has no avatar")

        embed = discord.Embed.from_dict({
            "title": f"Avatar of {user}",
            "image": {"url": str(user.avatar.url)},
            "color": 0x1400ff
        })
        await self.client.send_message(ctx, embed=embed)

    @check()
    @miscillaneous.command(aliases=["stats"], extras={"category":Category.FUN}, usage="info")
    async def info(self, ctx: commands.Context):
        """Gives you some infos and stats about Killua"""
        now = datetime.now()
        diff = now - self.client.startup_datetime
        t = f"{diff.days} days, {int((diff.seconds/60)/60)} hours, {int(diff.seconds/60)-(int((diff.seconds/60)/60)*60)} minutes and {int(diff.seconds)-(int(diff.seconds/60)*60)} seconds"
        embed = discord.Embed.from_dict({
            "title": f"Infos about {ctx.me.name}",
            "description": f"This is Killua, a bot designed to be a fun multipurpose bot themed after the hxh character Killua. I started this bot when I started learning Python (You can see when on Killua's status). This means I am unexperienced and have to go over old buggy code again and again in the process. Thank you all for helping me out by testing Killua, please consider leaving feedback with `k!fb`\n\n**__Bot stats__**\n__Bot uptime:__ `{t}`\n__Bot users:__ `{len(self.client.users)}`\n__Bot guilds:__ `{len(self.client.guilds)}`\n__Registered users:__ `{DB.teams.count_documents({})}`\n__Bot commands:__ `{len(self.client.commands)}`\n__Owner id:__ `606162661184372736`\n__Latency:__ `{int(self.client.latency*100)}` ms",
            "color": 0x1400ff,
            "thumbnail": {"url": str(ctx.me.avatar.url)}
        })
        await self.client.send_message(ctx, embed=embed)

    @check()
    @miscillaneous.command(extras={"category":Category.FUN}, usage="invite")
    async def invite(self, ctx: commands.Context):
        """Allows you to invite Killua to any guild you have at least `manage server` permissions."""
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Invite", url=self.client.invite))
        embed = discord.Embed(
            title = "Invite",
            description = f"Invite the bot to your server by clicking on the button. Thank you a lot for supporting me!",
            color = 0x1400ff
        )
        await ctx.send(embed=embed, view=view) 

    @check()
    @miscillaneous.command(aliases=["perms"], extras={"category":Category.FUN}, usage="permissions")
    async def permissions(self, ctx: commands.Context):
        """Displays the permissions Killua has and has not in the current channel"""
        permissions = "\n".join([f"{v} {n}" for n, v in ctx.me.guild_permissions])
        prettier = permissions.replace("_", " ").replace("True", "<:CheckMark:771754620673982484>").replace("False", "<:x_:771754157623214080>")
        embed = discord.Embed.from_dict({
            "title": "Bot permissions",
            "description": prettier,
            "color": 0x1400ff,
            "thumbnail": {"url": str(ctx.me.avatar.url)}
        })
        try:
            await ctx.send(embed=embed)
        except discord.Forbidden: # If embed permission is denied
            await ctx.send("__Bot permissions__\n\n"+prettier)

    @check()
    @miscillaneous.command(extras={"category":Category.FUN}, usage="vote")
    async def vote(self, ctx: commands.Context):
        """Gives you the links you need if you want vote for Killua, you will get sone Jenny as a reward"""
        view = discord.ui.View()
        view.add_item(discord.ui.Button(style=discord.ButtonStyle.grey, url="https://top.gg/bot/756206646396452975/vote", label="top.gg"))
        view.add_item(discord.ui.Button(style=discord.ButtonStyle.grey, url="https://discordbotlist.com/bots/killua/upvote", label="dbl"))
        await ctx.send("Thanks for supporting Killua! Vote for him by clicking on the buttons!", view=view)

    async def lang_autocomplete(
        self, 
        _: commands.Context,
        current: str
    ) -> List[discord.app_commands.Choice[str]]:
        """Returns a list of flags that match the current string since there are too many flags for it to use the options feature"""
        return [
            discord.app_commands.Choice(name=i.title(), value=i) for i in LANGS.keys() 
            if i.startswith(current.lower()) or current.lower() in i
        ][:25]

    @check()
    @miscillaneous.command(extras={"category":Category.FUN}, usage="translate <source_lang> <target_lang> <text>")
    @discord.app_commands.describe(
        source="The language you want to translate from",
        target="The language you want to translate to",
        text="The text you want to translate"
    )
    @discord.app_commands.autocomplete(source=lang_autocomplete, target=lang_autocomplete)
    async def translate(self, ctx: commands.Context, source: str, target: str = None, *, text: str):
        """Translate anything to 20+ languages with this command!"""
        if source.lower() in LANGS: source = LANGS[source.lower()]
        if hasattr(ctx, "invoked_by_modal") or not target: target = (str(ctx.interaction.locale) if str(ctx.interaction.locale).startswith("zh") else str(ctx.interaction.locale).split("-")[0]) if ctx.interaction else target
        elif target.lower() in LANGS: target = LANGS[target.lower()]

        if (not target in LANGS.values() and not hasattr(ctx, "invoked_by_modal")) or not (source in LANGS.values()):
            return await ctx.send("Invalid language! This is how to use the command: `" + ctx.command.usage + "`", ephemeral=True)

        if len(source) > 1800:
            return await ctx.send("Too many characters to translate!", ephemeral=True)

        coded_text = quote(text, safe="")
        res = await self.client.session.get("http://api.mymemory.translated.net/get?q=" + coded_text + "&langpair=" + source.lower() + "|" + target.lower())

        if not (res.status == 200):
            return await ctx.send(":x: " + await res.text(), ephemeral=True)

        translation = await res.json()
        if not "matches" in translation or len(translation["matches"]) < 1:
            if source == "autodetect":
                return await ctx.send("Unfortunately the translators language detection is currently malfunctioning, please try again later!", ephemeral=True)
            return await ctx.send("Translation failed!", ephemeral=hasattr(ctx, "invoked_by_modal"))

        embed = discord.Embed.from_dict({ 
            "title": f"Translation Successfull",
            "description": f"```\n{text}```\n`{source}` -> `{target}`\n\n```\n{translation['responseData']['translatedText']}```",
            "color": 0x1400ff,
            "footer": {"text": "Confidence: " + str(translation["matches"][0]["quality"]) + "%"}
        })
        
        await self.client.send_message(ctx, embed=embed, ephemeral=hasattr(ctx, "invoked_by_modal"))

    @check()
    @miscillaneous.command(extras={"category":Category.FUN}, usage="calc <math>")
    @discord.app_commands.describe(expression="The expression to calculate")
    async def calc(self, ctx: commands.Context, *, expression: str = None):
        """Calculates any equation you give it. Syntax: https://mathjs.org/docs/reference/functions.html"""
        if not expression:
            return await ctx.send("Please give me something to evaluate.\n")
        exprs = str(expression).split("\n")
        request = {"expr": exprs, "precision": 14}

        r = await self.client.session.post("http://api.mathjs.org/v4/", data=json.dumps(request))
        answer = await r.json()

        if "error" not in answer or "result" not in answer:
            return await ctx.send("An unknown error occurred during calculation!")
        if answer["error"]:
            return await ctx.send("The following error occured while calculating:\n`{}`".format(answer["error"]))
        await self.client.send_message(ctx, "Result{}:\n```\n{}\n```".format("s" if len(exprs) > 1 else "", "\n".join(answer["result"])))

    @check()
    @miscillaneous.command(extras={"category":Category.FUN}, usage="poll")
    async def poll(self, ctx: commands.Context):
        """Creates a poll"""
        if not ctx.interaction:
            view = View(ctx.author.id)
            view.add_item(Button(style=discord.ButtonStyle.green, label="Setup"))
            msg = await ctx.send("Please press the button to setup the poll", view=view)
            await view.wait()

            if view.timed_out:
                return await msg.delete()
            else:
                await msg.delete()
                ctx.interaction = view.interaction
            
        modal = PollSetup()
        await ctx.interaction.response.send_modal(modal)

        timed_out = await modal.wait()

        if timed_out:
            return

        view = discord.ui.View(timeout=None)

        embed = discord.Embed(title="Poll", description=modal.children[0].value, color=0x1400ff)
        embed.set_footer(text=f"Poll by {ctx.author}", icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)

        for pos, child in enumerate(modal.children):
            if child.value and child.label.startswith("Option"):
                embed.add_field(name=f"{pos}) " + child.value + " `[0 votes]`", value="No votes", inline=False)
                item = discord.ui.Button(style=discord.ButtonStyle.blurple, label=f"Option {pos}", custom_id=f"poll:option-{pos}:{ctx.author.id}")
                view.add_item(item)

        close_item = discord.ui.Button(style=discord.ButtonStyle.red, label="Close Poll", custom_id=f"poll:close:{ctx.author.id}")
        view.add_item(close_item)

        await ctx.send(embed=embed, view=view)

    @check()
    @miscillaneous.command(extras={"category":Category.FUN}, usage="wyr")
    async def wyr(self, ctx: commands.Context):
        """Asks a random would you rather question and allows you to vote."""
        
        view = discord.ui.View(timeout=None)

        embed = discord.Embed(title="Would you rather...", color=0x1400ff)
        embed.set_footer(text=f"Command ran by {ctx.author}", icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/761621578458202122/1035249833335861308/unknown.png")

        A, B = choice(WYR)

        embed.add_field(name="A) " + A + " `[0 people]`", value="No takers", inline=False)
        embed.add_field(name="B) " + B + " `[0 people]`", value="No takers", inline=False)

        itemA = discord.ui.Button(style=discord.ButtonStyle.blurple, label="Option A", custom_id=f"wyr:option-a:{ctx.author.id}")
        itemB = discord.ui.Button(style=discord.ButtonStyle.blurple, label="Option B", custom_id=f"wyr:option-b:{ctx.author.id}")

        view.add_item(itemA).add_item(itemB)

        await ctx.send(embed=embed, view=view)

Cog = SmallCommands
import discord
from discord.ext import commands
import random
import asyncio
from io import BytesIO
from typing import List, Union, Optional, cast, Tuple

from killua.bot import BaseBot
from killua.utils.checks import check
from killua.utils.classes import User
from killua.static.enums import Category
from killua.utils.interactions import View
from killua.static.constants import ACTIONS, KILLUA_BADGES


class SettingsSelect(discord.ui.Select):
    """Creates a select menu to change action settings"""

    def __init__(self, options, **kwargs):
        super().__init__(options=options, **kwargs)

    async def callback(self, interaction: discord.Interaction):
        self.view.values = interaction.data["values"]
        for opt in self.options:
            if opt.value in self.view.values:
                opt.default = True
        await interaction.response.defer()


class SettingsButton(discord.ui.Button):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def callback(self, interaction: discord.Interaction):
        if not hasattr(self.view, "values"):
            return await interaction.response.send_message(
                "You have not changed any settings", ephemeral=True
            )
        self.view.timed_out = False
        self.view.stop()


@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=False, private_channels=True)
class Actions(commands.GroupCog, group_name="action"):

    def __init__(self, client: BaseBot):
        self.client = client
        self.session = self.client.session

    async def request_action(self, endpoint: str) -> Union[dict, str]:
        """
        Fetch an image from the API for the action commands
        """

        r = await self.session.get(f"https://purrbot.site/api/img/sfw/{endpoint}/gif")
        if r.status == 200:
            res = await r.json()

            if res["error"]:
                return res["message"]

            return res
        else:
            return await r.text()

    async def get_image(
        self, ctx: commands.Context
    ) -> (
        discord.Message
    ):  # for endpoints like /blush/gif where you don't want to mention a user
        """
        Get the image for one of the action commands from the API without arguments
        """
        image = await self.request_action(ctx.command.name)
        if isinstance(image, str):
            return await ctx.send(f":x: {image}")
        embed = discord.Embed.from_dict(
            {
                "title": "",
                "image": {"url": image["link"]},
                "color": await self.client.find_dominant_color(image["link"]),
            }
        )
        return await ctx.send(embed=embed)

    async def save_stat(
        self,
        member: discord.Member,
        endpoint: str,
        targetted: bool = False,
        amount: int = 1,
    ) -> Optional[str]:
        """
        Saves the action being done on a user and returns the badge if the user
        has reached a milestone for the action.
        """
        user = await User.new(member.id)
        badge = await user.add_action(endpoint, targetted, amount)
        return badge

    def generate_users(self, users: List[discord.User], title: str) -> str:
        """
        Parses the list of members and returns a string with their names,
        making sure the string is not too long for the embed title
        """
        if isinstance(users, str):
            return users
        userlist = ""
        for p, user in enumerate(users):
            if (
                len(
                    userlist
                    + user.display_name
                    + title.replace("(a)", "").replace("(u)", "")
                )
                > 231
            ):  # embed titles have a max length of 256 characters.
                # If the name list contains too many names, stuff breaks.
                # This prevents that and displays the other people as "and x more"
                userlist = userlist + f" *and {len(user)-(p+1)} more*"
                break
            if users[-1] == user and len(users) != 1:
                userlist = userlist + f" and {user.display_name}"
            else:
                if users[0] == user:
                    userlist = f"{user.display_name}"
                else:
                    userlist = userlist + f", {user.display_name}"
        return userlist

    async def action_embed(
        self,
        endpoint: str,
        author: Union[str, discord.User],
        users: List[discord.User],
        disabled: int = 0,
    ) -> Tuple[discord.Embed, Optional[discord.File]]:
        """
        Creates an embed for the action commands with the members and author provided
        as well as adding the image and action text
        """
        if disabled == len(users):
            return "All members targetted have disabled this action.", None

        if endpoint == "hug":
            chosen = random.choice(ACTIONS[endpoint]["images"])
            chosen["url"] = (
                self.client.api_url(to_fetch=self.client.is_dev) + chosen["url"]
            )
            image = {
                "link": chosen
            }  # This might eventually be deprecated for copyright reasons
        else:
            image = await self.request_action(endpoint)
            if isinstance(image, str):
                return f":x: {image}", None

        text: str = random.choice(ACTIONS[endpoint]["text"])
        text = text.replace(
            "<author>",
            "**" + (author if isinstance(author, str) else author.name) + "**",
        ).replace("<user>", "**" + self.generate_users(users, text) + "**")

        embed = discord.Embed.from_dict(
            {
                "title": text,
                "color": await self.client.find_dominant_color(
                    image["link"]["url"] if "url" in image["link"] else image["link"]
                ),
                "description": (
                    f"Art by [{image['link']['artist']['name']}]("
                    + image["link"]["artist"]["link"]
                    + ")"
                    if "url" in image["link"] and image["link"]["artist"]
                    else None
                ),
            }
        )

        file = None
        if endpoint == "hug":
            if self.client.is_dev:
                # Upload the image as attachment instead
                data = await self.session.get(image["link"]["url"])
                if data.status != 200:
                    return ":x: " + await data.text(), None
                extension = cast(str, image["link"]["url"]).split(".")[-1]
                embed.set_image(url=f"attachment://image.{extension}")
                file = discord.File(BytesIO(await data.read()), f"image.{extension}")
            else:
                embed.set_image(url=image["link"]["url"])
        else:
            embed.set_image(url=image["link"])

        if disabled > 0:
            embed.set_footer(
                text=f"{disabled} user{'s' if disabled > 1 else ''} disabled being targetted with this action"
            )
        return embed, file

    async def no_argument(
        self, ctx: commands.Context
    ) -> Optional[Tuple[discord.Embed, Optional[discord.File]]]:
        """
        The user didn't provide any (valid) arguments to the command, so they are asked if they
        want to be hugged. If they respond with "yes", the command is executed with the author as the target.
        """
        await ctx.send(
            f"You provided no one to {ctx.command.name}.. Should- I {ctx.command.name} you?"
        )

        def check(m: discord.Message):
            return m.content.lower() == "yes" and m.author == ctx.author

        try:
            await self.client.wait_for("message", check=check, timeout=60)
        except asyncio.TimeoutError:
            return None, None  # Needs to be a tuple
        else:
            return await self.action_embed(ctx.command.name, "Killua", ctx.author.name)

    async def do_action(
        self, ctx: commands.Context, users: List[discord.User] = None
    ) -> Union[discord.Message, None]:
        """
        Executes an action command with the given members
        """
        if not users:
            embed, file = await self.no_argument(ctx)
            if not embed:
                return
        elif ctx.author == users[0]:
            return await ctx.send("Sorry... you can't use this command on yourself")
        else:
            first = await User.new(users[0].id)
            if (
                len(users) == 1
                and (ctx.command.name in first.action_settings)
                and not first.action_settings[ctx.command.name]
            ):
                return await ctx.send(
                    f"**{users[0].display_name}** has disabled this action",
                    allowed_mentions=discord.AllowedMentions.none(),
                )

            allowed: List[discord.User] = []
            disabled = 0
            for user in users:
                m = await User.new(user.id)
                if (
                    m.action_settings
                    and ctx.command.name in m.action_settings
                    and m.action_settings[ctx.command.name] is False
                ):
                    disabled += 1
                else:
                    allowed.append(user)

            for user in allowed:
                badge = await self.save_stat(user, ctx.command.name, True)
                if badge:
                    try:
                        await user.send(
                            f"Congratulation! You got the {KILLUA_BADGES[badge]} badge for being {ctx.command.name}ed more than 500 times! So many hugs :D. Check your shiny new badge out with `k!pofile`!"
                        )
                    except discord.Forbidden:
                        pass

            badge = await self.save_stat(
                ctx.author, ctx.command.name, False, len(allowed)
            )
            if badge:
                try:
                    await ctx.author.send(
                        f"Congratulations! You got the {KILLUA_BADGES[badge]} badge for {ctx.command.name}ing someone more than 1000 times! So many hugs :D. Check your shiny new badge out with `k!pofile`!"
                    )
                except discord.Forbidden:
                    pass
            embed, file = await self.action_embed(
                ctx.command.name, ctx.author, users, disabled
            )

        if isinstance(embed, str):
            return await ctx.send(content=embed)
        else:
            return await self.client.send_message(ctx, embed=embed, file=file)

    @check()
    @commands.hybrid_command(
        extras={"category": Category.ACTIONS, "id": 1}, usage="hug <user(s)>"
    )
    @discord.app_commands.describe(users="The people to hug")
    async def hug(
        self, ctx: commands.Context, users: commands.Greedy[discord.User] = None
    ):
        """Hug a user with this command"""
        return await self.do_action(ctx, users)

    @check()
    @commands.hybrid_command(
        extras={"category": Category.ACTIONS, "id": 2}, usage="pat <user(s)>"
    )
    @discord.app_commands.describe(users="The people to pat")
    async def pat(
        self, ctx: commands.Context, users: commands.Greedy[discord.User] = None
    ):
        """Pat a user with this command"""
        return await self.do_action(ctx, users)

    @check()
    @commands.hybrid_command(
        extras={"category": Category.ACTIONS, "id": 3}, usage="poke <user(s)>"
    )
    @discord.app_commands.describe(users="The people to poke")
    async def poke(
        self, ctx: commands.Context, users: commands.Greedy[discord.User] = None
    ):
        """Poke a user with this command"""
        return await self.do_action(ctx, users)

    @check()
    @commands.hybrid_command(
        extras={"category": Category.ACTIONS, "id": 4}, usage="tickle <user(s)>"
    )
    @discord.app_commands.describe(users="The people to tickle")
    async def tickle(
        self, ctx: commands.Context, users: commands.Greedy[discord.User] = None
    ):
        """Tickle a user wi- ha- hahaha- stop- haha"""
        return await self.do_action(ctx, users)

    @check()
    @commands.hybrid_command(
        extras={"category": Category.ACTIONS, "id": 5}, usage="slap <user(s)>"
    )
    @discord.app_commands.describe(users="The people to slap")
    async def slap(
        self, ctx: commands.Context, users: commands.Greedy[discord.User] = None
    ):
        """Slap a user with this command"""
        return await self.do_action(ctx, users)

    @check()
    @commands.hybrid_command(
        extras={"category": Category.ACTIONS, "id": 6}, usage="cuddle <user(s)>"
    )
    @discord.app_commands.describe(users="The people to cuddle with")
    async def cuddle(
        self, ctx: commands.Context, users: commands.Greedy[discord.User] = None
    ):
        """Snuggle up to a user and cuddle them with this command"""
        return await self.do_action(ctx, users)

    @check()
    @commands.hybrid_command(
        extras={"category": Category.ACTIONS, "id": 7}, usage="dance"
    )
    async def dance(self, ctx: commands.Context):
        """Show off your dance moves!"""
        return await self.get_image(ctx)

    @check()
    @commands.hybrid_command(
        extras={"category": Category.ACTIONS, "id": 8}, usage="neko"
    )
    async def neko(self, ctx: commands.Context):
        """uwu"""
        return await self.get_image(ctx)

    @check()
    @commands.hybrid_command(
        extras={"category": Category.ACTIONS, "id": 9}, usage="smile"
    )
    async def smile(self, ctx: commands.Context):
        """Show a bright smile with this command"""
        return await self.get_image(ctx)

    @check()
    @commands.hybrid_command(
        extras={"category": Category.ACTIONS, "id": 10}, usage="blush"
    )
    async def blush(self, ctx: commands.Context):
        """O-Oh! T-thank you for t-the compliment... You have beautiful fingernails too!"""
        return await self.get_image(ctx)

    @check()
    @commands.hybrid_command(
        extras={"category": Category.ACTIONS, "id": 11}, usage="tail"
    )
    async def tail(self, ctx: commands.Context):
        """Wag your tail when you're happy!"""
        return await self.get_image(ctx)

    def _get_view(self, id: int, current: dict) -> View:
        options = [
            discord.SelectOption(label=k, value=k, default=v)
            for k, v in current.items()
        ]
        select = SettingsSelect(
            options, min_values=0, max_values=len(current), custom_id="select"
        )
        button = SettingsButton(
            label="Save",
            style=discord.ButtonStyle.green,
            emoji="\U0001f4be",
            custom_id="save",
        )
        view = View(user_id=id, timeout=100)
        view.timed_out = True

        view.add_item(select)
        view.add_item(button)

        return view

    @check()
    @commands.hybrid_command(
        extras={"category": Category.ACTIONS, "id": 12}, usage="settings"
    )
    async def settings(self, ctx: commands.Context):
        """Change the settings that control who can use what action on you"""

        embed = discord.Embed.from_dict(
            {
                "title": "Settings",
                "description": "By unticking a box users will no longer able to use that action on you",
                "color": 0x3E4A78,
            }
        )

        user = await User.new(ctx.author.id)
        current = user.action_settings

        for action in ACTIONS.keys():
            if action in current:
                embed.add_field(
                    name=action, value="✅" if current[action] else "❌", inline=False
                )
            else:
                embed.add_field(name=action, value="✅", inline=False)
                current[action] = True

        view = self._get_view(ctx.author.id, current)

        msg = await ctx.send(embed=embed, view=view)

        await view.wait()

        if view.timed_out:
            return await view.disable(msg)

        while True:
            embed.clear_fields()

            for action in ACTIONS.keys():
                if (
                    action in view.values
                ):  # view.values contains a list of the remaining values in the select after the user has clicked save
                    current[action] = True
                    embed.add_field(name=action, value="✅", inline=False)
                else:
                    current[action] = False
                    embed.add_field(name=action, value="❌", inline=False)

            await user.set_action_settings(current)
            await view.interaction.response.defer()  # Ideally I would use the response to edit the message, however as view HAS to be redefined above before editing this is impossible
            view = self._get_view(ctx.author.id, current)

            await msg.edit(embed=embed, view=view)

            await view.wait()

            if view.timed_out:
                return await view.disable(msg)

            for val in view.values:
                current[val] = True


Cog = Actions

import discord
from discord.ext import commands
import asyncio, os, random
from pathlib import Path
from logging import info, warning
from typing import List, Union, Optional, cast, Tuple, Dict, TypedDict

from killua.bot import BaseBot
from killua.utils.checks import check
from killua.utils.classes import User
from killua.static.enums import Category, PrintColors
from killua.utils.interactions import View
from killua.static.constants import ACTIONS, KILLUA_BADGES, LIMITED_HUGS_ENDPOINT


class ActionException(Exception):
    def __init__(self, message: str):
        self.message = message


class APIException(ActionException):
    def __init__(self, message: str):
        super().__init__(message)


class AnimeAsset(TypedDict):
    url: str
    anime_name: str

    @classmethod
    def is_anime_asset(cls, data: dict) -> bool:
        return "anime_name" in data


class Artist(TypedDict):
    name: str
    link: str

    @classmethod
    def from_api(cls, data: dict) -> "Artist":
        return cls(name=data["artist_name"], link=data["artist_href"])


class ArtistAsset(TypedDict):
    url: str
    artist: Optional[Artist]
    featured: bool

    @classmethod
    def is_artist_asset(cls, data: dict) -> bool:
        return "artist" in data


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
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
class Actions(commands.GroupCog, group_name="action"):
    def __init__(self, client: BaseBot):
        self.client = client
        self.session = self.client.session
        self.limited_hugs = False

    async def cog_load(self):
        # Get number of files in assets/hugs
        DIR = Path(__file__).parent.parent.parent.joinpath("assets/hugs")

        files = [
            name
            for name in os.listdir(DIR)
            if os.path.isfile(os.path.join(DIR, name)) and not name.startswith(".")
        ]
        number_of_hug_imgs = len(files)

        if number_of_hug_imgs != len(ACTIONS["hug"]["images"]):
            first_filename = cast(str, LIMITED_HUGS_ENDPOINT["url"]).split("/")[-1]
            info(
                f"{PrintColors.WARNING}Number of hug images do not match expected number (expected: {len(ACTIONS['hug']['images'])}, actual: {number_of_hug_imgs}). Will attempt to use {first_filename} every time instead. You can ignore this warning for dev mode.{PrintColors.ENDC}"
            )
            self.limited_hugs = True
            return

        # Constant will be sorted, the files variable will not
        files.sort(key=lambda f: int(cast(str, f).split(".")[0]))
        for filename, expected_filename in zip(files, ACTIONS["hug"]["images"]):
            if (
                filename.split(".")[-1]
                != cast(str, expected_filename["url"]).split(".")[-1]
            ):
                warning(
                    f"{PrintColors.WARNING}Hug image {filename} does not match expected file type. Make sure to edit hugs.json to avoid errors.{PrintColors.ENDC}"
                )

        info(
            f"{PrintColors.OKGREEN}{number_of_hug_imgs} hugs loaded.{PrintColors.ENDC}"
        )

    async def request_action(self, endpoint: str) -> Union[AnimeAsset, ArtistAsset]:
        """
        Fetch an image from the API for the action commands

        Raises:
            APIException: If the API returns an error
        """

        r = await self.session.get(f"https://nekos.best/api/v2/{endpoint}")
        if r.status == 200:
            res = await r.json()

            if "message" in res:
                raise APIException(res["message"])

            raw_asset = res["results"][0]
            if "anime_name" in raw_asset:
                return AnimeAsset(
                    url=raw_asset["url"], anime_name=raw_asset["anime_name"]
                )
            else:
                return ArtistAsset(
                    # No asset is currently returned in this format but the API has
                    # endpoints that return this format so it's here for future use
                    url=raw_asset["url"],
                    artist=Artist.from_api(raw_asset),
                    featured=False,
                )
        else:
            json = await r.json()
            raise APIException(json["message"] if "message" in json else await r.text())

    def add_credit(
        self, embed: discord.Embed, asset: Union[ArtistAsset, AnimeAsset]
    ) -> discord.Embed:
        """
        Adds the artist credit to the embed
        """
        if ArtistAsset.is_artist_asset(asset) and asset["artist"] is not None:
            embed.description = (
                f"-# Art by [{asset['artist']['name']}]({asset['artist']['link']})"
            )
        elif AnimeAsset.is_anime_asset(asset):
            embed.description = f"-# GIF from anime `{asset['anime_name']}`"
        return embed

    async def _get_image(
        self, ctx: commands.Context
    ) -> (
        discord.Message
    ):  # for endpoints like /blush/gif where you don't want to mention a user
        """
        Get the image for one of the action commands from the API without arguments
        """
        image = await self.request_action(ctx.command.name)
        embed = discord.Embed.from_dict(
            {
                "title": "",
                "image": {"url": image["url"]},
                "color": await self.client.find_dominant_color(image["url"]),
            }
        )
        embed = self.add_credit(embed, image)
        return await ctx.send(embed=embed)

    async def save_stat(
        self,
        user: discord.User,
        endpoint: str,
        targeted: bool = False,
        amount: int = 1,
    ) -> Optional[str]:
        """
        Saves the action being done on a user and returns the badge if the user
        has reached a milestone for the action.
        """
        db_user = await User.new(user.id)
        badge = await db_user.add_action(endpoint, targeted, amount)
        return badge

    def generate_users(self, users: List[discord.User], title: str) -> str:
        """
        Parses the list of members and returns a string with their names,
        making sure the string is not too long for the embed title
        """
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

    async def _get_image_url(self, endpoint: str) -> Union[AnimeAsset, ArtistAsset]:
        """
        Gets an image URL and extra info from the API for the action commands
        or, for the hug command, returns a random image from the list of images

        Raises:
            APIException: If the API returns an error
        """
        if endpoint == "hug":
            chosen = (
                LIMITED_HUGS_ENDPOINT
                if self.limited_hugs
                else random.choice(ACTIONS[endpoint]["images"])
            )

            if not cast(str, chosen["url"]).startswith("http"):
                # This could have already been done (Python mutability my beloved)
                chosen["url"] = (
                    self.client.api_url(to_fetch=self.client.is_dev) + chosen["url"]
                )
            return ArtistAsset(chosen)
        else:
            return await self.request_action(endpoint)

    async def action_embed(
        self,
        endpoint: str,
        author: Union[str, discord.User],
        users: Union[str, List[discord.User]],
        disabled: int = 0,
    ) -> Tuple[discord.Embed, Optional[discord.File]]:
        """
        Creates an embed for the action commands with the members and author provided
        as well as adding the image and action text
        """
        if disabled == len(users):
            return "All members targeted have disabled this action.", None

        asset = await self._get_image_url(endpoint)

        text: str = random.choice(ACTIONS[endpoint]["text"])
        text = text.format(
            author="**"
            + (author if isinstance(author, str) else author.display_name)
            + "**",
            user="**"
            + (users if isinstance(users, str) else self.generate_users(users, text))
            + "**",
        )

        embed = discord.Embed(title=text, description="")

        if ArtistAsset.is_artist_asset(asset) and asset["featured"] is True:
            embed.set_footer(
                text="\U000024d8 This artwork has been created specifically for this bot"
            )

        file = None
        if endpoint == "hug":
            image_path = asset["url"].split("image/")[1]
            token, expiry = self.client.sha256_for_api(
                image_path, expires_in_seconds=60 * 60 * 24 * 7
            )
            asset["url"] += f"?token={token}&expiry={expiry}"
            embed, file = await self.client.make_embed_from_api(
                asset["url"], embed, no_token=True
            )
        else:
            # Does not need to be fetched under any conditions
            embed.set_image(url=asset["url"])

        embed.color = await self.client.find_dominant_color(asset["url"])
        if disabled > 0:
            embed.set_footer(
                text=f"{disabled} user{'s' if disabled > 1 else ''} disabled being targetted with this action"
            )
        embed = self.add_credit(embed, asset)
        return embed, file

    async def no_argument(
        self, ctx: commands.Context
    ) -> Optional[Tuple[discord.Embed, Optional[discord.File]]]:
        """
        The user didn't provide any (valid) arguments to the command, so they are asked if they
        want to be hugged. If they respond with "yes", the command is executed with the author as the target.

        This will never get called when the messageable is an interaction
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
            return await self.action_embed(
                ctx.command.name, "Killua", ctx.author.display_name
            )

    def has_disabled(self, user: User, action: str) -> bool:
        """
        Checks if a user has disabled a specific action
        """
        return (
            user.action_settings
            and action in user.action_settings
            and not user.action_settings[action]
        )

    async def _save_stat_for(
        self, user: discord.User, action: str, targeted: bool = False, amount: int = 1
    ) -> None:
        """
        Saves the action being done on a user and sends a message if the user has reached a milestone for the action
        """
        badge = await self.save_stat(user, action, targeted, amount)
        if badge:
            try:
                await user.send(
                    f"Congratulation! You got the {KILLUA_BADGES[badge]} badge for being {action}ed more than 500 times! So many hugs :D. Check your shiny new badge out with `k!pofile`!"
                )
            except discord.Forbidden:
                pass

    async def get_allowed_users(
        self,
        users: List[discord.User],
        command_name: str,
    ) -> Tuple[List[discord.User], int]:
        """
        Returns a list of users that are allowed to use the action command
        """
        allowed: List[discord.User] = []
        disabled = 0
        for user in users:
            m = await User.new(user.id)
            if m.action_settings and self.has_disabled(m, command_name):
                disabled += 1
            else:
                allowed.append(user)
        return allowed, disabled

    async def _do_action(
        self, messageable: Union[commands.Context, discord.Interaction], users: List[discord.User], action: str, author: Union[discord.User, discord.Member]
    ) -> None:
        """
        Executes an action command with the given members

        Raises:
            ActionException: If any exceptions are raised during the execution
        """
        if not users:
            embed, file = await self.no_argument(messageable) 
        elif author == users[0]:
            await messageable.send("Sorry... you can't use this command on yourself") # This will always be a Context obj in that case
            return
        else:
            allowed, disabled = await self.get_allowed_users(users, action or action)

            for user in allowed:
                await self._save_stat_for(user, action or action, True)

            await self._save_stat_for(author, action or action, False, len(allowed))
            embed, file = await self.action_embed(
                action or action, author, users, disabled
            )

        if isinstance(embed, str):
            await self.client.send_message(messageable, content=embed)
        elif (
            embed is not None
        ):  # May be None from no_argument, in which case we don't want to send a message
            if not isinstance(messageable, discord.Interaction):
                view = discord.ui.View(timeout=None)
                view.add_item(
                    discord.ui.Button(
                        label=f"{action.capitalize()} back",
                        style=discord.ButtonStyle.blurple,
                        custom_id=f"action:{action}:{author.id}:{','.join([self.client._encrypt(i.id) for i in users])}:",
                    )
                )
            else: 
                view = None
            await self.client.send_message(messageable, embed=embed, file=file, view=view)

    async def _handle_error(self, ctx: commands.Context, error: Exception) -> None:
        """
        Handles any exceptions raised during the execution of an action command
        """
        if isinstance(error, ActionException):
            embed = discord.Embed.from_dict(
                {
                    "title": "An error occurred",
                    "description": ":x: " + type(error).__name__ + ": " + error.message,
                    "color": int(discord.Colour.red()),
                }
            )
            await ctx.send(embed=embed)
        else:
            raise error

    async def get_image(self, ctx: commands.Context) -> discord.Message:
        """
        Wrapper for _get_image to catch any exceptions raised
        """
        try:
            return await self._get_image(ctx)
        except APIException as e:
            await self._handle_error(ctx, e)

    async def do_action(
        self, ctx: Union[commands.Context, discord.Interaction], users: List[discord.User] = None, action: Optional[str] = None
    ) -> None:
        """
        Wrapper for _do_action to catch any exceptions raised
        """
        try:
            await self._do_action(ctx, users, action or ctx.command.name, ctx.user if isinstance(ctx, discord.Interaction) else ctx.author)
        except ActionException as e:
            await self._handle_error(ctx, e)

    async def _button_checks(self, interaction: discord.Interaction, user_id, not_yet_responded, responded) -> bool:
        """
        Checks if the button is valid and if the user is allowed to use it
        """
        encrypted_user = self.client._encrypt(interaction.user.id)

        if interaction.user.id == int(user_id):
            await interaction.response.send_message(
                f"You cannot use this button on yourself", ephemeral=True
            )
            return False
        if encrypted_user not in not_yet_responded and encrypted_user not in responded:
            await interaction.response.send_message(
                f"You are not who this command was used on, so you cannot use this button", ephemeral=True
            )
            return False
        elif encrypted_user in responded:
            await interaction.response.send_message(
                f"You have already used this button, so you cannot use it again", ephemeral=True
            )
            return False
        elif interaction.channel.permissions_for(interaction.user).send_messages is False:
            await interaction.response.send_message(
                f"You do not have permission to send messages in this channel, so you can't use this button :(", ephemeral=True
            )
            return False
        elif isinstance(interaction.channel, discord.GroupChannel) or isinstance(interaction.channel, discord.DMChannel):
            view = discord.ui.View(timeout=None)
            view.add_item(
                discord.ui.Button(
                    label="Install Killua",
                    style=discord.ButtonStyle.link,
                    url="https://canary.discord.com/oauth2/authorize?client_id=756206646396452975",
                )
            )
            await interaction.response.send_message(
                f"You cannot use this button in DMs... Instead user install Killua and hug the person back that way!!", 
                view=view,
                ephemeral=True
            )
            return False
        return True

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return False

        if not interaction.data["custom_id"].startswith("act"):
            return False
        
        _, action, user_id, not_yet_responded, responded = interaction.data["custom_id"].split(":")
        not_yet_responded = not_yet_responded.split(",")
        responded = responded.split(",")
        if not await self._button_checks(interaction, user_id, not_yet_responded, responded):
            return 
        
        user = await self.client.find_user(interaction.context, user_id)
        if not user:
            return await interaction.response.send_message(
                "User not found", ephemeral=True
            )
        if len(not_yet_responded) == 1:
            # Remove button
            await interaction.message.edit(view=None)
        else:
            # Remove the button for this user
            not_yet_responded.remove(self.client._encrypt(interaction.user.id))
            new_not_yet_responded = ",".join(not_yet_responded)
            responded.append(self.client._encrypt(interaction.user.id))
            new_responded = ",".join(responded)
            await interaction.message.edit(
                view=discord.ui.View(timeout=None).add_item(
                    discord.ui.Button(
                        label=f"{action.capitalize()} back",
                        style=discord.ButtonStyle.blurple,
                        custom_id=f"action:{action}:{user_id}:{new_not_yet_responded}:{new_responded}",
                    )
                )
            )
        return await self.do_action(
           interaction, [user], action
        )
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

    # @check()
    # @commands.hybrid_command(
    #     extras={"category": Category.ACTIONS, "id": 8}, usage="neko"
    # )
    # async def neko(self, ctx: commands.Context):
    #     """uwu"""
    #     return await self.get_image(ctx)

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

    # @check()
    # @commands.hybrid_command(
    #     extras={"category": Category.ACTIONS, "id": 11}, usage="tail"
    # )
    # async def tail(self, ctx: commands.Context):
    #     """Wag your tail when you're happy!"""
    #     return await self.get_image(ctx)

    @check()
    @commands.hybrid_command(
        extras={"category": Category.ACTIONS, "id": 120}, usage="cry"
    )
    async def cry(self, ctx: commands.Context):
        """They thought Ant Man was gonna do WHAT to Thanos???"""
        return await self.get_image(ctx)

    @check()
    @commands.hybrid_command(
        extras={"category": Category.ACTIONS, "id": 121}, usage="smug"
    )
    async def smug(self, ctx: commands.Context):
        """They don't know I use Discord light mode..."""
        return await self.get_image(ctx)

    @check()
    @commands.hybrid_command(
        extras={"category": Category.ACTIONS, "id": 122}, usage="yawn"
    )
    async def yawn(self, ctx: commands.Context):
        """Don't worry I'll go to bed just 5 more Tik Toks!"""
        return await self.get_image(ctx)

    @check()
    @commands.hybrid_command(
        extras={"category": Category.ACTIONS, "id": 123}, usage="nope"
    )
    async def nope(self, ctx: commands.Context):
        """No I don't want to buy your new cryptocurrency Shabloink Coin™️!"""
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

import discord
from discord.ext import commands

import asyncio, os
from datetime import datetime, timedelta
from aiohttp import ClientSession
from random import randint, choice
from discord.ext import commands
from datetime import date
from PIL import Image
from io import BytesIO
from toml import load
from logging import info
from hashlib import sha256
from inspect import signature, Parameter
from functools import partial
from yaml import full_load
from typing import Coroutine, Union, Dict, List, Optional, Tuple, cast

from .static.enums import Category
from .utils.interactions import Modal
from .static.constants import TIPS, LOOTBOXES, DB

cache = {}


def _cached(func, cache):
    """Cache specifically designed for the find_dominant_color function"""

    async def inner(self, args):
        if args in cache:
            return cache[args]
        res = await func(self, args)
        cache[args] = res
        return res

    return inner


cached = partial(_cached, cache=cache)


async def get_prefix(bot: "BaseBot", message: discord.Message):
    if bot.is_dev:
        return commands.when_mentioned_or("kil!", "kil.")(bot, message)
    try:
        from .utils.classes import Guild

        g = await Guild.new(message.guild.id, message.guild.member_count)
        if g is None:
            return commands.when_mentioned_or("k!")(bot, message)
        return commands.when_mentioned_or(g.prefix)(bot, message)
    except Exception:
        # in case message.guild is `None` or something went wrong getting the prefix the bot still NEEDS to react to mentions and k!
        return commands.when_mentioned_or("k!")(bot, message)


class KilluaAPIException(Exception):
    """Raised when the Killua API returns an error"""

    def __init__(self, message: str):
        self.message = message


class BaseBot(commands.AutoShardedBot):
    def __init__(self, *args, **kwargs):
        super().__init__(chunk_guilds_at_startup=False, *args, **kwargs)

        self.session: ClientSession = None
        self.support_server_invite = "https://discord.gg/MKyWA5M"
        self.invite = "https://discord.com/oauth2/authorize?client_id=756206646396452975&scope=bot&permissions=268723414&applications.commands"
        self.url = "https://api.killua.dev"
        # self.ipc = ipc.Server(self, secret_key=IPC_TOKEN)
        self.is_dev = False
        self.run_in_docker = False
        self.force_local = False
        self.startup_datetime = datetime.now()
        self.__cached_formatted_commands: List[commands.Command] = []
        self.cached_skus: List[discord.SKU] = []
        self.cached_entitlements: List[discord.Entitlement] = []

        # Load ../api/Rocket.toml to get port under [debug]
        with open("api/Rocket.toml") as f:
            loaded = load(f)
            self.dev_port = loaded["debug"]["port"]

        with open("docker-compose.yaml") as f:
            loaded = full_load(f)
            self.public_api_port = loaded["services"]["api"]["ports"][0].split(":")[0]

        self.secret_api_key = os.getenv("API_KEY")
        self.hash_secret = os.getenv("HASH_SECRET")

    def api_url(self, *, to_fetch=False, is_for_cards=False):
        if to_fetch or (self.force_local and is_for_cards):
            return (
                f"http://{'api' if self.run_in_docker else '0.0.0.0'}:{self.dev_port}"
            )
        return self.url

    async def setup_hook(self):
        await self.load_extension("jishaku")
        # await self.ipc.start()

        for cog in self.cogs:
            await self.clone_top_level_cog(self.get_cog(cog))
        await self.tree.sync()

        self.cached_skus = await self.fetch_skus()
        self.cached_entitlements = [
            entitlement async for entitlement in self.entitlements(limit=None)
        ]

    async def _turn_top_level_user_installed(self, command: commands.HybridCommand):
        """
        This method is art.

        It takes a command and turns it into a user installable command. It does this by

        1) Creating a new wrapper function that takes a discord.Interaction as its first argument
        (since user installable commands are called with an interaction, not ctx)
        2) Modifying the command signature so dpy correctly infers argument types to the ones from the cloned command
        3) Creating a new discord.app_commands.Command object with the new wrapper function
        4) Modifying the command's arguments to include the correct descriptions
        5) Adding the new command to the global command tree
        """

        async def wrapper(interaction: discord.Interaction, *args, **kwargs):
            return await command.callback(
                command.cog,
                await commands.Context.from_interaction(interaction),
                *args,
                **kwargs,
            )

        # Retrieve the original signature
        original_signature = signature(command.callback)

        # Filter out 'self' and 'commands.Context'
        # Turn 'commands.Context' into 'discord.Interaction'
        new_parameters = [
            (
                param
                if param.annotation is not commands.Context
                else Parameter(
                    "interaction",
                    param.kind,
                    default=param.default,
                    annotation=discord.Interaction,
                )
            )
            for name, param in original_signature.parameters.items()
            if name != "self"
        ]

        # Create a new signature for the wrapper
        new_signature = original_signature.replace(parameters=new_parameters)

        # Apply the new signature to the wrapper
        wrapper.__signature__ = new_signature

        # All of the above is done so dpy will recognize any
        # command arguments in the original command and annotate
        # them in the wrapper, so dpy parses it correctly
        # and includes it in the sync with Discord

        new_command = discord.app_commands.Command(
            name=command.name,
            description=command.help or "No description",
            extras=command.extras,
            callback=wrapper,
            allowed_installs=discord.app_commands.AppInstallationType(
                user=True, guild=False
            ),
            allowed_contexts=discord.app_commands.AppCommandContext(
                guild=True, private_channel=True, dm_channel=True
            ),
        )

        discord.app_commands.commands._populate_descriptions( # pyright: ignore
            new_command._params,
            {
                k: v.description
                for k, v in discord.app_commands.commands._extract_parameters_from_callback(
                    command.callback, command.callback.__globals__
                ).items()
            },
        )
        setattr(new_command, "_cloned", True)
        self.tree.add_command(new_command)

    async def clone_top_level_cog(self, cog: commands.Cog) -> None:
        for cmd in cog.walk_commands():
            if isinstance(cmd, commands.Group):
                for c in cmd.walk_commands():
                    if c.extras.get("clone_top_level", False):
                        await self._turn_top_level_user_installed(c)
                        info(
                            f'Cloned command "{c.qualified_name}" to the top level as user installable'
                        )
            else:
                if cmd.extras.get("clone_top_level", False):
                    await self._turn_top_level_user_installed(cmd)
                    info(
                        f'Cloned command "{cmd.qualified_name}" to the top level as user installable'
                    )

    async def close(self):
        await super().close()
        await self.session.close()

    def __format_command(
        self,
        res: Dict[str, Dict[str, Union[str, Dict[str, str], List[commands.Command]]]],
        cmd: discord.app_commands.Command,
    ) -> Dict[str, Dict[str, Union[str, Dict[str, str], List[commands.Command]]]]:
        """Adds a command to a dict of formatted commands"""

        if (
            "jishaku" in cmd.qualified_name
            or cmd.name == "help"
            or cmd.hidden
            or getattr(cmd, "_cloned", False)
        ):
            return res

        # message_command = self.get_command(cmd.qualified_name)
        if cmd in res[cmd.extras["category"].value["name"]]["commands"]:
            return res

        res[cmd.extras["category"].value["name"]]["commands"].append(cmd)

        return res

    def _get_group(self, command: commands.HybridCommand) -> Optional[str]:
        if isinstance(command.cog, commands.GroupCog):
            return command.cog.__cog_group_name__
        else:
            return " ".join(command.qualified_name.split(" ")[:-1])

    def get_formatted_commands(
        self,
    ) -> Dict[str, Dict[str, Union[str, Dict[str, str], List[commands.Command]]]]:
        """Gets a dictionary of formatted commands"""
        if self.__cached_formatted_commands:
            return self.__cached_formatted_commands

        res = {
            c.value["name"]: {
                "description": c.value["description"],
                "emoji": c.value["emoji"],
                "commands": [],
            }
            for c in Category
        }

        for cmd in self.walk_commands():
            if isinstance(cmd, commands.Group) and cmd.name != "jishaku":
                for c in cmd.commands:
                    res = self.__format_command(res, c)
                continue
            res = self.__format_command(res, cmd)

        self.cached_commands = res
        return res

    def get_raw_formatted_commands(self) -> List[commands.Command]:
        # If the group doesn't exist, check if the command exists
        all_commands = [v["commands"] for v in self.get_formatted_commands().values()]
        # combine all individual lists in all_commands into one in one line
        return [item for sublist in all_commands for item in sublist]

    async def _get_bytes(
        self, image: Union[discord.Attachment, str]
    ) -> Union[None, BytesIO]:
        if isinstance(image, discord.Attachment):
            return BytesIO(await image.read())
        else:
            res = await self.session.get(image)
            if res.status != 200:  # Likely ratelimited
                return
            return BytesIO(await res.read())

    @cached  # cpu intensive and slow but the result does not change, so it is cached
    async def find_dominant_color(self, url: str) -> int:
        """Finds the dominant color of an image and returns it as an rgb tuple"""
        # Resizing parameters
        width, height = 150, 150
        obj = await self._get_bytes(url)
        if not obj:
            return 0x3E4A78
        image = Image.open(obj)
        # Handle if image is a GIF
        if hasattr(image, "is_animated"):
            # Set image variable to first frame of GIF
            image = image.convert("RGB")
        # Resize image
        image = image.resize((width, height), resample=0)
        # Get colors from image object
        pixels = image.getcolors(width * height)
        # Sort them by count number(first element of tuple)
        sorted_pixels = sorted(pixels, key=lambda t: t[0])
        # Get the most frequent color
        dominant_color = sorted_pixels[-1][1]
        # Return integer representation of color
        return (
            dominant_color[0] << 16 | dominant_color[1] << 8 | dominant_color[2]
            if isinstance(dominant_color, tuple)
            else 0x3E4A78
        )

    async def find_user(
        self, ctx: commands.Context, user: str
    ) -> Union[discord.Member, discord.User, None]:
        """Attempts to create a member or user object from the passed string"""
        try:
            res = await commands.MemberConverter().convert(ctx, user)
        except Exception:
            if not user.isdigit():
                return

            res = self.get_user(int(user))
            if not res:
                try:
                    res = await self.fetch_user(int(user))
                except discord.NotFound:
                    return
        return res

    def get_lootbox_from_name(self, name: str) -> Union[int, None]:
        """Gets a lootbox id from its name"""
        for k, v in LOOTBOXES.items():
            if name.lower() == v["name"].lower():
                return k

    def callback_from_command(
        self, command: Coroutine, message: bool, *args, **kwargs
    ) -> Coroutine[discord.Interaction, Union[discord.Member, discord.Message], None]:
        """Turn a command function into a context menu callback"""
        if message:

            async def callback(
                interaction: discord.Interaction, message: discord.Message
            ):
                ctx = await commands.Context.from_interaction(interaction)
                ctx.message = message
                ctx.invoked_by_context_menu = True  # This is added so we can check inside of the command if it was invoked from a modal
                await ctx.invoke(command, text=message.content, *args, **kwargs)

        else:

            async def callback(
                interaction: discord.Interaction, member: discord.Member
            ):
                ctx = await commands.Context.from_interaction(interaction)
                ctx.invoked_by_context_menu = True
                await ctx.invoke(command, str(member.id), *args, **kwargs)

        return callback

    async def _get_text_response_modal(
        self,
        ctx: commands.Context,
        text: str,
        timeout: int = None,
        timeout_message: str = None,
        interaction: discord.Interaction = None,
        *args,
        **kwargs,
    ) -> Union[str, None]:
        """Gets a response from a textinput UI"""
        modal = Modal(title="Answer the question and click submit", timeout=timeout)
        textinput = discord.ui.TextInput(label=text, *args, **kwargs)
        modal.add_item(textinput)

        if interaction:
            await interaction.response.send_modal(modal)
        else:
            await ctx.interaction.response.send_modal(modal)

        await modal.wait()
        if modal.timed_out:
            if timeout_message:
                await ctx.send(timeout_message, delete_after=5)
            return
        if modal.interaction and not modal.interaction.response.is_done():
            await modal.interaction.response.defer()
        return textinput.value

    async def _get_text_response_message(
        self,
        ctx: commands.Context,
        text: str,
        timeout: int = None,
        timeout_message: str = None,
        *args,
        **kwargs,
    ) -> Union[str, None]:
        """Gets a response by waiting a message sent by the user"""

        def check(m: discord.Message):
            return m.author.id == ctx.author.id

        msg = await ctx.send(text)
        try:
            confirm_msg: discord.Message = await self.wait_for(
                "message", check=check, timeout=timeout
            )
            res = confirm_msg.content
        except asyncio.TimeoutError:
            if timeout_message:
                await ctx.send(timeout_message, delete_after=5)
            res = None

        await msg.delete()
        try:
            await confirm_msg.delete()
        except discord.HTTPException:
            pass

        return res

    async def get_text_response(
        self,
        ctx: commands.Context,
        text: str,
        timeout: int = None,
        timeout_message: str = None,
        interaction: discord.Interaction = None,
        *args,
        **kwargs,
    ) -> Union[str, None]:
        """Gets a response from either a textinput UI or by waiting for a response"""

        if (ctx.interaction and not ctx.interaction.response.is_done()) or interaction:
            return await self._get_text_response_modal(
                ctx, text, timeout, timeout_message, interaction, *args, **kwargs
            )
        else:
            return await self._get_text_response_message(
                ctx, text, timeout, timeout_message, *args, **kwargs
            )

    def sha256_for_api(self, endpoint: str, expires_in_seconds: int) -> Tuple[str, str]:
        """Generates a sha256 hash for the Killua API"""
        expiry = str(
            int((datetime.now() + timedelta(seconds=expires_in_seconds)).timestamp())
        )
        return (
            sha256(f"{endpoint}{expiry}{self.hash_secret}".encode()).hexdigest(),
            expiry,
        )

    async def get_approximate_user_count(self) -> int:
        return cast(
            dict,
            (
                await (
                    await DB.guilds.aggregate(
                        [
                            {"$match": {"approximate_member_count": {"$exists": True}}},
                            {
                                "$group": {
                                    "_id": None,
                                    "total": {"$sum": "$approximate_member_count"},
                                }
                            },
                        ]
                    )
                ).to_list(length=None)
            )[0],
        ).get("total", 0)

    async def make_embed_from_api(
        self,
        image_url: str,
        embed: discord.Embed,
        expire_in: int = 60 * 60 * 24 * 7,
        no_token: bool = False,
        thumbnail: bool = False,
    ) -> Tuple[discord.Embed, Optional[discord.File]]:
        """
        Makes an embed from a Killua API image url.

        If the bot is running in a dev environment, the image is downloaded
        and sent as a file.

        Raises:
            KilluaAPIException: If the Killua API returns an error
        """
        file = None
        base_url = self.api_url(to_fetch=self.is_dev)
        if no_token is False:
            image_path = image_url.split(base_url)[1].split("image/")[1]
            token, expiry = self.sha256_for_api(
                image_path, expires_in_seconds=expire_in
            )

        if self.is_dev:
            # Upload the image as attachment instead
            data = await self.session.get(
                image_url + ("" if no_token else f"?token={token}&expiry={expiry}")
            )
            if data.status != 200:
                raise KilluaAPIException(await data.text())

            extension = image_url.split(".")[-1].split("?")[0]
            if thumbnail:
                embed.set_thumbnail(url=f"attachment://image.{extension}")
            else:
                embed.set_image(url=f"attachment://image.{extension}")
            file = discord.File(BytesIO(await data.read()), f"image.{extension}")
        else:
            if thumbnail:
                embed.set_thumbnail(
                    url=image_url
                    + ("" if no_token else f"?token={token}&expiry={expiry}")
                )
            else:
                embed.set_image(
                    url=image_url
                    + ("" if no_token else f"?token={token}&expiry={expiry}")
                )
        return embed, file

    async def update_presence(self):
        status = await DB.const.find_one({"_id": "presence"})
        if status["text"]:
            if not status["activity"]:
                status["activity"] = "playing"

            s = discord.Activity(
                name=status["text"],
                type=getattr(discord.ActivityType, status["activity"]),
            )

            if not status["presence"]:
                status["presence"] = "online"

            return await self.change_presence(
                activity=s, status=getattr(discord.Status, status["presence"])
            )

        a = date.today()
        # The day Killua was born!!
        b = date(2020, 9, 17)
        delta = a - b
        playing = discord.Activity(
            name=f"over {len(self.guilds)} guilds | k! | day {delta.days}",
            type=discord.ActivityType.watching,
        )
        return await self.change_presence(
            status=discord.Status.online, activity=playing
        )

    async def _send_interaction_response(
        self,
        interaction: discord.Interaction,
        *args,
        **kwargs,
    ) -> None:
        """
        Sends an interaction response.
        """
        msg = None
        if kwargs.get("file", False) is None:
            kwargs.pop("file")

        if kwargs.get("view", False) is None:
            kwargs["view"] = discord.utils.MISSING

        if interaction.response.is_done():
            msg = await interaction.followup.send(*args, **kwargs)
        else:
            await interaction.response.send_message(*args, **kwargs)

        if randint(1, 100) < 6:
            message = msg or interaction.message
            await interaction.followup.send(
                f"**Tip:** {choice(TIPS).replace('<prefix>', (await get_prefix(self, message))[2])}",
                ephemeral=True,
            )

        return msg or await interaction.original_response()

    async def _send_messageable_response(
        self,
        messageable: discord.abc.Messageable,
        *args,
        **kwargs,
    ) -> discord.Message:
        msg = await messageable.send(*args, **kwargs)
        if randint(1, 100) < 6:  # 5% probability to send a tip afterwards
            await messageable.send(
                f"**Tip:** {choice(TIPS).replace('<prefix>', (await get_prefix(self, messageable.message))[2]) if hasattr(messageable, 'message') else ('k!' if not self.is_dev else 'kil!')}",
                ephemeral=True,
            )
        return msg

    async def send_message(
        self,
        messageable: Union[discord.abc.Messageable, discord.Interaction],
        *args,
        **kwargs,
    ) -> discord.Message:
        """A helper function sending messages and adding a tip with the probability of 5%"""
        return (
            await self._send_interaction_response(messageable, *args, **kwargs)
            if isinstance(messageable, discord.Interaction)
            else await self._send_messageable_response(messageable, *args, **kwargs)
        )

    def convert_to_timestamp(self, id: int, args: str = "f") -> str:
        """Turns a discord snowflake into a discord timestamp string"""
        return f"<t:{int((id >> 22) / 1000) + 1420070400}:{args}>"

    def _encrypt(self, n: int, b: int = 10000, smallest: bool = True) -> str:
        """Changes an integer into base 10000 but with my own characters resembling numbers. It only returns the last 2 characters as they are the most unique"""
        chars = "".join([chr(i) for i in range(b + 1)][::-1])
        chars = (
            chars.replace(":", "").replace(";", "").replace("-", "").replace(",", "")
        )  # These characters are indicators used in the ids so they should be not be available as characters

        if n == 0:
            return [0]
        digits = []
        while n:
            digits.append(int(n % b))
            n //= b
        return (
            "".join([chars[d] for d in digits[::-1]])[-2:]
            if smallest
            else "".join([chars[d] for d in digits[::-1]])
        )

    def is_user_installed(self, ctx: commands.Context) -> bool:
        if not ctx.interaction:
            return False
        return not ctx.interaction.is_guild_integration()

    def get_command_from_id(self, id: int) -> Union[discord.app_commands.Command, None]:
        for cmd in [*self.walk_commands(), *self.tree.walk_commands()]:
            if cmd.extras["id"] == id:
                return cmd

    async def _dm_check(self, user: discord.User) -> bool:
        """
        Checks if a users dms are open by sending them
        an empty message and either receiving an error for can't
        send an empty message or not allowed
        """
        try:
            await user.send("")
        except Exception as e:
            if isinstance(e, discord.Forbidden):
                return False
            if isinstance(e, discord.HTTPException):
                return True
            return True

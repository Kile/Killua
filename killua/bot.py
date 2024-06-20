import discord
from discord.ext import commands

import asyncio, os
from datetime import datetime
from aiohttp import ClientSession
from random import randint, choice
from discord.ext import commands
from datetime import date
from PIL import Image
from io import BytesIO
from toml import load
from typing import Coroutine, Union, Dict, List, Optional

from .migrate import migrate_requiring_bot
from .static.enums import Category
from .utils.interactions import Modal
from .static.constants import TIPS, LOOTBOXES, DB


def get_prefix(bot: "BaseBot", message):
    if bot.is_dev:
        return commands.when_mentioned_or("kil!", "kil.")(bot, message)
    try:
        from .utils.classes import Guild

        g = Guild(message.guild.id)
        if g is None:
            return commands.when_mentioned_or("k!")(bot, message)
        return commands.when_mentioned_or(g.prefix)(bot, message)
    except Exception:
        # in case message.guild is `None` or something went wrong getting the prefix the bot still NEEDS to react to mentions and k!
        return commands.when_mentioned_or("k!")(bot, message)


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
        self.startup_datetime = datetime.now()
        self.__cached_formatted_commands: List[commands.Command] = []
        self.cached_skus: List[discord.SKU] = []
        self.cached_entitlements: List[discord.Entitlement] = []

        # Load ../api/Rocket.toml to get port under [debug]
        with open("api/Rocket.toml") as f:
            loaded = load(f)
            self.dev_port = loaded["debug"]["port"]

        self.secret_api_key = os.getenv("API_KEY")

    def api_url(self, *, to_fetch=False):
        if to_fetch:
            return (
                f"http://{'api' if self.run_in_docker else '0.0.0.0'}:{self.dev_port}"
            )
        return self.url

    async def setup_hook(self):
        await self.load_extension("jishaku")
        # await self.ipc.start()
        await self.tree.sync()
        self.cached_skus = await self.fetch_skus()
        self.cached_entitlements = [
            entitlement async for entitlement in self.entitlements(limit=None)
        ]
        if DB.const.find_one({"_id": "migrate"})["value"]:
            migrate_requiring_bot(self)
            DB.const.update_one({"_id": "migrate"}, {"$set": {"value": False}})

    async def close(self):
        await super().close()
        await self.session.close()

    def __format_command(
        self,
        res: Dict[str, Dict[str, Union[str, Dict[str, str], List[commands.Command]]]],
        cmd: discord.app_commands.Command,
    ) -> Dict[str, Dict[str, Union[str, Dict[str, str], List[commands.Command]]]]:
        """Adds a command to a dict of formatted commands"""

        if "jishaku" in cmd.qualified_name or cmd.name == "help" or cmd.hidden:
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
        except commands.MemberNotFound:
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
        """Gets a reponse from either a textinput UI or by waiting for a response"""

        if (ctx.interaction and not ctx.interaction.response.is_done()) or interaction:
            modal = Modal(
                title="Anser the question(s) and click submit", timeout=timeout
            )
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
            await modal.interaction.response.defer()

            return textinput.value

        else:

            def check(m: discord.Message):
                return m.author.id == ctx.author.id

            msg = await ctx.send(text)
            try:
                confirmmsg: discord.Message = await self.wait_for(
                    "message", check=check, timeout=timeout
                )
            except asyncio.TimeoutError:
                if timeout_message:
                    await ctx.send(timeout_message, delete_after=5)
                res = None
            else:
                res = confirmmsg.content

            await msg.delete()
            try:
                await confirmmsg.delete()
            except commands.Forbidden:
                pass

            return res

    async def update_presence(self):
        status = DB.const.find_one({"_id": "presence"})
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

    async def send_message(
        self, messageable: discord.abc.Messageable, *args, **kwargs
    ) -> discord.Message:
        """A helper function sending messages and adding a tip with the probability of 5%"""
        msg = await messageable.send(*args, **kwargs)
        if randint(1, 100) < 6:  # 5% probability to send a tip afterwards
            await messageable.send(
                f"**Tip:** {choice(TIPS).replace('<prefix>', get_prefix(self, messageable.message)[2]) if hasattr(messageable, 'message') else ('k!' if not self.is_dev else 'kil!')}",
                ephemeral=True,
            )
        return msg

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
        if not ctx.guild:
            return True
        if len(ctx.guild.members) == ctx.guild.member_count:
            return False  # Best indicator I found
        # if not self.user.id in [m.id for m in ctx.guild.members]: return True
        # ^ Does not work for some reason. That is really dumb. May be an issue with how
        # dpy caches members (assuming they are members when the command is executed
        # on a guild)
        return True

    def get_command_from_id(self, id: int) -> Union[discord.app_commands.Command, None]:
        for cmd in [*self.walk_commands(), *self.tree.walk_commands()]:
            if cmd.extras["id"] == id:
                return cmd

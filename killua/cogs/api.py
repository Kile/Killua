import discord
from discord.ext import commands

from os import environ
from random import choices
from json import loads, dumps
from asyncio import create_task, sleep
from datetime import datetime, timedelta
from zmq import ROUTER, Poller, POLLIN
from zmq.asyncio import Context
from io import BytesIO
from asyncio import create_task
from PIL import Image, ImageDraw, ImageChops
from typing import Tuple, Optional
from logging import error
from copy import deepcopy

from killua.bot import BaseBot
from killua.metrics import VOTES, COMMAND_USAGE
from killua.static.enums import Booster
from killua.utils.classes import User, Guild
from killua.cogs.tags import Tag, Tags
from killua.static.constants import (
    DB,
    LOOTBOXES,
    VOTE_STREAK_REWARDS,
    BOOSTERS,
    BOOSTER_LOGO_IMG,
    DEFAULT_AVATAR,
    NEWS_CHANNEL,
    POST_CHANNEL,
    UPDATE_CHANNEL,
    NEWS_ROLE,
    POST_ROLE,
    UPDATE_ROLE,
    LINK_ICONS,
    GUILD,
    UPDATE_AFTER,
)

from typing import List, Dict, Optional, Union, cast


class NewsMessage:
    def __init__(
        self,
        client: BaseBot,
        id: str,
        title: str,
        content: str,
        author: str,
        _type: str,
        version: Optional[str],
        images: List[str],
        links: Optional[Dict[str, str]],
        notify_users: Optional[List[int]],
        timestamp: datetime,
    ):
        self.client = client
        self.id = id
        self.title = title
        self.content = content
        self.author = author
        self._type = _type
        self.version = version
        self.images = images
        self.links = links
        self.notify_users = notify_users
        self.timestamp = timestamp

    @classmethod
    def from_data(cls, client: BaseBot, data: dict) -> "NewsMessage":
        return cls(
            client=client,
            id=data.get("_id"),
            title=data.get("title"),
            content=data.get("content"),
            author=str(data.get("author")),
            _type=data.get("type"),
            version=data.get("version"),
            images=data.get("images", []),
            links=data.get("links", {}),
            notify_users=data.get("notify_users", {}),
            timestamp=data.get("timestamp"),
        )

    @classmethod
    async def from_id(cls, client: BaseBot, news_id: str) -> "NewsMessage":
        # Fetch from DB
        obj = await DB.news.find_one({"_id": news_id})
        if not obj:
            raise ValueError("News item not found")

        cls.from_data(client, dict(obj))

    @classmethod
    def relevant_channel_id(cls, _type: str) -> int:
        # Get the appropriate channel based on news type
        channel_id = UPDATE_CHANNEL  # Default to update channel

        # You can customize this based on news type
        if _type == "news":
            channel_id = NEWS_CHANNEL
        elif _type == "update":
            channel_id = UPDATE_CHANNEL
        elif _type == "post":
            channel_id = POST_CHANNEL

        return channel_id

    @property
    def relevant_ping(self) -> int:
        if self._type == "news":
            return NEWS_ROLE
        elif self._type == "update":
            return UPDATE_ROLE
        elif self._type == "post":
            return POST_ROLE
        raise ValueError("Invalid news type")

    @property
    def guild(self) -> Optional[discord.Guild]:
        return self.client.get_guild(GUILD) or None

    @property
    def url(self) -> str:
        return f"{'http://localhost:5173' if self.client.is_dev else'https://beta.killua.dev'}/news/{self.id}"

    async def _make_view(
        self,
        include_ping=True
    ) -> Tuple[discord.ui.LayoutView, Optional[List[discord.File]]]:
        """Creates a discord.ui.Container for the news message"""
        last_version = None
        if self._type == "update":
            # Get the update immediately before this one
            last_update = await DB.news.find_one(
                {
                    "type": "update",
                    "published": True,
                    "timestamp": {"$lt": self.timestamp},
                    "_id": {"$ne": self.id},
                },
                sort=[("timestamp", -1)],
            )
            if last_update:
                last_version = last_update.get("version", "0.0.0")

        view = discord.ui.LayoutView()
        container = discord.ui.Container(
            discord.ui.TextDisplay(
                "-# **New "
                + (
                    f"Update `{last_version}` -> `{self.version}`**\n"
                    if last_version
                    else f"{self._type.capitalize()}**\n"
                ) + (f"-# <@&{self.relevant_ping}>\n" if include_ping else "")
                + "# "
                + self.title
            ),
            discord.ui.Separator(),
            discord.ui.TextDisplay(self.content),
            accent_color=0x3E4A78,
        )

        if (
            self.client.is_dev
        ):  # fetch the images
            images = []
            files = []
            for i, image_url in enumerate(self.images):
                try:
                    image_data = await self.client.session.get(image_url)
                    image_bytes = await image_data.read()
                    file = discord.File(BytesIO(image_bytes), filename=f"image_{i}.png")
                    files.append(file)
                    images.append(f"attachment://image_{i}.png")
                except Exception as e:
                    print(f"Failed to download image {image_url}: {e}")
                    continue

            gallery = discord.ui.MediaGallery(
                *[discord.MediaGalleryItem(image) for image in images]
            )
        else:  # Just link the images
            files = None
            gallery = discord.ui.MediaGallery(
                *[discord.MediaGalleryItem(image) for image in self.images]
            )

        buttons = discord.ui.ActionRow(
            *[
                discord.ui.Button(
                    style=discord.ButtonStyle.link,
                    label=key,
                    emoji=LINK_ICONS.get(key.lower(), None),
                    url=value,
                )
                for key, value in (self.links or {}).items()
            ]
        )

        view_on_website = discord.ui.ActionRow(
            discord.ui.Button(
                style=discord.ButtonStyle.link,
                label="View on Website",
                url=self.url,
            )
        )

        if gallery.items:
            container.add_item(gallery)
        if buttons.children:
            container.add_item(buttons)

        container.add_item(view_on_website)

        view.add_item(container)

        return view, files or None

    async def send(self) -> int:
        """Sends the news message to the appropriate channel and returns the message ID"""
        channel = self.guild.get_channel(self.relevant_channel_id(self._type))
        if not channel or not isinstance(channel, discord.TextChannel):
            raise ValueError("Invalid channel")

        view, files = await self._make_view()
        message = await channel.send(view=view, files=files)

        return message.id

    async def edit(self, message_id: int) -> None:
        """Edits an existing news message"""
        channel = self.guild.get_channel(self.relevant_channel_id(self._type))
        if not channel or not isinstance(channel, discord.TextChannel):
            raise ValueError("Invalid channel")

        try:
            message = await channel.fetch_message(message_id)
        except discord.NotFound:
            raise ValueError("Message not found")

        view, attachments = await self._make_view()
        await message.edit(content=None, view=view, attachments=attachments)


class IPCRoutes(commands.Cog):

    def __init__(self, client: BaseBot):
        self.client = client
        create_task(self.start())
        self.command_cache = {}

    async def start(self):
        """Starts the zmq server asynchronously and handles incoming requests"""
        context = Context()
        socket = context.socket(ROUTER)
        address = environ.get("ZMQ_ADDRESS", "tcp://0.0.0.0:3210")
        if self.client.run_in_docker:
            # If run in docker, both client and server connect
            # to the proxy server
            socket.connect(address)
        else:
            # If not run in docker, the server binds to the address
            # to receive requests directly
            socket.bind(address)

        poller = Poller()
        poller.register(socket, POLLIN)

        while True:
            message = await socket.recv_multipart()  # Receive the actual message
            message_data = message[-1].decode()
            # Strip the first byte (first_bit) before parsing JSON
            if message_data and message_data[0] == "\x00":
                message_data = message_data[1:]
            if message_data and message_data[0] == "\x01":
                # Must be run in Docker for this, notify the server about this.
                res = {"error": "For this endpoint to work, the bot must be run in Docker"}
            else:
                decoded = loads(message_data)
                metadata = message[
                    :-1
                ]  # The first parts are metadata, the last part is the actual data
                try:
                    print(f"IPC Route called: {decoded['route']}")
                    res = await getattr(self, decoded["route"].replace("/", "_"))(
                        decoded["data"]
                    )
                except Exception as e:
                    error(f"Error in IPC route {decoded['route']}: {e}")
                    await socket.send_multipart(
                        [*metadata, dumps({"error": str(e)}).encode()]
                    )
                    continue

                if res is None:
                    await socket.send_multipart([*metadata, b'{"status":"ok"}'])
                else:
                    await socket.send_multipart([*metadata, dumps(res).encode()])

    async def download(self, url: str) -> Image.Image:
        """Downloads an image from the given url and returns it as a PIL Image"""
        res = await self.client.session.get(url)

        if res.status != 200:
            raise IOError("Failed to download image")

        image_bytes = await res.read()
        image = Image.open(BytesIO(image_bytes)).convert("RGBA")

        return image

    def make_grey(self, img_colored: Image.Image) -> Image.Image:
        """Converts the given image to grayscale. Respects if the image is transparent"""
        img_colored.load()
        alpha = img_colored.split()[-1]
        img_grey = img_colored.convert("L").convert("RGB")
        img_grey.putalpha(alpha)
        return img_grey

    async def get_background(self) -> ImageDraw.Image:
        """Creates a transparent image to paste the user images on to"""
        background = Image.new("RGBA", (1100, 100), (0, 0, 0, 0))
        return background

    def crop_to_circle(self, im: Image.Image) -> Image.Image:
        """Crops the given image to a circle"""
        bigsize = (im.size[0] * 3, im.size[1] * 3)
        mask = Image.new("L", bigsize, 0)
        ImageDraw.Draw(mask).ellipse((0, 0) + bigsize, fill=255)
        mask = mask.resize(im.size, Image.LANCZOS)
        mask = ImageChops.darker(mask, im.split()[-1])
        im.putalpha(mask)
        return im.copy()

    async def streak_image(
        self, data: List[Union[discord.User, str]], reward: str = None
    ) -> BytesIO:
        """Creates an image of the streak path and returns it as a BytesIO"""
        if len(data) != 11:
            raise TypeError("Invalid Length")

        offset = 0  # Start with a 0 offset
        user_index = next(
            (i for i, x in enumerate(data) if isinstance(x, discord.User)), None
        )  # Find at what position the user image is
        background = await self.get_background()
        drawn = ImageDraw.Draw(background)
        for position, item in enumerate(data):
            if item == "-":
                # This code would be making the line before the user a straight line given that path is completed.
                # However I did not like how this looked so I chose to keep it like the path after the user image.
                # if position < user_index:
                #     drawn.line((offset+5, 50, offset+105, 50), fill="white", width=5)
                # else:
                drawn.line(
                    (offset + 5, 50, offset + 95, 50), fill="white", width=5
                )  # Draw normal path line

            else:
                image = await self.download(
                    (item.avatar.url if item.avatar else DEFAULT_AVATAR)
                    if isinstance(item, discord.User)
                    else item
                )  # Download the image
                size = (100, 100)
                image = image.resize(size)

                if position == user_index:
                    image = self.crop_to_circle(
                        image
                    )  # If the image is the user avatar, make it a circle
                elif position < user_index:
                    image = self.make_grey(
                        image
                    )  # Convert to grayscale if it was already "claimed"

                background.paste(
                    image, (offset, 0)
                )  # Paste the image to the background

                if (
                    reward and position == user_index
                ):  # If the user lands on a reward, paste the reward image to the bottom left of the user image
                    reward_image = await self.download(reward)
                    reward_image = reward_image.resize((50, 50))
                    background.paste(reward_image, (offset - 5, 60), mask=reward_image)

            offset += 100  # Increase the offset by 100 for the next image

        # Turn image into BytesIO
        buffer = BytesIO()
        background.save(buffer, format="PNG")
        buffer.seek(0)

        return buffer

    def _get_reward(self, streak: int, weekend: bool = False) -> int:
        """A pretty simple algorithm that adjusts the reward for voting"""
        # First loop through all lootbox streak rewards from the back and find if any of them apply
        if streak == 0:
            return 100

        for key, value in list(VOTE_STREAK_REWARDS.items())[::-1]:
            if streak % key == 0:
                return value

        # Then follow the algorithm to find whether a "booster" reward applies
        if streak % 7 == 0 or str(streak)[-1] == "7":
            return Booster(
                choices(
                    list(BOOSTERS.keys()),
                    weights=[v["probability"] for v in BOOSTERS.values()],
                )[0]
            )

        # If no streak reward applies, just return the base reward
        return int((120 if weekend else 100) * float(f"1.{int(streak//5)}"))

    def _create_path(
        self, streak: int, user: discord.User, url: str
    ) -> List[Union[discord.User, str]]:
        """
        Creates a path illustrating where the user currently is with vote rewards and what the next rewards are as well as already claimed ones like
        --:boxemoji:--⚫️--:boxemoji:--
        This string has a hard limit of 11 and puts where the user currently is at the center
        """
        # Edgecase where the user has no streak or a streak smaller than 5 which is when it would start in the middle
        if streak < 5:
            path_list = [
                (
                    cast(str, LOOTBOXES[reward]["image"]).format(url)
                    if isinstance(reward := self._get_reward(i), int) and reward < 100
                    else (
                        BOOSTER_LOGO_IMG.format(url)
                        if isinstance(reward, Booster)
                        else "-"
                    )
                )
                for i in range(1, 12)
            ]
            # Replace the character position where the user currently is with a black circle
            path_list[streak - 1] = user
            return path_list

        # Create the path
        before = [
            (
                cast(str, LOOTBOXES[reward]["image"]).format(url)
                if isinstance(reward := self._get_reward(streak - i), int)
                and reward < 100
                else (
                    BOOSTER_LOGO_IMG.format(url) if isinstance(reward, Booster) else "-"
                )
            )
            for i in range(1, 6)
        ]
        after = [
            (
                cast(str, LOOTBOXES[reward]["image"]).format(url)
                if isinstance(reward := self._get_reward(streak + i), int)
                and reward < 100
                else (
                    BOOSTER_LOGO_IMG.format(url) if isinstance(reward, Booster) else "-"
                )
            )
            for i in range(1, 6)
        ]
        path = before[::-1] + [user] + after

        return path

    async def handle_vote(self, data: dict) -> None:
        user_id = data["user"] if data.get("user", False) else data["id"]

        user = await User.new(int(user_id))
        platform = (
            "topgg"
            if "isWeekend" in data and data["isWeekend"] is not None
            else "discordbotlist"
        )
        await user.add_vote(platform)
        VOTES.labels(platform).inc()
        streak = user.voting_streak[platform]["streak"]
        reward: Union[int, Booster] = self._get_reward(
            streak,
            "isWeekend" in data and data["isWeekend"] is not None,
            # Could exist but be None so it needs an or False
        )

        reward_image = (
            cast(str, LOOTBOXES[reward]["image"]).format(
                self.client.api_url(to_fetch=True)
            )
            if isinstance(reward, int) and reward < 100
            else (
                BOOSTER_LOGO_IMG.format(self.client.api_url(to_fetch=True))
                if isinstance(reward, Booster)
                else None
            )
        )

        usr = self.client.get_user(user_id) or await self.client.fetch_user(user_id)

        path = self._create_path(streak, usr, self.client.api_url(to_fetch=True))

        # Whitelist images for token
        token, expiry = self.client.sha256_for_api("vote_rewards", 60)

        # Add token to the image endpoints
        path = [
            (
                item
                if not isinstance(item, str) or item == "-"
                else item + f"?token={token}&expiry={expiry}"
            )
            for item in path
        ]

        image = await self.streak_image(
            path,
            reward_image + f"?token={token}&expiry={expiry}" if reward_image else None,
        )
        file = discord.File(image, filename="streak.png")

        embed = discord.Embed.from_dict(
            {
                "title": "Thank you for voting!",
                "description": (
                    f"Well done for keeping your voting **streak** 🔥 of {streak} for"
                    if streak > 1
                    else "Thank you for voting on"
                )
                + f" {'top.gg' if 'isWeekend' in data and data['isWeekend'] is not None  else 'discordbotlist'}! As a reward I am happy to award with "
                + (
                    (
                        f"{reward} Jenny"
                        if reward >= 100
                        else f"a lootbox {LOOTBOXES[reward]['emoji']} {LOOTBOXES[reward]['name']}"
                    )
                    if isinstance(reward, int)
                    else f"the {BOOSTERS[reward.value]['emoji']} `{BOOSTERS[reward.value]['name']}` booster"
                )
                + f"! You are **{5 - (streak % 5)}** votes away from the next reward!",
                "color": 0x3E4A78,
            }
        )
        embed.set_image(url="attachment://streak.png")

        if isinstance(reward, Booster):
            await user.add_booster(reward.value)
        elif reward < 100:
            await user.add_lootbox(reward)
        else:
            await user.add_jenny(reward)

        try:
            await usr.send(embed=embed, file=file)
        except discord.HTTPException:
            pass

    async def top(self, _) -> List[dict]:
        """Returns a list of the top 50 users by the amount of jenny they have"""
        members = await DB.teams.find(
            {"id": {"$in": [x.id for x in self.client.users]}}
        )
        top = sorted(members, key=lambda x: x["points"], reverse=True)[:50]
        res = []
        for t in top:
            u = self.client.get_user(t["id"])
            res.append(
                {
                    "name": u.display_name,
                    "tag": u.discriminator,
                    "avatar": str(u.avatar.url),
                    "jenny": t["points"],
                }
            )
        return res

    def get_message_command(self, cmd: str):
        c = self.client.get_command(cmd)
        if not c:
            c = self.client.get_command(cmd.split(" ")[-1])
        return c

    def format_command(self, cmd: commands.HybridCommand) -> dict:
        checks = cmd.checks

        premium_guild, premium_user, cooldown = False, False, False

        if [c for c in checks if hasattr(c, "premium_guild_only")]:
            premium_guild = True

        if [c for c in checks if hasattr(c, "premium_user_only")]:
            premium_user = True

        if res := [c for c in checks if hasattr(c, "cooldown")]:
            check = res[0]
            cooldown = getattr(check, "cooldown", False)

        usage_slash = (
            (cmd.qualified_name.replace(cmd.name, "") + cmd.usage)
            if not isinstance(cmd.cog, commands.GroupCog)
            else cmd.cog.__cog_group_name__ + " " + cmd.usage
        )
        usage_message = (
            ("k!" + cmd.qualified_name.replace(cmd.name, "") + cmd.usage)
            if not isinstance(cmd.cog, commands.GroupCog)
            else "k!" + cmd.usage
        )

        return {
            "name": cmd.name,
            "slash_usage": usage_slash,
            "description": cmd.help or "No help found...",
            "aliases": cmd.aliases,
            "cooldown": cooldown or 0,
            "premium_guild": premium_guild,
            "premium_user": premium_user,
            "message_usage": usage_message,
        }

    async def commands(self, _) -> dict:
        """Returns all commands with descriptions etc"""
        raw = self.client.get_raw_formatted_commands()

        to_be_returned: Dict[str, Dict[str, Union[str, list]]] = {}

        for cmd in raw:
            formatted = self.format_command(cmd)

            if cmd.extras["category"].name in to_be_returned:
                to_be_returned[cmd.extras["category"].name]["commands"].append(
                    formatted
                )
            else:
                to_be_returned[cmd.extras["category"].name] = {
                    "commands": [formatted],
                    "description": cmd.extras["category"].value["description"],
                    "name": cmd.extras["category"].value["name"],
                    "emoji": cmd.extras["category"].value["emoji"],
                }

        return to_be_returned

    async def stats(self, _) -> dict:
        """Gets stats about the bot"""
        return {
            "guilds": len(self.client.guilds),
            "shards": self.client.shard_count,
            "registered_users": await DB.teams.count_documents({}),
            "user_installs": (
                await self.client.application_info()
            ).approximate_user_install_count,
            "last_restart": self.client.startup_datetime.timestamp(),
        }

    async def get_discord_user(self, data) -> dict:
        """Getting additional info about a user with their id"""
        res = self.client.get_user(data["user"])
        return {
            "name": res.display_name,
            "username": res.name,
            "avatar": str(res.avatar.url),
            "created_at": res.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    async def discord_application_authorized(self, data) -> None:
        """Handles the application authorized webhook"""
        user_id = data["user"]["id"]
        user = await User.new(user_id)
        await user.register_user_installed_usage()

    async def discord_application_deauthorized(self, data) -> None:
        """Handles the application deauthorized webhook"""
        user_id = data["user"]["id"]
        user = await User.new(user_id)
        await user.register_user_uninstalled_usage()

    # async def update_guild_cache(self, data) -> None:
    #     """Makes sure the local cache is up to date with the db"""
    #     guild = await Guild.new(data["id"])
    #     guild.prefix = data["prefix"]
    #     guild.commands = {v for _, v in data.commands.items()}

    async def vote(self, data) -> None:
        """Registers a vote from either topgg or dbl"""
        await self.handle_vote(data)

    async def heartbeat(self, _) -> dict:
        """Just a simple heartbeat to see if the bot and IPC connection is alive"""
        return {"status": "ok"}

    def _convert_datetime(self, obj):
        """Helper function to convert datetime objects to ISO strings"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {k: self._convert_datetime(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_datetime(item) for item in obj]
        else:
            return obj

    def _convert_snowflakes(self, obj):
        """Helper function to convert snowflake (discord IDs) objects to strings"""
        # check if the integer has more than 17 digits
        if isinstance(obj, int) and len(str(obj)) > 17:
            return str(obj)
        elif isinstance(obj, dict):
            return {k: self._convert_snowflakes(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_snowflakes(item) for item in obj]
        else:
            return obj

    def jsonify(self, obj):
        """Helper function to convert objects to JSON transferable format"""
        return self._convert_snowflakes(self._convert_datetime(obj))

    async def user_info(self, data: dict) -> dict:
        """Gets user info by Discord ID and returns it with display name and avatar URL"""
        user_id = data.get("user_id")
        if not user_id:
            raise ValueError("User ID is required")

        # Convert user_id to int if it's a string
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            raise ValueError("Invalid user ID format")

        # Get Discord user
        user = self.client.get_user(user_id) or await self.client.fetch_user(user_id)
        if not user:
            raise ValueError("User not found")

        # Get user data from database
        user_data = await User.new(user_id)

        # Save email if provided
        email = data.get("email")
        if email and email != user_data.email:
            await user_data.set_email(email)

        # Return flat dictionary structure with all user data and Discord info
        response_data = {
            "id": str(user_data.id),
            "email": user_data.email,
            "display_name": user.display_name,
            "avatar_url": str(user.avatar.url) if user.avatar else None,
            "jenny": user_data.jenny,
            "daily_cooldown": user_data.daily_cooldown,
            "met_user": user_data.met_user,
            "effects": user_data.effects,
            "rs_cards": user_data.rs_cards,
            "fs_cards": user_data.fs_cards,
            "badges": user_data.badges,
            "rps_stats": user_data.rps_stats,
            "counting_highscore": user_data.counting_highscore,
            "trivia_stats": user_data.trivia_stats,
            "achievements": user_data.achievements,
            "votes": user_data.votes,
            "voting_streak": user_data.voting_streak,
            "voting_reminder": user_data.voting_reminder,
            "premium_guilds": user_data.premium_guilds,
            "lootboxes": user_data.lootboxes,
            "boosters": user_data.boosters,
            "weekly_cooldown": (
                user_data.weekly_cooldown if user_data.weekly_cooldown else None
            ),
            "action_settings": user_data.action_settings,
            "action_stats": user_data.action_stats,
            "locale": user_data.locale,
            "has_user_installed": user_data.has_user_installed,
            "is_premium": user_data.is_premium,
            "premium_tier": user_data.premium_tier,
            "email_notifications": user_data.email_notifications,
        }

        if data.get("from_admin", False) is False:
            # Fire and forget background task
            create_task(self._register_login(user, user_data))

        return self.jsonify(response_data)

    async def user_edit(self, data: dict) -> dict:
        """Edits user info by Discord ID. Only certain fields are editable."""
        user_id = data.get("user_id")
        if not user_id:
            raise ValueError("User ID is required")

        # Convert user_id to int if it's a string
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            raise ValueError("Invalid user ID format")

        # Get user data from database
        user = await User.new(user_id)

        # Editable fields
        editable_fields = {
            "voting_reminder",
            "action_settings",
            "email_notifications",
        }

        update_data = {}
        for key in editable_fields:
            if key in data and data[key] is not None:
                update_data[key] = data[key]

        if update_data:
            for key, value in update_data.items():
                # The format of the input is trusted to be correct due to 
                # Rust's strict typing on the API side
                setattr(user, key, value)
                await user._update_val(key, value)

        return {"success": True, "message": "User updated successfully"}

    async def _register_login(self, user: discord.User, user_data: User) -> None:
        """The actual background work you want to do"""
        first_login = await user_data.register_login()
        if not first_login:
            return

        # Add free golden lootbox and 1000 Jenny to user
        await user_data.add_lootbox(4)
        await user_data.add_jenny(1000)

        # Try to send the user a DM about their reward
        if user:
            try:
                await user.send(
                    embed=discord.Embed.from_dict(
                        {
                            "title": "Thank you for checking out Killua's new website!",
                            "description": "You've received a free golden lootbox and 1000 Jenny!",
                            "color": 0x3E4A78,
                        }
                    )
                )
            except discord.HTTPException:
                pass  # Ignore failure

    # User management routes
    async def user_get_basic_details(self, data: dict) -> dict:
        """Get basic Discord user details (display name and avatar URL)"""
        user_id = data.get("user_id")
        if not user_id:
            raise ValueError("User ID is required")

        # Convert user_id to int if it's a string
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            raise ValueError("Invalid user ID format")

        # Get Discord user
        user = self.client.get_user(user_id) or await self.client.fetch_user(user_id)
        if not user:
            raise ValueError("User not found")

        return {
            "display_name": user.display_name,
            "avatar_url": str(user.avatar.url) if user.avatar else None,
        }

    async def news_save(self, data: dict) -> dict:
        """Save a new news item"""
        # Generate unique ID using timestamp
        news_id = str(int(datetime.now().timestamp() * 1000))

        news_item = {
            "_id": news_id,
            "title": data["title"],
            "content": data["content"],
            "type": data["type"],
            "likes": [],
            "author": int(data["author"]),
            "version": data.get("version"),
            "messageId": None,
            "published": data["published"],
            "timestamp": datetime.now(),
            "links": data.get("links", {}),
            "images": data.get("images", []),
            "notify_users": data["notify_users"],
        }

        await DB.news.insert_one(news_item)

        if data.get("published", False):
            # If published, send Discord message
            message_id = await self._send_discord_message(news_item)
            await DB.news.update_one(
                {"_id": news_id}, {"$set": {"messageId": message_id}}
            )
            return {"news_id": news_id, "message_id": message_id}

        return {"news_id": news_id, "message_id": None}

    async def news_delete(self, data: dict) -> dict:
        """Delete a news item"""
        news_id = data.get("news_id")
        if not news_id:
            raise ValueError("News ID is required")

        news_item = await DB.news.find_one({"_id": news_id})
        if not news_item:
            raise ValueError("News item not found")

        # Delete Discord message if it exists
        message_id = news_item.get("messageId")
        if message_id:
            await self._delete_discord_message(news_item["type"], message_id)

        await DB.news.delete_one({"_id": news_id})

        return {"status": "deleted"}

    async def news_edit(self, data: dict) -> dict:
        """Edit a news item"""
        news_id = data.get("news_id")
        if not news_id:
            raise ValueError("News ID is required")

        news_item = await DB.news.find_one({"_id": news_id})
        if not news_item:
            raise ValueError("News item not found")

        old_published = news_item.get("published", False)

        # Prepare update data
        for key, value in data.items():
            if key not in news_item:
                continue
            if key in ["news_id", "message_id"]:
                continue
            if key == "author":
                value = int(value)
            if key == "timestamp" and isinstance(value, str):
                value = datetime.fromisoformat(value)
            news_item[key] = value

        # Handle published status change
        if "published" in data:
            new_published = news_item.get("published", False)

            if not old_published and new_published:
                # Publishing for the first time - send Discord message
                message_id = await self._send_discord_message(news_item)
                news_item["messageId"] = message_id
            elif old_published and new_published and news_item.get("messageId"):
                # Already published, edit existing message
                await self._edit_discord_message(news_item["messageId"], news_item)
            elif old_published and not new_published and news_item.get("messageId"):
                # Unpublishing - delete Discord message
                await self._delete_discord_message(
                    news_item["type"], news_item["messageId"]
                )
                news_item["messageId"] = None

            news_item["published"] = new_published

        await DB.news.update_one({"_id": news_id}, {"$set": news_item})

        return {"news_id": news_id, "message_id": news_item.get("messageId")}

    async def _send_discord_message(self, data: dict) -> int:
        """Send a Discord message for a news item"""
        news_message = NewsMessage.from_data(self.client, data)
        if news_message.timestamp < UPDATE_AFTER or self.client.is_dev:
            # Don't send messages for old news items or in dev mode
            return None
        message_id = await news_message.send()
        return message_id

    async def _edit_discord_message(self, message_id: str, data: dict) -> None:
        """Edit an existing Discord message"""
        try:
            news_message = NewsMessage.from_data(self.client, data)
            if news_message.timestamp < UPDATE_AFTER or self.client.is_dev:
                # If the news item is old, do nothing
                return None
            await news_message.edit(message_id)
        except discord.NotFound:
            # Message was deleted, ignore
            pass

    async def _delete_discord_message(self, news_type: str, message_id: str) -> None:
        """Delete a Discord message"""
        channel_id = NewsMessage.relevant_channel_id(news_type)
        if not channel_id:
            raise ValueError(f"Invalid news type: {news_type}")

        channel = self.client.get_channel(channel_id)

        if not channel:
            raise ValueError(f"Channel {channel_id} not found")

        try:
            message = await channel.fetch_message(int(message_id))
            await message.delete()
        except discord.NotFound:
            # Message was already deleted, ignore
            pass

    async def guild_editable(self, data: dict) -> dict:
        """Returns whether a guild is editable by the bot"""
        guild_ids = data.get("guild_ids")
        bot_is_on = []

        for gid in guild_ids:
            guild = self.client.get_guild(int(gid))
            if guild:
                bot_is_on.append(gid)

        return {
            "editable": bot_is_on,
            "premium": await Guild.get_premium_subset(bot_is_on),
        }
    
    async def guild_info(self, data: dict) -> dict:
        """Gets guild info by Discord ID and returns it with name and icon URL"""
        guild_id = data.get("guild_id")
        if not guild_id:
            raise ValueError("Guild ID is required")

        # Convert guild_id to int if it's a string
        try:
            guild_id = int(guild_id)
        except (ValueError, TypeError):
            raise ValueError("Invalid guild ID format")

        # Get Discord guild
        guild = self.client.get_guild(guild_id)
        if not guild:
            raise ValueError("Guild not found")
        
        db_guild = await Guild.new(guild_id)

        tag_copy = deepcopy(db_guild.tags) 
        # Do not want to mass up the cached tags with datetime objects
        for tag in tag_copy:
            if "created_at" in tag:
                tag["created_at"] = cast(datetime, tag["created_at"]).isoformat()

            owner_id = tag.get("owner")
            owner_obj = guild.get_member(owner_id) or await self.client.fetch_user(owner_id)
            tag["owner"] = {
                "user_id": owner_obj.id,
                "display_name": owner_obj.display_name,
                "avatar_url": owner_obj.avatar.url if owner_obj.avatar else None
            }

        return {
            "badges": db_guild.badges,
            "prefix": db_guild.prefix,
            "is_premium": db_guild.is_premium,
            "bot_added_on": db_guild.added_on.isoformat() if db_guild.added_on else None,
            "tags": tag_copy,
            "approximate_member_count": db_guild.approximate_member_count,
            "name": guild.name,
            "icon_url": str(guild.icon.url) if guild.icon else None,
        }
    
    async def guild_edit(self, data: dict) -> dict:
        """Edits guild info by Discord ID. Only certain fields are editable."""
        guild_id = data.get("guild_id")
        if not guild_id:
            raise ValueError("Guild ID is required")

        # Convert guild_id to int if it's a string
        try:
            guild_id = int(guild_id)
        except (ValueError, TypeError):
            raise ValueError("Invalid guild ID format")

        # Get guild data from database
        guild = await Guild.new(guild_id)

        # Editable fields
        editable_fields = {
            "prefix",
            "tags",
        }

        update_data = {}
        for key in editable_fields:
            if key in data and data[key] is not None:
                update_data[key] = data[key]

        if update_data:
            for key, value in update_data.items():
                # The format of the input is trusted to be correct due to 
                # Rust's strict typing on the API side
                setattr(guild, key, value)
                await guild._update_val(key, value)

        return {"success": True, "message": "Guild updated successfully"}
    
    async def guild_tag_create(self, data: dict) -> dict:
        """Creates a new tag in the guild"""
        guild_id = data.get("guild_id")
        if not guild_id:
            raise ValueError("Guild ID is required")
        
        guild = self.client.get_guild(guild_id)
        if not guild:
            raise ValueError("Guild not found")
        db_guild = await Guild.new(guild_id)

        # Create the tag
        error = await Tags.initial_new_tag_validation(data["name"], guild, db_guild, data["user_id"])

        if error:
            return {"success": False, "message": error}
        
        error = Tags._validate_tag_details(data["name"], data["content"])

        if error:
            return {"success": False, "message": error}

        tag = await Tag.new(guild_id, data["name"])
        await tag.create(name=data["name"], content=data["content"], owner=data["user_id"])

        return {"success": True, "message": "Tag created successfully"}
    
    async def guild_tag_delete(self, data: dict) -> dict:
        """Deletes a tag in the guild"""
        guild_id = data.get("guild_id")
        if not guild_id:
            raise ValueError("Guild ID is required")
        
        guild = self.client.get_guild(guild_id)
        if not guild:
            raise ValueError("Guild not found")

        tag = await Tag.new(guild_id, data["name"])

        if tag.found is False:
            return {"success": False, "message": "Tag not found"}

        await tag.delete()

        return {"success": True, "message": "Tag deleted successfully"}
    
    async def guild_tag_edit(self, data: dict) -> dict:
        """Edits a tag in the guild"""
        guild_id = data.get("guild_id")
        if not guild_id:
            raise ValueError("Guild ID is required")
        
        guild = self.client.get_guild(guild_id)
        if not guild:
            raise ValueError("Guild not found")

        tag = await Tag.new(guild_id, data["name"])

        if tag.found is False:
            return {"success": False, "message": "Tag not found"}

        error = Tags._validate_tag_details(data.get("new_name", None), data.get("content", None))

        if error:
            return {"success": False, "message": error}

        if "new_name" in data and data["new_name"] and data["new_name"] != tag.name:
            await tag.update(key="name", value=data["new_name"])
        if "content" in data and data["content"] and data["content"] != tag.content:
            await tag.update(key="content", value=data["content"])

        if "new_owner" in data and data["new_owner"] and data["new_owner"] != tag.owner:
            await tag.transfer(to=data["new_owner"])

        return {"success": True, "message": "Tag edited successfully"}
    
    async def guild_command_usage(self, data: dict) -> Union[dict, list]:
        """Returns command usage stats for the server"""
        if self.client.run_in_docker is False:
            return {"error": "Command usage stats are only available when running in Docker."}

        _from = data.get("from", round((datetime.now() - timedelta(days=14)).timestamp(), 3))
        to = data.get("to", round(datetime.now().timestamp(), 3))
        interval = data.get("interval", "1h")
        guild_id = data.get("guild_id", None)
        if not guild_id:
            return {"error": "Guild ID is required."}
        
        query = f"http://prometheus:9090/api/v1/query_range?query=discord_command_usage%7Bguild_id%3D%22{guild_id}%22%7D&step={interval}&start={_from}&end={to}"
        res = await self.client.session.get(query)
        body = await res.json()

        if body["status"] == "error":
            return {"error": body["error"]}

        body = body["data"]["result"]

        formatted = []
        for res in body:
            formatted.append(
                {
                    "name": res["metric"]["command"],
                    "group": res["metric"]["group"],
                    "command_id": int(res["metric"]["command_id"]),
                    "values": [(str(timestamp), int(value)) for timestamp, value in res["values"]]
                }
            )

        return formatted

Cog = IPCRoutes

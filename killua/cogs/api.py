import discord
from discord.ext import commands

from random import choices
from json import loads, dumps
from asyncio import create_task
from zmq import REP, Poller, POLLIN
from zmq.asyncio import Context

from io import BytesIO
from PIL import Image, ImageDraw, ImageChops
from killua.bot import BaseBot
from killua.static.enums import Booster
from killua.utils.classes import User, Guild
from killua.static.constants import DB, LOOTBOXES, IPC_TOKEN, VOTE_STREAK_REWARDS, BOOSTERS, BOOSTER_LOGO_IMG, DEFAULT_AVATAR

from typing import List, Dict, Union

class IPCRoutes(commands.Cog):

    def __init__(self, client: BaseBot):
        self.client = client
        create_task(self.start())
        self.command_cache = {}

    async def start(self):
        """Starts the zmq server asyncronously and handles incoming requests"""
        context = Context()
        socket = context.socket(REP)
        socket.bind("ipc:///tmp/killua.ipc")

        poller = Poller()
        poller.register(socket, POLLIN)

        while True:
            # socks = dict(await poller.poll())
            # print(socks)
            # if socket in socks and socks[socket] == POLLIN:
            #     message = await socket.recv_multipart()
            #     identity, request = message
            #     decoded = loads(request.decode())
            #     print(identity, decoded)
            #     res = await getattr(self, decoded["route"])(decoded["data"])
            #     if res:
            #         await socket.send_multipart([identity, dumps(res).encode()])
            #     else:
            #         await socket.send_multipart([identity, b'{"status":"ok"}'])
            message = await socket.recv()
            # for message in messages:
            #     print(messages)
            #     print(message)
                #identity, message = message
                #print(identity)
            decoded = loads(message.decode())
            print(decoded)
            try:
                res = await getattr(self, decoded["route"])(decoded["data"])
            except Exception as e:
                await socket.send(dumps({"error": str(e)}).encode())
                continue
            
            if res:
                await socket.send(dumps(res).encode())
            else:
                await socket.send(b'{"status":"ok"}')
        # context = Context()

        # auth = AsyncioAuthenticator(context)
        # auth.start()
        # auth.configure_plain(domain="*", passwords={"killua": IPC_TOKEN})
        # auth.allow("127.0.0.1")

        # socket = context.socket(REP)
        # socket.plain_server = True
        # socket.bind("tcp://localhost:5555")

        # poller = Poller()
        # # poller.register(socket, POLLIN)

        # while True:
        #     from asyncio import wait_for, TimeoutError
        #     print("Loop")
        #     try:
        #         print(await wait_for(socket.recv_multipart(), timeout=5))
        #     except TimeoutError:
        #         continue
            # socks = dict(await poller.poll(1000))
            # print(socks)
            # if socket in socks and socks[socket] == POLLIN:
            #     message = await socket.recv_multipart()
            #     identity, request = message
            #     decoded = loads(request.decode())
            #     res = await getattr(self, decoded["route"])(decoded["data"])
            #     print(f"Received request: {decoded['route']} with data: {decoded['data']} and returned: {res}")
            #     if res:
            #         await socket.send_multipart([identity, dumps(res).encode()])
            #     else:
            #         await socket.send_multipart([identity, b'{"status":"ok"}'])

    async def download(self, url: str) -> Image.Image:
        """Downloads an image from the given url and returns it as a PIL Image"""
        res = await self.client.session.get(url)

        if res.status != 200:
            raise Exception("Failed to download image")
        
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

    async def streak_image(self, data: List[Union[discord.User, str]], reward: str = None) -> BytesIO:
        """Creates an image of the streak path and returns it as a BytesIO"""
        if len(data) != 11:
            return Exception("Invalid Length")
        
        offset = 0 # Start with a 0 offset
        user_index = next(
            (i for i, x in enumerate(data) if isinstance(x, discord.User)), 
            None
        ) # Find at what positon the user image is
        background = await self.get_background()
        drawn = ImageDraw.Draw(background)
        for position, item in enumerate(data):
            if item == "-":
                # Thise code would be making the line before the user a straight line given that path is completed.
                # However I did not like how this looked so I chose to keep it like the path after the user image.
                # if position < user_index:
                #     drawn.line((offset+5, 50, offset+105, 50), fill="white", width=5)
                # else:
                drawn.line((offset+5, 50, offset+95, 50), fill="white", width=5) # Draw normal path line

            else:
                image = await self.download((item.avatar.url if item.avatar else DEFAULT_AVATAR) if isinstance(item, discord.User) else item) # Download the image
                size = (100, 100)
                image = image.resize(size)

                if position == user_index:
                    image = self.crop_to_circle(image) # If the image is the user avatar, make it a circle
                elif position < user_index:
                    image = self.make_grey(image) # Convert to grayscale if it was already "claimed"

                background.paste(image, (offset, 0)) # Paste the image to the background

                if reward and position == user_index: # If the user lands on a reward, paste the reward image to the bottom left of the user image
                    reward_image = await self.download(reward)
                    reward_image = reward_image.resize((50, 50))
                    background.paste(reward_image, (offset-5, 60), mask=reward_image)

            offset += 100 # Increase the offset by 100 for the next image

        # Turn image into BytesIO
        buffer = BytesIO()
        background.save(buffer, format="PNG")
        buffer.seek(0)

        return buffer

    def _get_reward(self, streak: int, weekend: bool = False) -> int:
        """A pretty simple algorithm that adjusts the reward for voting"""
        # First loop through all lootbox streak rwards from the back and find if any of them apply
        if streak == 0:
            return 100

        for key, value in list(VOTE_STREAK_REWARDS.items())[::-1]:
            if streak % key == 0:
                return value
        
        # Then follow the algorithm to find whether a "booster" reward applies
        if streak % 7 == 0 or str(streak)[-1] == "7":
            return Booster(choices(list(BOOSTERS.keys()), weights=[v["probability"] for v in BOOSTERS.values()])[0])

        # If no streak reward applies, just return the base reward
        return int((120 if weekend else 100) * float(f"1.{int(streak//5)}"))

    def _create_path(self, streak: int, user: discord.User) -> str:
        """
        Creates a path illustrating where the user currently is with vote rewards and what the next rewards are as well as already claimed ones like
        --:boxemoji:--⚫️--:boxemoji:--
        This string has a hard limit of 11 and puts where the user currently is at the center
        """
        # Edgecase where the user has no streak or a streak smaller than 5 which is when it would start in the middle
        if streak < 5:
            path_list = [LOOTBOXES[reward]["image"] if isinstance(reward := self._get_reward(i), int) and reward < 100 else (BOOSTER_LOGO_IMG if isinstance(reward, Booster) else "-") for i in range(1, 12)]
            # Replace the character position where the user currently is with a black circle
            path_list[streak-1] = user
            return path_list

        # Create the path
        before = [LOOTBOXES[reward]["image"] if isinstance(reward := self._get_reward(streak-i), int) and reward < 100 else (BOOSTER_LOGO_IMG if isinstance(reward, Booster) else "-") for i in range(1, 6)]
        after = [LOOTBOXES[reward]["image"] if isinstance(reward := self._get_reward(streak+i), int) and reward < 100 else (BOOSTER_LOGO_IMG if isinstance(reward, Booster) else "-") for i in range(1, 6)]
        path = before[::-1] + [user] + after

        return path


    async def handle_vote(self, data: dict) -> None:
        user_id = data["user"] if "user" in data else data["id"]

        user = User(int(user_id))
        user.add_vote("topgg" if "isWeekend" in data else "discordbotlist")
        streak = user.voting_streak["topgg" if "isWeekend" in data else "discordbotlist"]["streak"]
        reward: Union[int, Booster] = self._get_reward(streak, data["isWeekend"] if hasattr(data, "isWeekend") else False)

        usr = self.client.get_user(user_id) or await self.client.fetch_user(user_id)

        path = self._create_path(streak, usr)
        image = await self.streak_image(path, (LOOTBOXES[reward]["image"] if isinstance(reward, int) and reward < 100 else (BOOSTERS[reward.value]["image"] if isinstance(reward, Booster) else None)))
        file = discord.File(image, filename="streak.png")

        embed = discord.Embed.from_dict({
            "title": "Thank you for voting!",
            "description": (f"Well done for keeping your voting **streak** 🔥 of {streak} for" if streak > 1 else "Thank you for voting on ") + f" {'top.gg' if 'isWeekend' in data else 'discordbotlist'}! As a reward I am happy to award with " + \
            ((f"{reward} Jenny" if reward >= 100 else f"a lootbox {LOOTBOXES[reward]['emoji']} {LOOTBOXES[reward]['name']}") if isinstance(reward, int) else f"the {BOOSTERS[reward.value]['emoji']} `{BOOSTERS[reward.value]['name']}` booster") + \
            f"! You are **{5 - (streak % 5)}** votes away from the next reward!",
            "color": 0x3e4a78
        })
        embed.set_image(url="attachment://streak.png")

        if isinstance(reward, Booster):
            user.add_booster(reward.value)
        elif reward < 100:
            user.add_lootbox(reward)
        else:
            user.add_jenny(reward)

        try:
            await usr.send(embed=embed, file=file)
        except discord.HTTPException:
            pass

    async def top(self, _) -> List[dict]:
        """Returns a list of the top 50 users by the amount of jenny they have"""
        members = DB.teams.find({'id': {'$in': [x.id for x in self.client.users]} })
        top = sorted(members, key=lambda x: x['points'], reverse=True)[:50]
        res = []
        for t in top:
            u = self.client.get_user(t["id"])
            res.append({"name": u.name, "tag": u.discriminator, "avatar": str(u.avatar.url), "jenny": t["points"]})
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

        if (res := [c for c in checks if hasattr(c, "cooldown")]):
            check = res[0]
            cooldown = getattr(check, "cooldown", False)

        usage_slash = (cmd.qualified_name.replace(cmd.name, "") + cmd.usage) if not isinstance(cmd.cog, commands.GroupCog) else cmd.cog.__cog_group_name__ + " " + cmd.usage
        usage_message = (f"k!" + cmd.qualified_name.replace(cmd.name, "") + cmd.usage) if not isinstance(cmd.cog, commands.GroupCog) else f"k!" + cmd.usage

            
        return {
            "name": cmd.name,
            "slash_usage": usage_slash,
            "description": cmd.help or "No help found...",
            "aliases": cmd.aliases,
            "cooldown": cooldown or 0,
            "premium_guild": premium_guild,
            "premium_user": premium_user,
            "message_usage": usage_message
        }

    async def commands(self, _) -> dict:
        """Returns all commands with descriptions etc"""
        if not self.command_cache:
            raw = [v["commands"] for v in self.client.get_formatted_commands().values() if "commands" in v]
            self.command_cache = [item for sublist in raw for item in sublist]
        
        to_be_returned: Dict[str, Dict[str, Union[str, list]]] = {}

        for cmd in self.command_cache:
            formatted = self.format_command(cmd)

            if cmd.extras["category"].name in to_be_returned:
                to_be_returned[cmd.extras["category"].name]["commands"].append(formatted)
            else:
                to_be_returned[cmd.extras["category"].name] = {"commands": [formatted], "description": cmd.extras["category"].value["description"], "name": cmd.extras["category"].value["name"], "emoji": cmd.extras["category"].value["emoji"]}

        return to_be_returned
    
    async def stats(self, _) -> dict:
        """Gets stats about the bot"""
        return {"guilds": len(self.client.guilds), "shards": self.client.shard_count, "registered_users": DB.teams.count_documents({}), "last_restart": self.client.startup_datetime.timestamp()}

    async def save_user(self, data) -> None:
        """This functions purpose is not that much getting user data but saving a user in the database"""
        User(data["user"])

    async def get_discord_user(self, data) -> dict:
        """Getting additional info about a user with their id"""
        res =  self.client.get_user(data["user"])
        return {"name": res.name, "tag": res.discriminator, "avatar": str(res.avatar.url), "created_at": res.created_at.strftime('%Y-%m-%dT%H:%M:%SZ')}

    async def update_guild_cache(self, data) -> None:
        """Makes sure the local cache is up to date with the db"""
        guild = Guild(data.id)
        guild.prefix = data["prefix"]
        guild.commands = {v for _, v in data.commands.items()}

    async def vote(self, data) -> None:
        """Registers a vote from either topgg or dbl"""
        await self.handle_vote(data)
        # Test: curl -L -X POST 127.0.0.1:port/vote -H 'Authorization: uwu' -d '{"user": 606162661184372736}' -H "Content-Type: application/json"


Cog = IPCRoutes
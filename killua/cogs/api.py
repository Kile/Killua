import discord
from discord.ext import commands

from random import choices
from json import loads, dumps
from asyncio import create_task
from zmq import POLLIN, ROUTER
from zmq.asyncio import Context, Poller
from zmq.auth.asyncio import AsyncioAuthenticator

from killua.bot import BaseBot
from killua.static.enums import Booster
from killua.utils.classes import User, Guild
from killua.static.constants import DB, LOOTBOXES, IPC_TOKEN, VOTE_STREAK_REWARDS, BOOSTERS

from typing import List, Dict, Union

class IPCRoutes(commands.Cog):

    def __init__(self, client: BaseBot):
        self.client = client
        create_task(self.start())

    async def start(self):
        """Starts the zmq server asyncronously and handles incoming requests"""
        context = Context()

        auth = AsyncioAuthenticator(context)
        auth.start()
        auth.configure_plain(domain="*", passwords={"killua": IPC_TOKEN})
        auth.allow("127.0.0.1")

        socket = context.socket(ROUTER)
        socket.plain_server = True
        socket.bind("tcp://*:5555")

        poller = Poller()
        poller.register(socket, POLLIN)

        while True:
            socks = dict(await poller.poll())

            if socket in socks and socks[socket] == POLLIN:
                message = await socket.recv_multipart()
                identity, request = message
                decoded = loads(request.decode())
                res = await getattr(self, decoded["route"])(decoded["data"])
                if res:
                    await socket.send_multipart([identity, dumps(res).encode()])
                else:
                    await socket.send_multipart([identity, b'{"status":"ok"}'])

    def _get_reward(self, streak: int, weekend: bool = False) -> int:
        """A pretty simple algorithm that adjusts the reward for voting"""
        # First loop through all lootbox streak rwards from the back and find if any of them apply
        for key, value in list(VOTE_STREAK_REWARDS.items())[::-1]:
            if streak % key == 0:
                return value
        
        # Then follow the algorithm to find whether a "booster" reward applies
        if streak % 7 == 0 or str(streak)[-1] == "7":
            return Booster(choices(list(BOOSTERS.keys()), weights=[v["probability"] for v in BOOSTERS.values()])[0])

        # If no streak reward applies, just return the base reward
        return int((120 if weekend else 100) * float(f"1.{int(streak//5)}"))

    def _create_path(self, streak: int) -> str:
        """
        Creates a path illustrating where the user currently is with vote rewards and what the next rewards are as well as already claimed ones like
        --:boxemoji:--⚫️--:boxemoji:--
        This string has a hard limit of 11 and puts where the user currently is at the center
        """
        booster = "<:powerup:1091112046210330724>"
        # Edgecase where the user has no streak or a streak smaller than 5 which is when it would start in the middle
        if streak < 5:
            path_list = [LOOTBOXES[reward]['emoji'] if isinstance(reward := self._get_reward(i), int) and reward < 100 else (booster if isinstance(reward, Booster) else "-") for i in range(1, 11)]
            # Replace the character position where the user currently is with a black circle
            path_list[streak-1] = "⚫️"
            return " ".join(path_list)

        # Create the path
        before = [LOOTBOXES[reward]['emoji'] if isinstance(reward := self._get_reward(streak-i), int) and reward < 100 else (booster if isinstance(reward, Booster) else "-") for i in range(1, 6)]
        after = [LOOTBOXES[reward]['emoji'] if isinstance(reward := self._get_reward(streak+i), int) and reward < 100 else (booster if isinstance(reward, Booster) else "-") for i in range(1, 6)]
        path = before[::-1] + ["⚫️"] + after

        return " ".join(path)


    async def handle_vote(self, data: dict) -> None:
        user_id = data["user"] if "user" in data else data["id"]

        user = User(int(user_id))
        user.add_vote("topgg" if "isWeekend" in data else "discordbotlist")
        streak = user.voting_streak["topgg" if "isWeekend" in data else "discordbotlist"]["streak"]
        reward: Union[int, Booster] = self._get_reward(streak, data["isWeekend"] if hasattr(data, "isWeekend") else False)

        path = self._create_path(streak)
        embed = discord.Embed.from_dict({
            "title": "Thank you for voting!",
            "description": (f"Well done for keeping your voting **streak** 🔥 of {streak} for" if streak > 1 else "Thank you for voting on ") + f" {'top.gg' if 'isWeekend' in data else 'discordbotlist'}! As a reward I am happy to award with " + \
            ((f"{reward} Jenny" if reward >= 100 else f"a lootbox {LOOTBOXES[reward]['emoji']} {LOOTBOXES[reward]['name']}") if isinstance(reward, int) else f"the {BOOSTERS[reward.value]['emoji']} `{BOOSTERS[reward.value]['name']}` booster") + \
            f"! You are **{5 - (streak % 5)}** votes away from the next reward! \n\n{path}",
            "color": 0x3e4a78
        })
        if isinstance(reward, Booster):
            user.add_booster(reward)
        elif reward < 100:
            user.add_lootbox(reward)
        else:
            user.add_jenny(reward)
        
        usr = self.client.get_user(user_id) or await self.client.fetch_user(user_id)

        try:
            await usr.send(embed=embed)
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

    async def commands(self, _) -> dict:
        """Returns all commands with descriptions etc"""
        command_groups = [c.commands for c in self.client.tree.get_commands() if hasattr(c, "commands")]
        commands = [item for sublist in command_groups for item in sublist]
        
        to_be_returned: Dict[str, Dict[str, Union[str, list]]] = {}
        for cmd in commands:
            if not cmd.qualified_name.startswith("image"):
                msg_cmd = self.get_message_command(cmd.qualified_name) # Edge case and possibly a lib bug. See https://github.com/Rapptz/discord.py/issues/9243
            else:
                msg_cmd = None
                
            if not msg_cmd: # Ignores groups, jishaku and anything else that doesn't have extras
                continue
            
            cmd_extras = msg_cmd.extras
            checks = cmd.checks

            premium_guild, premium_user, cooldown = False, False, False

            if [c for c in checks if hasattr(c, "premium_guild_only")]:
                premium_guild = True

            if [c for c in checks if hasattr(c, "premium_user_only")]:
                premium_user = True

            if (res := [c for c in checks if hasattr(c, "cooldown")]):
                check = res[0]
                cooldown = getattr(check, "cooldown", False)
            
            data = {
                "name": cmd.name,
                "slash_usage": cmd.qualified_name,
                "description": cmd.description,
                "usage": msg_cmd.usage,
                "aliases": msg_cmd.aliases,
                "cooldown": cooldown,
                "premium_guild": premium_guild,
                "premium_user": premium_user,
                "message_usage": msg_cmd.qualified_name
            }
            if cmd_extras["category"].name in to_be_returned:
                to_be_returned[cmd_extras["category"].name]["commands"].append(data)
            else:
                to_be_returned[cmd_extras["category"].name] = {"commands": [data], "description": cmd_extras["category"].value["description"], "name": cmd_extras["category"].value["name"], "emoji": cmd_extras["category"].value["emoji"]}

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
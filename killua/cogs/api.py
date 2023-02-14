import discord
from discord.ext import commands

from asyncio import create_task
from zmq import REP, POLLIN, NOBLOCK
from zmq.asyncio import Context, Poller
from zmq.auth.asyncio import AsyncioAuthenticator

from killua.bot import BaseBot
from killua.utils.classes import User, Guild, LootBox
from killua.static.constants import DB, LOOTBOXES, IPC_TOKEN, VOTE_STREAK_REWARDS

from typing import List

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

        socket = context.socket(REP)
        socket.plain_server = True
        socket.bind("tcp://*:5555")

        poller = Poller()
        poller.register(socket, POLLIN)

        while True:
            socks = dict(await poller.poll())

            if socket in socks and socks[socket] == POLLIN:
                message = await socket.recv_json(NOBLOCK)
                res = await getattr(self, message["route"])(message["data"])
                if res:
                    socket.send_json(res)
                else:
                    socket.send_json({"status": "ok"})

    def _get_reward(self, streak: int, weekend: bool = False) -> int:
        """A pretty simple algorithm that adjusts the reward for voting"""
        # First loop through all lootbox streak rwards from the back and find if any of them apply
        for key, value in list(VOTE_STREAK_REWARDS.items())[::-1]:
            if streak % key == 0:
                return value

        # If no streak reward applies, just return the base reward
        return int((120 if weekend else 100) * float(f"1.{int(streak//5)}"))

    def _create_path(self, streak: int) -> str:
        """
        Creates a path illustrating where the user currently is with vote rewards and what the next rewards are as well as already claimed ones like
        --:boxemoji:--⚫️--:boxemoji:--
        This string has a hard limit of 11 and puts where the user currently is at the center
        """
        # Edgecase where the user has no streak or a streak smaller than 5 which is when it would start in the middle
        if streak < 5:
            path = " ".join([LOOTBOXES[self._get_reward(streak)]['emoji'] if self._get_reward(streak) < 100 else "-" for _ in range(1, 11)])
            # Replace the character position where the user currently is with a black circle
            return path[:streak*2] + "⚫️" + path[streak*2+1:]

        # Create the path
        before = [LOOTBOXES[self._get_reward(streak-i)]['emoji'] if self._get_reward(streak-i) < 100 else "-" for i in range(1, 6)]
        after = [LOOTBOXES[self._get_reward(streak+i)]['emoji'] if self._get_reward(streak+i) < 100 else "-" for i in range(1, 6)]
        path = before[::-1] + ["⚫️"] + after

        return " ".join(path)


    async def handle_vote(self, data: dict) -> None:
        user_id = data["user"] if "user" in data else data["id"]

        user = User(int(user_id))
        user.add_vote("topgg" if "isWeekend" in data else "discordbotlist")
        streak = user.voting_streak["topgg" if "isWeekend" in data else "discordbotlist"]["streak"]
        reward = self._get_reward(streak, data["isWeekend"] if hasattr(data, "isWeekend") else False)

        path = self._create_path(streak)
        embed = discord.Embed.from_dict({
            "title": "Thank you for voting!",
            "description": (f"Well done for keeping your voting **streak** 🔥 of {streak} for {'top.gg' if 'isWeekend' in data else 'discordbotlist'}! " if streak > 1 else "") + "As a reward I am happy to award with " + (f"{reward} Jenny" if reward >= 100 else f"a lootbox {LOOTBOXES[reward]['emoji']} {LOOTBOXES[reward]['name']}") + f"! You are **{5 - (streak % 5)}** votes away from the next reward! \n\n{path}",
            "color": 0x1400ff
        })
        if reward < 100:
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

    async def commands(self, _) -> dict:
        """Returns all commands with descriptions etc"""
        return self.client.get_formatted_commands()

    async def save_user(self, data) -> None:
        """This functions purpose is not that much getting user data but saving a user in the database"""
        User(data["user"])

    async def get_discord_user(self, data) -> dict:
        """Getting additional info about a user with their id"""
        res =  self.client.get_user(data["user"])
        return {"name": res.name, "tag": res.discriminator, "avatar": str(res.avatar.url), "created_at": res.created_at.strftime('%Y-%m-%dT%H:%M:%SZ')}

    async def get_guild_data(self, data) -> dict:
        """Getting some info about guild roles and channels for black and whitelisting"""
        res = self.client.get_guild(int(data["guild"]))
        return {"roles": [{"name": r.name, "id": str(r.id), "color": r.color.value} for r in res.roles], "channels": [{"name": c.name, "id": c.id} for c in res.channels if isinstance(c, discord.TextChannel)]}

    async def update_guild_cache(self, data) -> None:
        """Makes sure the local cache is up to date with the db"""
        guild = Guild(data.id)
        guild.prefix = data["prefix"]
        guild.commands = {v for _, v in data.commands.items()}

    async def vote(self, data) -> None:
        """Registers a vote from either topgg or dbl"""
        await self.handle_vote(data)


Cog = IPCRoutes
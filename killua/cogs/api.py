import discord
from discord.ext import ipc, commands

from killua.bot import BaseBot
from killua.utils.classes import User, Guild, LootBox
from killua.static.constants import DB, LOOTBOXES

from typing import List

class IPCRoutes(commands.Cog):

    def __init__(self, client: BaseBot):
        self.client = client

    def _get_reward(self, user:User, weekend:bool) -> int:
        """A pretty simple algorithm that adjusts the reward for voting"""
        if user.votes % 5 == 0:
            return LootBox.get_random_lootbox()
        if user.votes*2 > 100:
            reward = int((user.votes*2)/100)*(150 if weekend else 100)
        else:
            reward = 100
        return reward

    async def handle_vote(self, data: dict) -> None:
        user_id = data["user"] if "user" in data else data["id"]

        user = User(int(user_id))
        user.add_vote()
        reward = self._get_reward(user, data["isWeekend"] if hasattr(data, "isWeekend") else False)

        if reward < 100:
            user.add_lootbox(reward)
            text = f"Thank you for voting for Killua! This time you get a :sparkles: special :sparkles: reward: the lootbox {LOOTBOXES[reward]['emoji']} {LOOTBOXES[reward]['name']}. Open it with `k!open`"
        else:
            text = f"Thank you for voting for Killua! Here take {reward} Jenny as a sign of my gratitude. {5-user.votes%5} vote{'s' if 5-user.votes%5 > 1 else ''} away from a :sparkles: special :sparkles: reward"
            user.add_jenny(reward)
        
        usr = self.client.get_user(user_id) or await self.client.fetch_user(user_id)

        try:
            await usr.send(text)
        except discord.HTTPException:
            pass

    @ipc.server.route()
    async def top(self, _) -> List[dict]:
        """Returns a list of the top 50 users by the amount of jenny they have"""
        members = DB.teams.find({'id': {'$in': [x.id for x in self.client.users]} })
        top = sorted(members, key=lambda x: x['points'], reverse=True)[:50]
        res = []
        for t in top:
            u = self.client.get_user(t["id"])
            res.append({"name": u.name, "tag": u.discriminator, "avatar": str(u.avatar.url), "jenny": t["points"]})
        return res

    @ipc.server.route()
    async def commands(self, _) -> dict:
        """Returns all commands with descriptions etc"""
        return self.client.get_formatted_commands()

    @ipc.server.route()
    async def save_user(self, data) -> None:
        """This functions purpose is not that much getting user data but saving a user in the database"""
        User(data.user)

    @ipc.server.route()
    async def get_discord_user(self, data) -> dict:
        """Getting additional info about a user with their id"""
        res =  self.client.get_user(data.user)
        return {"name": res.name, "tag": res.discriminator, "avatar": str(res.avatar.url), "created_at": res.created_at.strftime('%Y-%m-%dT%H:%M:%SZ')}

    @ipc.server.route()
    async def get_guild_data(self, data) -> dict:
        """Getting some info about guild roles and channels for black and whitelisting"""
        res = self.client.get_guild(int(data.guild))
        return {"roles": [{"name": r.name, "id": str(r.id), "color": r.color.value} for r in res.roles], "channels": [{"name": c.name, "id": c.id} for c in res.channels if isinstance(c, discord.TextChannel)]}

    @ipc.server.route()
    async def update_guild_cache(self, data) -> None:
        """Makes sure the local cache is up to date with the db"""
        guild = Guild(data.id)
        guild.prefix = data.prefix
        guild.commands = {v for _, v in data.commands.items()}

    @ipc.server.route()
    async def vote(self, data) -> None:
        """Registers a vote from either topgg or dbl"""
        await self.handle_vote(data.data)


Cog = IPCRoutes

async def setup(client):
    await client.add_cog(IPCRoutes(client))
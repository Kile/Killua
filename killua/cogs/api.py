import discord
from discord.ext import ipc, commands
from killua.classes import User, Guild
from killua.constants import teams

from typing import List

class IPCRoutes(commands.Cog):

    def __init__(self, client):
        self.client = client

    @ipc.server.route()
    async def top(self, data) -> List[dict]:
        """Returns a list of the top 50 users by the amount of jenny they have"""
        members = teams.find({'id': {'$in': [x.id for x in self.client.users]} })
        top = sorted(members, key=lambda x: x['points'], reverse=True)[:50]
        res = []
        for t in top:
            u = self.client.get_user(t["id"])
            res.append({"name": u.name, "tag": u.discriminator, "avatar": str(u.avatar.url), "jenny": t["points"]})
        return res

    @ipc.server.route()
    async def commands(self, data) -> dict:
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
        guild.commands = {v for k, v in data.commands.items()}

Cog = IPCRoutes

def setup(client):
    client.add_cog(IPCRoutes(client))
import discord
from discord.ext import ipc, commands
from killua.classes import Category, User
from killua.constants import teams

from typing import List

class IPCRoutes(commands.Cog):

    def __init__(self, client):
        self.client = client

    def format_command(self, res:dict, cmd:commands.Command) -> dict:

        if cmd.name in ["jishaku", "help"] or cmd.hidden:
            return res

        res[cmd.extras["category"].value["name"]]["commands"].append({"name": cmd.name, "usage": cmd.usage, "help": cmd.help})
        
        return res

    @ipc.server.route()
    async def top(self, data) -> List[dict]:
        """Returns a list of the top 100 users by the amount of jenny they have"""
        members = teams.find({'id': {'$in': [x.id for x in self.client.users]} })
        top = sorted(members, key=lambda x: x['points'], reverse=True)[:100]
        res = []
        for t in top:
            u = self.client.get_user(t["id"])
            res.append({"name": u.name, "tag": u.discriminator, "avatar": str(u.avatar.url), "jenny": t["points"]})
        return res

    @ipc.server.route()
    async def commands(self, data) -> dict:
        """Returns all commands with descriptions etc"""
        res = {c.value["name"]:{"description":c.value["description"], "emoji": c.value["emoji"], "commands": [], "group_prefix": None} for c in Category}

        for cmd in self.client.commands:
            if isinstance(cmd, commands.Group) and cmd.name != "jishaku":
                res[cmd.extras["category"].value["name"]]["group_prefix"] = cmd.qualified_name
                for c in cmd.commands:
                    res = self.format_command(res, c)
            res = self.format_command(res, cmd)

        return res

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

Cog = IPCRoutes

def setup(client):
    client.add_cog(IPCRoutes(client))
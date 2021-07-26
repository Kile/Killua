from discord.ext import ipc, commands
from killua.classes import Category, User

class IPCRoutes(commands.Cog):

    def __init__(self, client):
        self.client = client

    @ipc.server.route()
    async def commands(self, args, **kwargs):
        """
        Returns all commands with descriptions in this format:
        
        {
        "category": {
            "description": "Some category description",
            "emoji": {
            "unicode": "emoji_in_unicode",
            "normal": ":how_discord_sends_emojis:"
            },
            "commands": [{
            "name": "command_name",
            "help": "some very helpful text about the command",
            "usage": "command_name <args>"
            },
            #...
            ],
        "other_category": {
        #...
        },
        #...
        } 

        """
        return {c.value["name"]:{"description":c.value["description"], "emoji": c.value["emoji"], "commands": [{"name": cmd.name, "usage": cmd.usage, "help": cmd.help} for cmd in self.client.commands if not (cmd.hidden or cmd.name == "jishaku" or cmd.name == "help") and cmd.extras["category"] == c]} for c in Category}

    @ipc.server.route()
    async def get_db_user(self, user:int, **kwargs):
        """This functions purpose is not that much getting user data but saving a user in the database"""
        return User(user)

    @ipc.server.route()
    async def get_discord_user(self, user:int, **kwargs):
        """Getting additional info about a user with their id"""
        return self.client.get_user(user)

Cog = IPCRoutes

def setup(client):
    client.add_cog(IPCRoutes(client))
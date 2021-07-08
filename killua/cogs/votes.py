import discord
from discord.ext import commands
import topgg
import json
from killua.classes import User
with open('config.json', 'r') as config_file:
    config = json.loads(config_file.read())

class Vote(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.dbl = config["dbl"]
        self.topgg_webhook = topgg.WebhookManager(self.client).dbl_webhook("/dblwebhook", self.dbl["password"])
        self.topgg_webhook.run(self.dbl["port"])

    def _get_reward(self, user:User, weekend:bool) -> int:
        """A pretty simple algorithm that adjusts the reward for voting"""
        if user.votes*2 > 100:
            reward = int((user.votes*2)/100)*(150 if weekend else 100)
        else:
            reward = 100
        return reward

    async def _get_user(self, u:int) -> discord.User:
        """Looking for a user in the cache and if not found making a dapi request for them"""
        r = self.client.get_user(u)
        if not r:
            r = await self.client.fetch_user(u)
        return r

    @commands.Cog.listener()
    async def on_dbl_vote(self, data):
        """An event that is called whenever someone votes for the bot on Top.gg."""
        user_id = data["user"]
        user = User(int(user_id))
        user.add_vote()
        reward = self._get_reward(user, data["isWeekend"])
        user.add_jenny(reward)
        
        usr = await self._get_user(user_id)
        try:
            await usr.send(f"Thank you for voting for Killua! Here take {reward} Jenny as a sign of my gratitude. Remember: the more you vote, the higher the reward gets!")
        except discord.HTTPException:
            pass

Cog = Vote

def setup(client):
    client.add_cog(Vote(client))
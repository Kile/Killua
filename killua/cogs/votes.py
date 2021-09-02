import discord
from discord.ext import commands
import topgg

from killua.classes import User
from killua.constants import DBL, LOOTBOXES
from killua.cogs.economy import LootBox

class Vote(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.dbl = DBL
        self.topgg_webhook = topgg.WebhookManager(self.client).dbl_webhook("/dblwebhook", self.dbl["password"])
        self.topgg_webhook.run(self.dbl["port"])

    def _get_reward(self, user:User, weekend:bool) -> int:
        """A pretty simple algorithm that adjusts the reward for voting"""
        if user.votes % 5 == 0:
            return LootBox.get_random_lootbox()
        if user.votes*2 > 100:
            reward = int((user.votes*2)/100)*(150 if weekend else 100)
        else:
            reward = 100
        return reward

    @commands.Cog.listener()
    async def on_dbl_vote(self, data):
        """An event that is called whenever someone votes for the bot on Top.gg."""
        user_id = data["user"]
        user = User(int(user_id))
        user.add_vote()
        reward = self._get_reward(user, data["isWeekend"])

        if reward < 100:
            user.add_lootbox(reward)
            text = f"Thank you for voting for Killua! This time you get a :sparkles: special :sparkles: reward: the lootbox {LOOTBOXES[reward]['emoji']} {LOOTBOXES[reward]['name']}. Open it with `k!open`"
        else:
            text = f"Thank you for voting for Killua! Here take {reward} Jenny as a sign of my gratitude. {user.votes%5} votes left from a :sparkles: special :sparkles: reward"
            user.add_jenny(reward)
        
        usr = self.client.get_user(user_id) or await self.client.fetch_user(user_id)
        try:
            await self.client.send_message(usr, content=text)
        except discord.HTTPException:
            pass

Cog = Vote


def setup(client):
    client.add_cog(Vote(client))
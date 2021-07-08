import discord
from discord.ext import commands
import topgg
import json
with open('config.json', 'r') as config_file:
    config = json.loads(config_file.read())

class Vote(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.dbl = config["dbl"]
        self.topgg_webhook = topgg.WebhookManager(self.client).dbl_webhook("/dblwebhook", self.dbl["password"])
        self.topgg_webhook.run(self.dbl["port"])

    @commands.Cog.listener()
    async def on_dbl_vote(data):
        """An event that is called whenever someone votes for the bot on Top.gg."""
        if data["type"] == "test":
            # this is roughly equivalent to
            # `return await on_dbl_test(data)` in this case
            return self.client.dispatch("dbl_test", data)

        print(f"Received a vote:\n{data}")

    @commands.Cog.listener()
    async def on_dbl_test(data):
        """An event that is called whenever someone tests the webhook system for your bot on Top.gg."""
        print(f"Received a test vote:\n{data}")


Cog = Vote

def setup(client):
    client.add_cog(Vote(client))
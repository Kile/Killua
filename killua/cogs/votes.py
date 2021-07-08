import discord
from discord.ext import commands
import dbl
import json
with open('config.json', 'r') as config_file:
    config = json.loads(config_file.read())

class Vote(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.dbl = config["dbl"]
        self.token = self.dbl["token"] # set this to your DBL token
        self.dblpy = dbl.DBLClient(self.client, self.token, webhook_path='/dblwebhook', webhook_auth=self.dbl["password"], webhook_port=self.dbl["port"])

    @commands.Cog.listener()
    async def on_ready(self):
        print(dbl.__version__)

    @commands.Cog.listener()
    async def on_dbl_vote(self, data):
        print('Someone voted')
        print(data)

Cog = Vote

def setup(client):
    client.add_cog(Vote(client))
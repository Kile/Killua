from __future__ import annotations

import discord
import asyncio
import topgg

from discord.ext import commands
from typing import TypedDict, Dict
from aiohttp import web
from aiohttp.web_urldispatcher import _WebHandler

from killua.utils.classes import User
from killua.static.constants import PORT, PASSWORD, LOOTBOXES
from killua.cogs.economy import LootBox


# These classes have been adapted from the topggpy library to work with dbl
class DBLdata:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

class _Webhook(TypedDict):
    route: str
    auth: str
    func: _WebHandler

class WebhookManager:

    __app: web.Application
    _webhooks: Dict[
        str,
        _Webhook,
    ]
    _webserver: web.TCPSite
    _is_closed: bool

    def __init__(self, bot: discord.Client):
        self.bot = bot
        self._webhooks = {}
        self.__app = web.Application()
        self._is_closed = False

    def dbl_webhook(self, route: str = "/dbl", auth_key: str = "") -> WebhookManager:
        self._webhooks["dbl"] = _Webhook(
            route=route or "/dbl",
            auth=auth_key or "",
            func=self._bot_vote_handler,
        )
        return self

    async def _bot_vote_handler(self, request: web.Request) -> web.Response:
        auth = request.headers.get("Authorization", "")
        if auth == self._webhooks["dbl"]["auth"]:
            data = await request.json()
            self.bot.dispatch("dbl_vote", DBLdata(**data))
            return web.Response(status=200, text="OK")
        return web.Response(status=401, text="Unauthorized")

    async def _run(self, port: int) -> None:
        for webhook in self._webhooks.values():
            self.__app.router.add_post(webhook["route"], webhook["func"])
        runner = web.AppRunner(self.__app)
        await runner.setup()
        self._webserver = web.TCPSite(runner, "0.0.0.0", port)
        await self._webserver.start()
        self._is_closed = False

    def run(self, port: int) -> asyncio.Task[None]:
        return self.bot.loop.create_task(self._run(port))

class Vote(commands.Cog):

    def __init__(self, client):
        self.client = client
        
        self.dbl_webhook = WebhookManager(self.client).dbl_webhook("/dblwebhook", PASSWORD)
        self.dbl_webhook.run(PORT+1)

        self.topgg_webhook = topgg.WebhookManager(self.client).dbl_webhook("/topggwebhook", PASSWORD)
        self.topgg_webhook.run(PORT)

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
        """An event that is called whenever someone votes for the bot on Top.gg or discordbotlist"""
        if isinstance(data, DBLdata):
            user_id = data.id
        else:
            user_id = data["user"]
        user = User(int(user_id))
        user.add_vote()
        reward = self._get_reward(user, data["isWeekend"] if hasattr(data, "isWeekend") else False)

        if reward < 100:
            user.add_lootbox(reward)
            text = f"Thank you for voting for Killua! This time you get a :sparkles: special :sparkles: reward: the lootbox {LOOTBOXES[reward]['emoji']} {LOOTBOXES[reward]['name']}. Open it with `k!open`"
        else:
            text = f"Thank you for voting for Killua! Here take {reward} Jenny as a sign of my gratitude. {5-user.votes%5} votes away from a :sparkles: special :sparkles: reward"
            user.add_jenny(reward)
        
        usr = self.client.get_user(user_id) or await self.client.fetch_user(user_id)
        try:
            await self.client.send_message(usr, content=text)
        except discord.HTTPException:
            pass

Cog = Vote


def setup(client):
    client.add_cog(Vote(client))
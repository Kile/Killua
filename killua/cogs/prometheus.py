from discord.ext import commands, tasks
from discord import Interaction, InteractionType

import logging
from pymongo.errors import ServerSelectionTimeoutError
from prometheus_client import start_http_server
from typing import cast, List, Dict
from psutil import virtual_memory, cpu_percent

from killua.metrics import *
from killua.static.constants import DB, API_ROUTES
from killua.utils.classes import User
from killua.bot import BaseBot as Bot

log = logging.getLogger("prometheus")


class PrometheusCog(commands.Cog):
    """
    A Cog to be added to a discord bot. The prometheus server will start once the bot is ready
    using the `on_ready` listener.
    """

    def __init__(self, client: Bot, port: int = 8000):
        """
        Parameters:
            bot: The Discord bot
            port: The port for the Prometheus server
        """
        self.client = client
        self.port = port
        self.initial = False
        self.api_previous: Dict[str, Dict[str, int]] = {}
        self.spam_previous: int = 0

        if self.client.run_in_docker:
            if not self.latency_loop.is_running():
                self.latency_loop.start()
            if not self.system_usage_loop.is_running():
                self.system_usage_loop.start()
            if not self.db_loop.is_running():
                self.db_loop.start()

    async def update_api_stats(self):
        url = (
            f"http://{'api' if self.client.run_in_docker else '0.0.0.0'}:{self.client.dev_port}"
            if self.client.is_dev
            else self.client.url
        )

        data = await self.client.session.get(
            url + "/diagnostics", headers={"Authorization": self.client.secret_api_key}
        )
        if data.status != 200:
            return

        json = await data.json()
        response_time = data.headers.get("X-Response-Time")

        API_RESPONSE_TIME.set(int(response_time.replace("ms", "")))
        if time := cast(dict, json["ipc"]).get("response_time"):  # Can be None
            IPC_RESPONSE_TIME.set(time)

        reqs = 0
        not_spam = 0
        for key, val in cast(dict, json["usage"]).items():
            reqs += len(val["requests"])
            if not key in API_ROUTES:
                continue
            not_spam += len(val["requests"])
            new_requests = len(val["requests"]) - self.api_previous.get(key, {}).get(
                "requests", 0
            )
            if key not in self.api_previous:
                self.api_previous[key] = {}
            self.api_previous[key]["requests"] = len(val["requests"])
            API_REQUESTS_COUNTER.labels(key, "requests").inc(amount=new_requests)
            new_success = val["successful_responses"] - self.api_previous.get(
                key, {}
            ).get("successful_responses", 0)
            self.api_previous[key]["successful_responses"] = val["successful_responses"]
            API_REQUESTS_COUNTER.labels(key, "success").inc(amount=new_success)

        new_spam = reqs - not_spam - self.spam_previous
        self.spam_previous = reqs - not_spam
        API_SPAM_REQUESTS.inc(new_spam)

    async def save_locales(self):
        locales = [
            doc["locale"]
            async for doc in DB.teams.find({"locale": {"$exists": True}})
            if "locale" in doc and doc["locale"]
        ]
        # turn into dict with locale as key and count as value
        locale_count = {locale: locales.count(locale) for locale in locales}
        for locale, count in locale_count.items():
            LOCALE.labels(
                cast(str, locale).split("-")[-1].upper()
                if "-" in locale
                else cast(str, locale).upper()
            ).set(count)

    async def init_gauges(self):
        log.debug("Initializing gauges")
        num_of_commands = len(self.get_all_commands())
        COMMANDS_GAUGE.set(num_of_commands)

        # The main point of this is to initialise the Counter
        # with the correct labels, so that the labels are present
        # in the metrics even if no one has voted there yet.
        VOTES.labels("topgg")
        VOTES.labels("discordbotlist")

        registered_users = await DB.teams.count_documents({})
        REGISTERED_USER_GAUGE.set(registered_users)

        dau = (await DB.const.find_one({"_id": "growth"}))["growth"][-1]["daily_users"]
        DAILY_ACTIVE_USERS.set(dau)

        await self.save_locales()

        # Update command stats
        usage_data: Dict[str, int] = (await DB.const.find_one({"_id": "usage"}))[
            "command_usage"
        ]
        cmds = self.client.get_raw_formatted_commands()
        for cmd in cmds:
            if (
                not cmd.extras
                or not "id" in cmd.extras
                or not str(cmd.extras["id"]) in usage_data
            ):
                continue
            COMMAND_USAGE.labels(
                self.client._get_group(cmd), cmd.name, cmd.extras["id"]
            ).set(usage_data[str(cmd.extras["id"])])

        await self.update_api_stats()

    def get_all_commands(self) -> List[commands.Command]:
        return self.client.get_raw_formatted_commands()

    def start_prometheus(self):
        log.debug(f"Starting Prometheus Server on port {self.port}")
        start_http_server(self.port)
        self.started = True

    @tasks.loop(seconds=5)
    async def latency_loop(self):
        for shard, latency in self.client.latencies:
            LATENCY_GAUGE.labels(shard).set(latency)

    @tasks.loop(minutes=10)
    async def db_loop(self):
        try:
            registered_users = await DB.teams.count_documents({})
            REGISTERED_USER_GAUGE.set(registered_users)

            todo_list_amount = await DB.todo.count_documents({})
            TODO_LISTS.set(todo_list_amount)
            todos = sum([len(todo["todos"]) async for todo in DB.todo.find({})])
            TODOS.set(todos)

            tags = await DB.guilds.find({"tags": {"$exists": True}}).to_list(
                length=None
            )
            tag_amount = sum([len(v["tags"]) for v in tags])
            TAGS.set(tag_amount)
            await self.save_locales()
            await self.update_api_stats()
        except ServerSelectionTimeoutError:
            logging.warn("Failed to save mongodb stats to DB due to connection error")
             # Skip this iteration

    @tasks.loop(seconds=5)
    async def system_usage_loop(self):
        RAM_USAGE_GAUGE.set(virtual_memory().percent)
        CPU_USAGE_GAUGE.set(cpu_percent())
        MEMORY_USAGE_GAUGE.set(
            virtual_memory().available * 100 / virtual_memory().total
        )

    @commands.Cog.listener()
    async def on_ready(self):
        # This is very intentionally not cog_load.
        # I hope future me remembers why. For whatever reason,
        # commands which are NOT part of a GroupCog are only
        # loaded AFTER the Bot is ready. I am not sure why, they
        # could already be added since it doesn't need any info
        # from Discord, but it is what it is and this is the way
        # to make sure all commands are returned by get_all_raw_commands.
        #
        # Given how significant it is especially for the command stats
        # to take into account historical data, I am glad I spotted this.
        if self.initial:
            return
        self.initial = True
        if self.client.run_in_docker:
            GUILD_GAUGE.set(len(self.client.guilds))
            await self.init_gauges()

            # Set connection back up (since we in on_ready)
            CONNECTION_GAUGE.labels(None).set(1)

            self.start_prometheus()
        else:
            log.info("Running outside of Docker, not starting Prometheus server")

    @commands.Cog.listener()
    async def on_command(self, ctx: commands.Context):
        ON_COMMAND_COUNTER.inc()

        if not ctx.command.extras.get("id"):
            return
        COMMAND_USAGE.labels(
            self.client._get_group(ctx.command),
            ctx.command.name,
            str(ctx.command.extras["id"]),
        ).inc()

    @commands.Cog.listener()
    async def on_interaction(self, interaction: Interaction):
        old = await (await User.new(interaction.user.id)).log_locale(
            interaction.locale[-1]
        )
        if old:
            LOCALE.labels(old).dec()


        if not interaction.type in [InteractionType.application_command]:
            # don't save just any interaction
            return

        ON_INTERACTION_COUNTER.labels(
            not interaction.is_guild_integration()
        ).inc()

    @commands.Cog.listener()
    async def on_connect(self):
        CONNECTION_GAUGE.labels(None).set(1)

    @commands.Cog.listener()
    async def on_resumed(self):
        CONNECTION_GAUGE.labels(None).set(1)

    @commands.Cog.listener()
    async def on_disconnect(self):
        CONNECTION_GAUGE.labels(None).set(0)

    @commands.Cog.listener()
    async def on_shard_ready(self, shard_id):
        CONNECTION_GAUGE.labels(shard_id).set(1)

    @commands.Cog.listener()
    async def on_shard_connect(self, shard_id):
        CONNECTION_GAUGE.labels(shard_id).set(1)

    @commands.Cog.listener()
    async def on_shard_resumed(self, shard_id):
        CONNECTION_GAUGE.labels(shard_id).set(1)

    @commands.Cog.listener()
    async def on_shard_disconnect(self, shard_id):
        CONNECTION_GAUGE.labels(shard_id).set(0)

    @commands.Cog.listener()
    async def on_guild_join(self, _):
        GUILD_GAUGE.set(len(self.client.guilds))

    @commands.Cog.listener()
    async def on_guild_remove(self, _):
        GUILD_GAUGE.set(len(self.client.guilds))


Cog = PrometheusCog

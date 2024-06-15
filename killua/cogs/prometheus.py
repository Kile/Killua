import logging
from prometheus_client import start_http_server
from typing import cast, List, Optional
from psutil import virtual_memory, cpu_percent
from discord.ext import commands, tasks
from discord import Interaction, InteractionType

from killua.utils.checks import CommandUsageCache
from killua.metrics import *
from killua.static.constants import DB, API_ROUTES
from killua.bot import BaseBot as Bot

log = logging.getLogger('prometheus')

class PrometheusCog(commands.Cog):
    """
    A Cog to be added to a discord bot. The prometheus server will start once the bot is ready
    using the `on_ready` listener.
    """

    def __init__(self, client: Bot, port: int=8000):
        """
        Parameters:
            bot: The Discord bot
            port: The port for the Prometheus server
        """
        self.client = client
        self.port = port

        if self.client.run_in_docker:
            self.latency_loop.start()
            self.system_usage_loop.start()
            self.db_loop.start()

    async def update_api_stats(self):
        url = f"http://{'api' if self.client.run_in_docker else '0.0.0.0'}:{self.client.dev_port}" if self.client.is_dev else self.client.url

        data = await self.client.session.get(url + "/diagnostics", headers={"Authorization": self.client.secret_api_key})
        if data.status != 200:
            return
        
        json = await data.json()
        response_time = data.headers.get("X-Response-Time")

        API_RESPONSE_TIME.set(int(response_time.replace("ms", "")))
        if (time := cast(dict, json["ipc"]).get("response_time")): # Can be None
            IPC_RESPONSE_TIME.set(time)

        reqs = 0
        not_spam = 0
        for key, val in cast(dict, json["usage"]).items():
            reqs += len(val["requests"])
            if not key in API_ROUTES:
                continue
            not_spam += len(val["requests"])
            API_REQUESTS_COUNTER.labels(key, "requests").set(len(val["requests"]))
            API_REQUESTS_COUNTER.labels(key, "success").set(val["successful_responses"])

        API_SPAM_REQUESTS.set(reqs - not_spam)


    async def init_gauges(self):    
        log.debug('Initializing gauges')
        num_of_commands = len(self.get_all_commands())
        COMMANDS_GAUGE.set(num_of_commands)
        
        registered_users = DB.teams.count_documents({})
        REGISTERED_USER_GAUGE.set(registered_users)

        dau = DB.const.find_one({"_id": "growth"})["growth"][-1]["daily_users"]
        DAILY_ACTIVE_USERS.set(dau)

        # Update command stats
        usage_data: dict = DB.const.find_one({"_id": "usage"})["command_usage"]

        commands = self.client.get_raw_formatted_commands()
        for cmd in commands:
            if not cmd.extras or not "id" in cmd.extras or not str(cmd.extras["id"]) in usage_data:
                continue

            COMMAND_USAGE.labels(
                self.client._get_group(cmd),
                cmd.name,
                str(cmd.extras["id"])
            ).set(
                usage_data[str(cmd.extras["id"])]
            )
        
        await self.update_api_stats()

    def get_all_commands(self) -> List[commands.Command]:
        return self.client.get_raw_formatted_commands()

    def start_prometheus(self):
        log.debug(f'Starting Prometheus Server on port {self.port}')
        start_http_server(self.port)
        self.started = True

    @tasks.loop(seconds=5)
    async def latency_loop(self):
        for shard, latency in self.client.latencies:
            LATENCY_GAUGE.labels(shard).set(latency)

    @tasks.loop(minutes=10)
    async def db_loop(self):
        registered_users = DB.teams.count_documents({})
        REGISTERED_USER_GAUGE.set(registered_users)
        await self.update_api_stats()

            
    @tasks.loop(seconds=5)
    async def system_usage_loop(self):
        RAM_USAGE_GAUGE.set(virtual_memory().percent)
        CPU_USAGE_GAUGE.set(cpu_percent())
        MEMORY_USAGE_GAUGE.set(
            virtual_memory().available * 100 / virtual_memory().total
        )

    async def cog_load(self):
        if self.client.run_in_docker:
            # some gauges needs to be initialized after each reconect
            # (value could changed during an outtage)
            await self.init_gauges()

            # Set connection back up (since we in on_ready)
            CONNECTION_GAUGE.labels(None).set(1)

            self.start_prometheus()
        else:
            log.info("Running outside of Docker, not starting Prometheus server")

    @commands.Cog.listener()
    async def on_command(self, ctx: commands.Context):
        shard_id = ctx.guild.shard_id if ctx.guild else None
        ON_COMMAND_COUNTER.labels(shard_id, ctx.command.name).inc()

        if not ctx.command.extras.get("id"): return
        COMMAND_USAGE.labels(
            self.client._get_group(ctx.command),
            ctx.command.name,
            str(ctx.command.extras["id"])
        ).inc()

    @commands.Cog.listener()
    async def on_interaction(self, interaction: Interaction):
        shard_id = interaction.guild.shard_id if interaction.guild else None

        # command name can be None if comming from a view (like a button click) or a modal
        command_name = None
        if interaction.type == InteractionType.application_command and interaction.command:
            command_name = interaction.command.name

        ON_INTERACTION_COUNTER.labels(shard_id, interaction.type.name, command_name).inc()

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
    async def on_ready(self):
        # Seperate from setup hook due to the count being 0 before ready
        GUILD_GAUGE.set(len(self.client.guilds))

    @commands.Cog.listener()
    async def on_guild_join(self, _):
        GUILD_GAUGE.set(len(self.client.guilds))

    @commands.Cog.listener()
    async def on_guild_remove(self, _):
        GUILD_GAUGE.set(len(self.client.guilds))
        
Cog = PrometheusCog
from threading import Thread, Event
from queue import Queue
from typing import Tuple, Callable, Any
import traceback
import time

import logging
from prometheus_client import start_wsgi_server
from typing import cast, List, Dict
from psutil import virtual_memory, cpu_percent
from discord.ext import commands, tasks
from discord import Interaction, InteractionType

from killua.metrics import *
from killua.static.constants import DB, API_ROUTES
from killua.bot import BaseBot as Bot

log = logging.getLogger("prometheus")


def start_wsgi_server_with_error_handling(
    *args, **kwargs
) -> Tuple[Any, Thread, Thread, Queue, Event]:
    error_queue = Queue()
    stop_event = Event()

    server_obj, server_thread = start_wsgi_server(*args, **kwargs)

    def target_with_exception_handling(original_thread: Thread, error_queue: Queue):
        try:
            original_thread.join()
        except Exception as e:
            logging.info("Caught prometheus exception")
            error_queue.put((e, traceback.format_exc()))

    def error_handling_function(stop_event: Event, error_queue: Queue):
        while not stop_event.is_set():
            if not error_queue.empty():
                # Non-blocking get with timeout
                exception, traceback_str = error_queue.get(timeout=1)
                logging.info(f"Caught (custom) exception: {exception}")
                logging.info(traceback_str)

    # Create and start the error handling thread
    error_thread = Thread(
        target=error_handling_function, args=(stop_event, error_queue)
    )
    error_thread.start()

    # Wrap the original server thread to capture its exceptions
    exception_thread = Thread(
        target=target_with_exception_handling, args=(server_thread, error_queue)
    )
    exception_thread.start()

    return (
        server_obj,
        server_thread,
        error_thread,
        exception_thread,
        error_queue,
        stop_event,
    )


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
            API_REQUESTS_COUNTER.labels(key, "requests").set(len(val["requests"]))
            API_REQUESTS_COUNTER.labels(key, "success").set(val["successful_responses"])

        API_SPAM_REQUESTS.set(reqs - not_spam)

    async def init_gauges(self):
        log.debug("Initializing gauges")
        num_of_commands = len(self.get_all_commands())
        COMMANDS_GAUGE.set(num_of_commands)

        registered_users = DB.teams.count_documents({})
        REGISTERED_USER_GAUGE.set(registered_users)

        dau = DB.const.find_one({"_id": "growth"})["growth"][-1]["daily_users"]
        DAILY_ACTIVE_USERS.set(dau)

        # Update command stats
        usage_data: Dict[str, int] = DB.const.find_one({"_id": "usage"})[
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
        (
            self.server_obj,
            self.server_thread,
            self.error_thread,
            self.exception_thread,
            self.error_queue,
            self.stop_event,
        ) = start_wsgi_server_with_error_handling(self.port)
        self.started = True

    async def on_shutdown(self):
        log.debug("Shutting down Prometheus server")
        cast(Event, self.stop_event).set()
        self.server_thread.join()
        self.error_thread.join()
        self.exception_thread.join()

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
        shard_id = ctx.guild.shard_id if ctx.guild else None
        ON_COMMAND_COUNTER.labels(shard_id, ctx.command.name).inc()

        if not ctx.command.extras.get("id"):
            return
        COMMAND_USAGE.labels(
            self.client._get_group(ctx.command),
            ctx.command.name,
            str(ctx.command.extras["id"]),
        ).inc()

    @commands.Cog.listener()
    async def on_interaction(self, interaction: Interaction):
        shard_id = interaction.guild.shard_id if interaction.guild else None

        # command name can be None if comming from a view (like a button click) or a modal
        command_name = None
        if (
            interaction.type == InteractionType.application_command
            and interaction.command
        ):
            command_name = interaction.command.name

        ON_INTERACTION_COUNTER.labels(
            shard_id, interaction.type.name, command_name
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

from discord.ext import commands
import discord

import math
from typing import List, Tuple, Union, Literal, cast, Dict
from io import BytesIO
from datetime import datetime
from matplotlib import pyplot as plt
import numpy as np

from killua.bot import BaseBot
from killua.utils.checks import check
from killua.utils.paginator import Paginator
from killua.utils.classes import User, Guild  # lgtm [py/unused-import]
from killua.utils.interactions import View, Button, Modal
from killua.static.enums import Category  # , StatsOptions
from killua.static.cards import Card  # lgtm [py/unused-import]
from killua.static.constants import DB, UPDATE_CHANNEL, GUILD_OBJECT, INFO, API_ROUTES
from killua.cogs.api import NewsMessage


class UsagePaginator(Paginator):
    """A normal paginator with a button that returns to the original help command"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.view.add_item(
            Button(label="Back", style=discord.ButtonStyle.red, custom_id="1")
        )

    async def start(self):
        view = await self._start()

        if view.ignore or view.timed_out:
            return

        await self.view.message.delete()
        await self.ctx.command.__call__(self.ctx, "usage")


class Dev(commands.GroupCog, group_name="dev"):

    def __init__(self, client: BaseBot):
        self.client = client
        self.version_cache = []

    async def version_autocomplete(
        self,
        _: discord.Interaction,
        current: str,
    ) -> List[discord.app_commands.Choice[str]]:

        if not self.version_cache:
            self.version_cache = [
                x["version"]
                async for x in DB.news.find({"type": "update", "published": True})
            ]

        return [
            discord.app_commands.Choice(name=v, value=v)
            for v in self.version_cache
            if current.lower() in v.lower()
        ]

    def _create_piechart(
        self,
        data: List[list],
    ) -> discord.File:
        """Creates a piechart with the given data"""
        labels = [x[0] for x in data]
        values = [x[1] for x in data]
        buffer = BytesIO()
        plt.pie(
            values,
            labels=labels,
            autopct="%1.1f%%",
            shadow=True,
            textprops={"color": "w"},
        )
        plt.axis("equal")
        plt.tight_layout()
        plt.savefig(buffer, format="png", transparent=True)
        buffer.seek(0)
        plt.close()
        file = discord.File(buffer, filename="piechart.png")
        return file

    def _create_graph(
        self, dates: List[datetime], y_points: List[int], label: str
    ) -> BytesIO:
        """Creates a graph with y over time supplied in the dates list"""
        plt.style.use("seaborn-v0_8")  # After testing this is the best theme
        # Plotting the main graph
        plt.plot(dates, y_points, color="blue")
        plt.xlabel("Time")
        plt.ylabel(label)

        # Plot the trend using a linear regression
        x = np.array([x.timestamp() for x in dates])
        y = np.array(y_points)
        m, b = np.polyfit(x, y, 1)
        plt.plot(dates, m * x + b, linestyle=":", color="grey")

        plt.tight_layout()  # Making the actual graph a bit bigger
        buf = BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        plt.close()

        return buf

    def _calc_predictions(self, values: List[int]) -> dict:
        """Calculates various predictions for the given values"""

        # Calculates the average change between one value compared to the next one in the list
        change = [values[i + 1] - values[i] for i in range(len(values) - 1)]
        avg_change = round(sum(change) / len(values), 2)
        # Calculates the standard deviation of the avergae change
        std_change = round(
            math.sqrt(sum([(x - avg_change) ** 2 for x in change]) / len(values)), 2
        )

        recent_avg = round(sum(values[-10:]) / 10, 2)

        return {
            "recent_avg": recent_avg,
            "min": min(values),
            "max": max(values),
            "avg_change": avg_change,
            "std_change": std_change,
            "median": sorted(values)[len(values) // 2],
            "mode": max(set(values), key=values.count),
        }

    def _get_stats_embed(
        self, data: List[dict], embed: discord.Embed, type: str
    ) -> Tuple[discord.Embed, discord.File]:
        """Creates an embed with the stats of the given type"""
        dates = [x["date"] for x in data if type in x]
        type_list = [x[type] for x in data if type in x]

        embed.title = (
            f"Statistics about {self.client.user.name}'s "
            + type.replace("_", " ").title()
        )

        if not dates:
            embed.description = "No data available just yet"
            return embed
        elif type == "users":
            embed.description = "⚠️ This only displays the amount of cached users, it is rarely representative of the actual amount of users"
        else:
            embed.description = None

        buffer = self._create_graph(dates, type_list, type.replace("_", " ").title())
        file = discord.File(buffer, filename=f"{type}.png")
        add_data = self._calc_predictions(type_list)

        embed.set_image(url=f"attachment://{type}.png")
        type = type.replace("_", " ")
        embed.add_field(
            name=f"Maximum {type} reached", value=add_data["max"]
        )  # This is only really relevant for guilds and users as registered users cannot decrease
        embed.add_field(
            name=f"Average {type} last 10 days", value=add_data["recent_avg"]
        )
        embed.add_field(
            name=f"Average {type} gained per day", value=add_data["avg_change"]
        )
        embed.add_field(
            name=f"\U000003c3 of the average daily {type} gain",
            value=add_data["std_change"],
        )
        return embed, file

    async def all_top(self, ctx: commands.Context, top: List[tuple]) -> None:
        """Shows a list of all top commands"""

        def make_embed(page, embed: discord.Embed, pages):
            embed.title = "Top command usage"

            if len(pages) - page * 10 + 10 > 10:
                top = pages[page * 10 - 10 : -(len(pages) - page * 10)]
            elif len(pages) - page * 10 + 10 <= 10:
                top = pages[-(len(pages) - page * 10 + 10) :]

            embed.description = (
                "```\n"
                + "\n".join(
                    [
                        "#" + str(n + 1) + " /" + k + " with " + str(v) + " uses"
                        for n, (k, v) in enumerate(top, page * 10 - 10)
                    ]
                )
                + "\n```"
            )
            return embed

        await UsagePaginator(
            ctx, top, func=make_embed, max_pages=math.ceil(len(top) / 10)
        ).start()

    async def group_top(
        self, ctx: commands.Context, top: List[tuple], interaction: discord.Interaction
    ) -> None:
        """Displays a pie chart of the top used commands in a group"""
        # A list of all valid groups as strings
        possible_groups = [
            g.name for g in self.client.tree.get_commands() if hasattr(g, "commands")
        ]  # Groups have an attribute of "commands" which includes all subcommands
        group = await self.client.get_text_response(
            ctx,
            "Please enter a command group",
            interaction=interaction,
            style=discord.TextStyle.short,
            placeholder=(", ".join(possible_groups))[:97] + "...",
        )
        if not group:
            return

        if group.lower() not in possible_groups:
            return await ctx.send("That is not a valid group", ephemeral=True)
        else:
            top = [
                (x[0].split(" ")[1], x[1])
                for x in top
                if x[0].startswith(group.lower()) and len(x[0].split(" ")) > 1
            ]
            rest = 0
            for x in top[9:]:
                rest += x[1]

            if len(top) > 9:
                real_top = [*top[:9], ("other", rest)]
            else:
                real_top = top[:9]

            file = self._create_piechart(real_top)
            embed = discord.Embed(
                title=f"Top 10 used commands of group {group}", color=0x3E4A78
            )
            embed.set_image(url="attachment://piechart.png")

            view = View(ctx.author.id)
            view.add_item(
                Button(label="Back", style=discord.ButtonStyle.red, custom_id="back")
            )

            msg = await ctx.send(embed=embed, file=file, view=view)
            await view.wait()

            if view.timed_out:
                await view.disable()

            if view.value and view.value == "back":
                await msg.delete()
                await self.initial_top(ctx)

    def get_command_extras(self, cmd: str):
        c = self.client.get_command(cmd)
        if not c:
            c = self.client.get_command(cmd.split(" ")[-1])
        return c.extras

    async def initial_top(self, ctx: commands.Context) -> None:
        # Convert the ids to actually command names
        usage_data: Dict[str, int] = (await DB.const.find_one({"_id": "usage"}))[
            "command_usage"
        ]
        usage_data_formatted = {}

        cmds = self.client.get_raw_formatted_commands()
        for cmd in cmds:
            if (
                not cmd.extras
                or not "id" in cmd.extras
                or not str(cmd.extras["id"]) in usage_data
            ):
                continue
            usage_data_formatted[
                (
                    cmd.qualified_name
                    if not isinstance(cmd.cog, commands.GroupCog)
                    else cmd.cog.__cog_group_name__ + " " + cmd.name
                )
            ] = usage_data[str(cmd.extras["id"])]

        top = sorted(usage_data_formatted.items(), key=lambda x: x[1], reverse=True)
        rest = 0
        for x in top[9:]:
            rest += x[1]

        # creates a piechart in an embed with the top 10 commands using _create_piechart
        file = self._create_piechart([*top[:9], ("other", rest)])
        embed = discord.Embed(title="Top 10 used commands", color=0x3E4A78)
        embed.set_image(url="attachment://piechart.png")

        view = View(ctx.author.id)
        view.add_item(
            Button(label="See all", style=discord.ButtonStyle.primary, custom_id="all")
        )
        view.add_item(
            Button(
                label="See for group",
                style=discord.ButtonStyle.primary,
                custom_id="group",
            )
        )

        msg = await ctx.send(embed=embed, file=file, view=view)

        await view.wait()

        if view.timed_out:
            await view.disable()
        else:
            await msg.delete()
            if view.value == "all":
                await self.all_top(ctx, top)
            elif view.value == "group":
                await self.group_top(ctx, top, view.interaction)

    async def api_stats(self, ctx: commands.Context):
        """Gets statistics about the Killua API"""
        data = await self.client.session.get(
            self.client.api_url(to_fetch=True) + "/diagnostics",
            headers={"Authorization": self.client.secret_api_key},
        )
        if data.status != 200:
            return await ctx.send("An error occurred while fetching the data")

        json = await data.json()
        response_time = data.headers.get("X-Response-Time")

        embed = discord.Embed(
            title="Killua API statistics",
            description="IPC connection: "
            + ("✅ Ok" if json["ipc"]["success"] else "❌ Down")
            + "\n"
            + (
                ("IPC latency: " + str(round(json["ipc"]["response_time"], 2)) + "ms\n")
                if json["ipc"]["success"]
                else ""
            )
            + "API latency: "
            + response_time,
            color=0x3E4A78,
        )

        # Generate piechart
        spam = 0
        data = []
        for key, val in cast(dict, json["usage"]).items():
            if key not in API_ROUTES:
                spam += val["request_count"]
                continue
            reqs: int = cast(dict, val).get("request_count")
            successful_res: int = cast(dict, val).get("successful_responses")

            embed.add_field(
                name=key,
                value="Requests: "
                + str(reqs)
                + "\n"
                + "Successful responses: "
                + str(successful_res)
                + f" ({round(successful_res/reqs*100)}%)"
                + "\n",
            )
            data.append((key, reqs))

        embed.description += f"\nSpam requests: {spam}"
        piechart = self._create_piechart(data)
        embed.set_image(url="attachment://piechart.png")
        await ctx.send(embed=embed, file=piechart)

    # Eval command, unnecessary with the jsk extension but useful for database stuff
    @commands.is_owner()
    @commands.command(
        aliases=["exec"],
        extras={"category": Category.OTHER, "id": 23},
        usage="eval <code>",
        hidden=True,
        with_app_command=False,
    )
    @discord.app_commands.describe(
        code="The code to evaluate"
    )  # Since this is not an app command this won"t show up but is still added for consistency
    async def eval(self, ctx: commands.Context, *, code: str):
        """Standard eval command, owner restricted"""
        try:
            await ctx.send(f"```py\n{eval(code)}```")
        except Exception as e:
            await ctx.send(str(e))

    @commands.is_owner()
    @commands.command(
        extras={"category": Category.OTHER, "id": 24},
        usage="say <text>",
        hidden=True,
        with_app_command=False,
    )
    @discord.app_commands.describe(
        content="What to say"
    )  # Same thing as for the eval command
    async def say(self, ctx: commands.Context, *, content: str):
        """Lets Killua say what is specified with this command. Possible abuse leads to this being restricted"""

        await ctx.message.delete()
        await ctx.send(content, reference=ctx.message.reference)

    @check()
    @commands.hybrid_command(
        extras={"category": Category.OTHER, "id": 26},
        usage="update <version(optional)>",
    )
    @discord.app_commands.autocomplete(version=version_autocomplete)
    @discord.app_commands.describe(version="The version to get information about")
    async def update(self, ctx: commands.Context, version: str = None):
        """Allows you to view current and past updates"""
        if version is None:
            data = await DB.news.find_one({"type": "update", "published": True}, sort=[("timestamp", -1)])
            if not data:
                return await ctx.send("No updates found", ephemeral=True)
        else:
            data = await DB.news.find_one(
                {"type": "update", "version": version, "published": True}
            )
            if not data:
                return await ctx.send("That version does not exist", ephemeral=True)
            
        news = NewsMessage.from_data(self.client, data)
        view, files = await news._make_view(include_ping=False)
        await ctx.send(view=view, files=files, allowed_mentions=discord.AllowedMentions.none(), ephemeral=True)

    @commands.is_owner()
    @commands.hybrid_command(
        extras={"category": Category.OTHER, "id": 27},
        usage="blacklist <user_id>",
        hidden=True,
    )
    @discord.app_commands.guilds(GUILD_OBJECT)
    @discord.app_commands.describe(
        user="The user to blacklist", reason="The reason for the blacklist"
    )
    async def blacklist(self, ctx: commands.Context, user: str, *, reason=None):
        """Blacklisting bad people like Hisoka. Owner restricted"""
        discord_user: Union[discord.User, None] = await self.client.find_user(ctx, user)
        if not discord_user:
            return await ctx.send("Invalid user!", ephermal=True)
        # Inserting the bad person into my database
        await DB.const.update_one(
            {"_id": "blacklist"},
            {
                "$push": {
                    "blacklist": {
                        "id": discord_user.id,
                        "reason": reason or "No reason provided",
                        "date": datetime.now(),
                    }
                }
            },
        )
        await ctx.send(f"Blacklisted user `{user}` for reason: {reason}", ephermal=True)

    @commands.is_owner()
    @commands.hybrid_command(
        extras={"category": Category.OTHER, "id": 28},
        usage="whitelist <user_id>",
        hidden=True,
    )
    @discord.app_commands.guilds(GUILD_OBJECT)
    @discord.app_commands.describe(user="The user to whitelist")
    async def whitelist(self, ctx: commands.Context, user: str):
        """Whitelists a user. Owner restricted"""
        user: Union[discord.User, None] = await self.client.find_user(user)
        if not user:
            return await ctx.send("Invalid user!", ephermal=True)

        to_pull = [
            d
            for d in (await DB.const.find_one({"_id": "blacklist"}))["blacklist"]
            if d["id"] == user.id
        ]

        if not to_pull:
            return await ctx.send("User is not blacklisted!", ephermal=True)

        await DB.const.update_one(
            {"_id": "blacklist"}, {"$pull": {"blacklist": to_pull[0]}}
        )
        await ctx.send(f"Successfully whitelisted `{user}`")

    @commands.is_owner()
    @commands.hybrid_command(
        aliases=["st", "pr", "status"],
        extras={"category": Category.OTHER, "id": 119},
        usage="pr <text>",
        hidden=True,
    )  # I messed up here with the numbers and did not want to have to increment all of them after this one
    @discord.app_commands.guilds(GUILD_OBJECT)
    @discord.app_commands.describe(
        text="The text displayed as the status",
        activity="The activity Killua is doing",
        presence="Killua's presence",
    )
    async def presence(
        self,
        ctx: commands.Context,
        text: str,
        activity: Literal["playing", "watching", "listening", "competing"] = None,
        presence: Literal["dnd", "idle", "online"] = None,
    ):
        """Changes the presence of Killua. Owner restricted"""

        if text == "-rm":
            await DB.const.update_many(
                {"_id": "presence"},
                {"$set": {"text": None, "activity": None, "presence": None}},
            )
            await ctx.send("Done! reset Killua's presence", ephemeral=True)
            return await self.client.update_presence()

        await DB.const.update_many(
            {"_id": "presence"},
            {
                "$set": {
                    "text": text,
                    "presence": presence if presence else None,
                    "activity": activity if activity else None,
                }
            },
        )
        await self.client.update_presence()
        await ctx.send(
            f"Successfully changed Killua's status to `{text}`! (I hope people like it >-<)",
            ephemeral=True,
        )

    @check()
    @commands.hybrid_command(
        extras={"category": Category.OTHER, "id": 29},
        usage="stats <usage/growth/general>",
    )
    @discord.app_commands.describe(type="The type of stats you want to see")
    async def stats(
        self, ctx: commands.Context, type: Literal["growth", "usage", "general", "api"]
    ):
        """Shows some statistics about the bot such as growth and command usage"""
        if type == "usage":
            await self.initial_top(ctx)
        elif type == "api":
            # if not bot owner deny
            if not await self.client.is_owner(ctx.author):
                return await ctx.send(
                    "API stats are currently only visible to the bot owner",
                    ephemeral=True,
                )
            return await self.api_stats(ctx)

        elif type == "growth":

            async def make_embed(page, embed: discord.Embed, _):
                embed.clear_fields()
                embed.description = ""

                data = (await DB.const.find_one({"_id": "growth"}))["growth"]

                if page == 1:
                    # Guild growth
                    return self._get_stats_embed(data, embed, "guilds")
                elif page == 2:
                    # User growth
                    return self._get_stats_embed(data, embed, "users")
                elif page == 3:
                    # Registered user growth
                    return self._get_stats_embed(data, embed, "registered_users")
                elif page == 4:
                    # Daily users
                    return self._get_stats_embed(data, embed, "daily_users")
                elif page == 5:
                    # Approximate users
                    return self._get_stats_embed(data, embed, "approximate_users")
                elif page == 6:
                    # User installs
                    return self._get_stats_embed(data, embed, "user_installs")

            return await Paginator(
                ctx, func=make_embed, max_pages=6, has_file=True
            ).start()
        else:
            n_of_commands = 0

            for command in self.client.tree.walk_commands():
                if not isinstance(
                    command, discord.app_commands.Group
                ) and not command.qualified_name.startswith("jishaku"):
                    n_of_commands += 1

            data = (await DB.const.find_one({"_id": "updates"}))["updates"]
            bot_version = (
                "`Development`"
                if self.client.is_dev
                else (data[-1]["version"] if "version" in data[-1] else "`Unknown`")
            )

            embed = discord.Embed.from_dict(
                {
                    "title": "General bot stats",
                    "fields": [
                        {
                            "name": "Bot started at",
                            "value": f"<t:{int(self.client.startup_datetime.timestamp())}:f>",
                            "inline": True,
                        },
                        {
                            "name": "Cached bot users",
                            "value": str(len(self.client.users)),
                            "inline": True,
                        },
                        {
                            "name": "Bot guilds",
                            "value": str(len(self.client.guilds)),
                            "inline": True,
                        },
                        {
                            "name": "Registered users",
                            "value": str(await DB.teams.count_documents({})),
                            "inline": True,
                        },
                        {
                            "name": "Bot commands",
                            "value": str(n_of_commands),
                            "inline": True,
                        },
                        {
                            "name": "Owner id",
                            "value": "606162661184372736",
                            "inline": True,
                        },
                        {
                            "name": "Latency",
                            "value": f"{int(self.client.latency*100)} ms",
                            "inline": True,
                        },
                        {
                            "name": "Shard",
                            "value": f"{self.client.shard_id or 0}/{self.client.shard_count}",
                            "inline": True,
                        },
                        {
                            "name": "Bot version",
                            "value": f"{bot_version}",
                            "inline": True,
                        },
                    ],
                    "color": 0x3E4A78,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            await ctx.send(embed=embed)

    @check()
    @commands.hybrid_command(
        extras={"category": Category.OTHER, "id": 30}, usage="info"
    )
    async def info(self, ctx: commands.Context):
        """Get some general information (lore) about the bot"""
        embed = discord.Embed(title="Infos about the bot", description=INFO)
        embed.color = 0x3E4A78
        return await ctx.send(embed=embed, ephemeral=True)

    @check()
    @commands.hybrid_command(
        extras={"category": Category.OTHER, "id": 31}, usage="voteremind <on/off>"
    )
    @discord.app_commands.describe(toggle="Toggle the voteremind on or off")
    async def voteremind(self, ctx: commands.Context, toggle: Literal["on", "off"]):
        """Toggle the voteremind on or off"""
        user = await User.new(ctx.author.id)
        if toggle == "on":
            if user.voting_reminder:
                return await ctx.send(
                    "You already have the voteremind enabled!", ephemeral=True
                )
            await user.toggle_votereminder()
            await ctx.send(
                "Enabled the voteremind! You can turn it off any time with this command!",
                ephemeral=True,
            )
        else:
            if not user.voting_reminder:
                return await ctx.send(
                    "You already have the voteremind disabled!", ephemeral=True
                )
            await user.toggle_votereminder()
            await ctx.send(
                "Disabled the voteremind! You can turn it back on any time with this command!",
                ephemeral=True,
            )


Cog = Dev

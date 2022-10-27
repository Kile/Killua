from discord.ext import commands
import discord

import math
from typing import List, Tuple
from io import BytesIO
from datetime import datetime
from matplotlib import pyplot as plt

from killua.bot import BaseBot
from killua.utils.checks import check
from killua.utils.paginator import Paginator
from killua.utils.classes import User, Guild #lgtm [py/unused-import]
from killua.utils.interactions import View, Button
from killua.static.enums import Category, Activities, Presences, StatsOptions
from killua.static.cards import Card #lgtm [py/unused-import]
from killua.static.constants import DB, UPDATE_CHANNEL, GUILD_OBJECT

class UsagePaginator(Paginator):
    """A normal paginator with a button that returns to the original help command"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.view.add_item(Button(label="Back", style=discord.ButtonStyle.red, custom_id="1"))

    async def start(self):
        view = await self._start()

        if view.ignore or view.timed_out:
            return
        
        await self.view.message.delete()
        await self.ctx.command.__call__(self.ctx, StatsOptions.usage)

class Dev(commands.Cog):

    def __init__(self, client: BaseBot):
        self.client = client
        self.version_cache = []

    async def version_autocomplete(
        self,
        _: discord.Interaction,
        current: str,
    ) -> List[discord.app_commands.Choice[str]]:

        if not self.version_cache:
            self.version_cache = [x["version"] for x in DB.updates.find_one({"_id": "log"})["past_updates"]]

        return [
            discord.app_commands.Choice(name=v, value=v)
            for v in self.version_cache if current.lower() in v.lower()
        ]

    def _create_piechart(self, data: List[list], ) -> discord.File:
        """Creates a piechart with the given data"""
        labels = [x[0] for x in data]
        values = [x[1] for x in data]
        buffer = BytesIO()
        plt.pie(values, labels=labels, autopct="%1.1f%%", shadow=True, textprops={'color':"w"})
        plt.axis("equal")
        plt.tight_layout()
        plt.savefig(buffer, format="png", transparent=True)
        buffer.seek(0)
        plt.close()
        file = discord.File(buffer, filename="piechart.png")
        return file

    def _create_graph(self, dates: List[datetime], y_points: List[int], label: str) -> BytesIO:
        """Creates a graph with y over time supplied in the dates list"""
        plt.style.use("seaborn") # After testing this is the best theme
        # Plotting the main graph
        plt.plot(dates, y_points, color="blue")
        plt.xlabel("Time")
        plt.ylabel(label)
        # Plot the trend
        avg_change_per_day = round(sum([y_points[i+1] - y_points[i] for i in range(len(y_points)-1)])/len(y_points), 2)
        start = y_points[0]
        trend = [start + avg_change_per_day * i for i in range(len(y_points))]
        plt.plot(dates, trend, linestyle=":", color="grey")

        plt.tight_layout() # Making the actual graph a bit bigger
        buf = BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()

        return buf

    def _calc_predictions(self, values: List[int]) -> dict:
        """Calculates various predictions for the given values"""

        #Calculates the average change between one value compared to the next one in the list
        change = [values[i+1] - values[i] for i in range(len(values)-1)]
        avg_change = round(sum(change)/len(values), 2)
        # Calculates the standart deviation of the avergae change
        std_change = round(math.sqrt(sum([(x - avg_change)**2 for x in change])/len(values)), 2)

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

    def _get_stats_embed(self, dates: List[datetime], data: List[dict], embed: discord.Embed, type: str) -> Tuple[discord.Embed, discord.File]:
        """Creates an embed with the stats of the given type"""
        type_list = [x[type] for x in data]
        buffer = self._create_graph(dates, type_list, type.replace("_", " ").title())
        file = discord.File(buffer, filename=f"{type}.png")
        add_data = self._calc_predictions(type_list)

        embed.set_image(url=f"attachment://{type}.png")
        type = type.replace("_", "") # Because we don't want the _ of registered_users
        embed.title = f"Statistics about {self.client.user.name}'s " + type.title()
        embed.add_field(name=f"Maximum {type} reached", value=add_data["max"]) # This is only really relevant for guilds and users as registered users cannot decrease
        embed.add_field(name=f"Average {type} last 10 days", value=add_data["recent_avg"])
        embed.add_field(name=f"Average {type} gained per day", value=add_data["avg_change"])
        embed.add_field(name=f"\U000003c3 of the average daily {type} gain", value=add_data["std_change"])
        return embed, file

    async def all_top(self, ctx: commands.Context, top: List[tuple]) -> None:
        """Shows a list of all top commands"""
        def make_embed(page, embed, pages):
            embed.title = "Top command usage"

            if len(pages)-page*10+10 > 10:
                top = pages[page*10-10:-(len(pages)-page*10)]
            elif len(pages)-page*10+10 <= 10:
                top = pages[-(len(pages)-page*10+10):]

            embed.description = "```\n" + "\n".join(["#"+str(n+1)+" /"+k+" with "+str(v)+" uses" for n, (k, v) in enumerate(top, page*10-10)]) + "\n```"
            return embed

        await UsagePaginator(ctx, top, func=make_embed, max_pages=math.ceil(len(top)/10)).start()

    async def group_top(self, ctx: commands.Context, top: List[tuple], interaction: discord.Interaction) -> None:
        """Displays a pie chart of the top used commands in a group"""
        # A list of all valid groups as strings
        possible_groups = [g.name for g in self.client.commands if not g.parent and g.name != "help"] # The only time a command doesn't have a parent is when it's a group
        group = await self.client.get_text_response(ctx, "Please enter a command group", interaction=interaction, style=discord.TextStyle.short, placeholder=(", ".join(possible_groups))[:97] + "...")
        if not group: return

        if not group.lower() in possible_groups:
            return await ctx.send("That is not a valid group", ephemeral=True)
        else:
            top = [(x[0].split(" ")[1], x[1]) for x in top if x[0].startswith(group.lower()) and len(x[0].split(" ")) > 1]
            rest = 0
            for x in top[-9:]:
                rest += x[1]

            if len(top) > 9:
                real_top = [*top[:9], ("other", rest)]
            else:
                real_top = top[:9]

            file = self._create_piechart(real_top)
            embed = discord.Embed(title=f"Top 10 used commands of group {group}", color=0x1400ff)
            embed.set_image(url="attachment://piechart.png")

            view = View(ctx.author.id)
            view.add_item(Button(label="Back", style=discord.ButtonStyle.red, custom_id="back"))

            msg = await ctx.send(embed=embed, file=file, view=view)
            await view.wait()
            
            if view.timed_out:
                await view.disable()

            if view.value:
                if view.value == "back":
                    await msg.delete()
                    await self.initial_top(ctx)

    async def initial_top(self, ctx: commands.Context) -> None:
        s = DB.stats.find_one({"_id": "commands"})["command_usage"]
        top = sorted(s.items(), key=lambda x: x[1], reverse=True)
        rest = 0
        for x in top[-9:]:
            rest += x[1]

        # creates a piechart in an embed with the top 10 commands using _create_piechart
        file = self._create_piechart([*top[:9], ("other", rest)])
        embed = discord.Embed(title="Top 10 used commands", color=0x1400ff)
        embed.set_image(url="attachment://piechart.png")

        view = View(ctx.author.id)
        view.add_item(Button(label="See all", style=discord.ButtonStyle.primary, custom_id="all"))
        view.add_item(Button(label="See for group", style=discord.ButtonStyle.primary, custom_id="group"))

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


    @commands.hybrid_group()
    async def dev(self, _: commands.Context):
        """A collection of commands regarding the development side of Killua"""
        ...

    #Eval command, unnecessary with the jsk extension but useful for database stuff
    @commands.is_owner()
    @commands.command(aliases=["exec"], extras={"category":Category.OTHER}, usage="eval <code>", hidden=True, with_app_command=False)
    @discord.app_commands.describe(code="The code to evaluate") # Since this is not an app command this won"t show up but is still added for consistency
    async def eval(self, ctx: commands.Context, *, code: str):
        """Standart eval command, owner restricted"""
        try:
            await ctx.send(f"```py\n{eval(code)}```")
        except Exception as e:
            await ctx.send(str(e))

    @commands.is_owner()
    @commands.command(extras={"category":Category.OTHER}, usage="say <text>", hidden=True, with_app_command=False)
    @discord.app_commands.describe(content="What to say") # Same thing as for the eval command
    async def say(self, ctx: commands.Context, *, content: str):
        """Let"s Killua say what is specified with this command. Possible abuse leads to this being restricted"""

        await ctx.message.delete()
        await ctx.send(content, reference=ctx.message.reference)

    @commands.is_owner()
    @dev.command(aliases=["publish-update", "pu"], extras={"category":Category.OTHER}, usage="publish_update <version> <text>", hidden=True)
    @discord.app_commands.guilds(GUILD_OBJECT)
    @discord.app_commands.describe(
        version="The name of the version to publish",
        update="The content of the update"
    )
    async def publish_update(self, ctx: commands.Context, version: str, *, update: str):
        """Allows me to publish Killua updates in a handy formart"""

        old = DB.updates.find_one({"_id": "current"})
        old_version = old["version"] if "version" in old else "No version"

        if version in [*[old_version],*[x["version"] for x in DB.updates.find_one({"_id": "log"})["past_updates"]]]:
            return await ctx.send("This is an already existing version")

        embed = discord.Embed.from_dict({
            "title": f"Killua Update `{old_version}` -> `{version}`",
            "description": update,
            "color": 0x1400ff,
            "footer": {"text": f"Update by {ctx.author}", "icon_url": str(ctx.author.avatar.url)},
            "image": {"url": "https://cdn.discordapp.com/attachments/780554158154448916/788071254917120060/killua-banner-update.png"}
        })

        data = {"version": version, "description": update, "published_on": datetime.now(), "published_by": ctx.author.id}
        DB.updates.update_one({"_id": "current"}, {"$set": data})
        DB.updates.update_one({"_id": "log"}, {"$push": {"past_updates": data}})
        self.version_cache.append(version)

        await ctx.send("Published new update " + f"`{old_version}` -> `{version}`", ephemeral=True)
        if self.client.is_dev: # We do not want to accidentally publish a message when testing
            return
        channel = self.client.get_channel(UPDATE_CHANNEL)
        msg = await channel.send(content= "<@&795422783261114398>", embed=embed)
        if not ctx.interaction:
            await ctx.message.delete()
        await msg.publish()

    @check()
    @dev.command(extras={"category":Category.OTHER}, usage="update <version(optional)>")
    @discord.app_commands.autocomplete(version=version_autocomplete)
    @discord.app_commands.describe(version="The version to get information about")
    async def update(self, ctx: commands.Context, version: str = None):
        """Allows you to view current and past updates"""
        if version is None:
            data = DB.updates.find_one({"_id": "current"})
        else:
            d = [x for x in DB.updates.find_one({"_id": "log"})["past_updates"] if x["version"] == version]
            if len(d) == 0:
                return await ctx.send("Invalid version!")
            data = d[0]
            
        author = self.client.get_user(data["published_by"])
        embed = discord.Embed.from_dict({
            "title": f"Infos about version `{data['version']}`",
            "description": str(data["description"]),
            "color": 0x1400ff,
            "footer": {"icon_url": str(author.avatar.url), "text": f"Published on {data['published_on'].strftime('%b %d %Y %H:%M:%S')}"}
        })
        await ctx.send(embed=embed)

    @commands.is_owner() 
    @dev.command(extras={"category":Category.OTHER}, usage="blacklist <user_id>", hidden=True)
    @discord.app_commands.guilds(GUILD_OBJECT)
    @discord.app_commands.describe(
        user="The user to blacklist",
        reason="The reason for the blacklist"
    )
    async def blacklist(self, ctx: commands.Context, user: str, *,reason = None):
        """Blacklisting bad people like Hisoka. Owner restricted"""
        user = await self.client.find_user(user)
        if not user:
            return await ctx.send("Invalid user!", ephermal=True)
        # Inserting the bad person into my database
        DB.blacklist.insert_one({"id": user, "reason": reason or "No reason provided", "date": datetime.now()})
        await ctx.send(f"Blacklisted user `{user}` for reason: {reason}", ephermal=True)
        
    @commands.is_owner()
    @dev.command(extras={"category":Category.OTHER}, usage="whitelist <user_id>", hidden=True)
    @discord.app_commands.guilds(GUILD_OBJECT)
    @discord.app_commands.describe(
        user="The user to whitelist"
    )
    async def whitelist(self, ctx: commands.Context, user: str):
        """Whitelists a user. Owner restricted"""
        user = await self.client.find_user(user)
        if not user:
            return await ctx.send("Invalid user!", ephermal=True)

        DB.blacklist.delete_one({"id": user})
        await ctx.send(f"Successfully whitelisted `{user}`")

    @commands.is_owner()
    @dev.command(aliases=["st", "pr", "status"], extras={"category":Category.OTHER}, usage="pr <text>", hidden=True)
    @discord.app_commands.guilds(GUILD_OBJECT)
    @discord.app_commands.describe(
        text="The text displayed as the status",
        activity="The activity Killua is doing",
        presence="Killua's presence"
    )
    async def presence(self, ctx: commands.Context, text: str, activity: Activities = None, presence: Presences = None):
        """Changes the presence of Killua. Owner restricted"""

        if text == "-rm":
            DB.presence.update_many({}, {"$set": {"text": None, "activity": None, "presence": None}})
            await ctx.send("Done! reset Killua's presence", ephemeral=True)
            return await self.client.update_presence()

        DB.presence.update_many({}, {"$set": {"text": text, "presence": presence.name if presence else None, "activity": activity.name if activity else None}})
        await self.client.update_presence()
        await ctx.send(f"Successfully changed Killua's status to `{text}`! (I hope people like it >-<)", ephemeral=True)

    @dev.command(extras={"category":Category.OTHER}, usage="stats")
    async def stats(self, ctx: commands.Context, type: StatsOptions):
        """Shows some statistics about the bot such as growth and command usage"""
        if type.name == "usage":
            await self.initial_top(ctx)
        else:
            def make_embed(page, embed, _):
                embed.clear_fields()

                data = DB.stats.find_one({"_id": "growth"})["growth"]
                dates = [x["date"] for x in data]

                if page == 1:
                    # Guild growth
                    return self._get_stats_embed(dates, data, embed, "guilds")
                elif page == 2:
                    # User growth
                    return self._get_stats_embed(dates, data, embed, "users")
                elif page == 3:
                    # Registered user growth
                    return self._get_stats_embed(dates, data, embed, "registered_users")

            return await Paginator(ctx, func=make_embed, max_pages=3, has_file=True).start()


Cog = Dev

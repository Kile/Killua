import discord
from discord.ext import commands
from typing import Union, List, Tuple, Dict, cast
from datetime import datetime
from random import randint

from killua.bot import BaseBot
from killua.utils.checks import check
from killua.utils.interactions import Select, View
from killua.utils.classes import User, Guild, LootBox
from killua.static.enums import Category
from killua.static.constants import (
    USER_FLAGS,
    KILLUA_BADGES,
    GUILD_BADGES,
    LOOTBOXES,
    PREMIUM_ALIASES,
    DB,
    BOOSTERS,
)


class Economy(commands.GroupCog, group_name="econ"):

    def __init__(self, client: BaseBot):
        self.client = client
        self._init_menus()

    def _init_menus(self) -> None:
        menus = []
        menus.append(
            discord.app_commands.ContextMenu(
                name="profile",
                callback=self.client.callback_from_command(self.profile, message=False),
                allowed_installs=discord.app_commands.AppInstallationType(
                    guild=True, user=True
                ),
                allowed_contexts=discord.app_commands.AppCommandContext(
                    guild=True, dm_channel=True, private_channel=True
                ),
                # guild_ids=[...],
            )
        )
        menus.append(
            discord.app_commands.ContextMenu(
                name="balance",
                callback=self.client.callback_from_command(self.jenny, message=False),
                allowed_installs=discord.app_commands.AppInstallationType(
                    guild=True, user=True
                ),
                allowed_contexts=discord.app_commands.AppCommandContext(
                    guild=True, dm_channel=True, private_channel=True
                ),
            )
        )

        for menu in menus:
            self.client.tree.add_command(menu)

    async def _get_user(self, user_id: int) -> Union[discord.User, None]:
        u = self.client.get_user(user_id)
        if not u:
            u = await self.client.fetch_user(user_id)
        return u

    def _fieldify_lootboxes(self, lootboxes: List[int]) -> List[dict]:
        """Creates a list of fields from the lootboxes in the passed list"""
        lbs: List[Tuple[int, int]] = (
            []
        )  # A list containing the a tuple with the amount and id of the lootboxes owned
        res: List[dict] = []  # The fields to be returned

        for lb in lootboxes:
            if lb not in (l := [y for _, y in lbs]):
                lbs.append((1, lb))
            else:
                indx = l.index(lb)
                lbs[indx] = (lbs[indx][0] + 1, lb)

        for lb in lbs:
            n, i = lb
            data = LOOTBOXES[i]
            res.append(
                {
                    "name": f"{n}x {data['emoji']} {data['name']} (id:{i})",
                    "value": data["description"],
                    "inline": False,
                }
            )

        return res

    def _fieldify_boosters(self, boosters: Dict[int, int]):
        """Creates a string from the boosters in the passed dict"""
        start = (
            "You have the following boosters:\n"
            if boosters
            else "You don't have any boosters yet. You can get them by opening lootboxes\n"
        )
        for booster in boosters:
            start += f"{BOOSTERS[int(booster)]['emoji']} {BOOSTERS[int(booster)]['name']} (id:{booster}) - {boosters[booster]}x\n"
        return start

    async def _getmember(
        self, user: Union[discord.Member, discord.User]
    ) -> discord.Embed:
        """A function to handle getting infos about a user for less messy code"""
        joined = self.client.convert_to_timestamp(user.id)

        info = await User.new(user.id)
        flags = [USER_FLAGS[x[0]] for x in user.public_flags if x[1]]
        if (user.avatar and user.avatar.is_animated()) or len(
            [
                x
                for x in self.client.guilds
                if user.id in [y.id for y in x.premium_subscribers]
            ]
        ) > 0:  # A very simple nitro check that is not too accurate
            flags.append(USER_FLAGS["nitro"])
        badges = [
            (
                KILLUA_BADGES[PREMIUM_ALIASES[x]]
                if x in PREMIUM_ALIASES.keys()
                else KILLUA_BADGES[x]
            )
            for x in info.badges
        ]

        if str(datetime.now()) > str(info.daily_cooldown):
            cooldown = "Ready to claim!"
        else:
            cooldown = f"<t:{int(info.daily_cooldown.timestamp())}:R>"

        return discord.Embed.from_dict(
            {
                "title": f"Information about {user.display_name}",
                "description": f"{user.id}\n{' '.join(flags)}",
                "fields": [
                    {
                        "name": "Killua Badges",
                        "value": " ".join(badges) if len(badges) > 0 else "No badges",
                        "inline": False,
                    },
                    {"name": "Jenny", "value": str(info.jenny), "inline": False},
                    {"name": "Account created at", "value": joined, "inline": False},
                    {
                        "name": "daily cooldown",
                        "value": cooldown or "Never claimed `daily` before",
                        "inline": False,
                    },
                ],
                "thumbnail": {
                    "url": str(user.display_avatar.url) if user.avatar else None
                },
                "image": {"url": user.banner.url if user.banner else None},
                "color": 0x3E4A78,
            }
        )

    async def _lb(self, ctx: commands.Context, limit: int = 10) -> dict:
        """Creates a list of the top members regarding jenny in a server"""
        members = await DB.teams.find(
            {"id": {"$in": [x.id for x in ctx.guild.members]}}
        ).to_list(None)
        top = sorted(
            members, key=lambda x: x["points"], reverse=True
        )  # Bringing it in a nice lederboard order
        points = 0
        for m in top:
            points += m["points"]  # Working out total points in the server

        return {
            "points": points,
            "top": [
                {"name": ctx.guild.get_member(x["id"]), "points": x["points"]}
                for x in top
            ][: (limit or len(top))],
        }

    async def lootbox_autocomplete(
        self, _: discord.Interaction, current: str
    ) -> List[discord.app_commands.Choice[str]]:
        """A function to autocomplete the lootbox name"""
        options = []
        for id, lb in LOOTBOXES.items():
            if current in lb["name"]:
                options.append(
                    discord.app_commands.Choice(name=lb["name"], value=str(id))
                )
        return options

    @check()
    @commands.guild_only()
    @commands.hybrid_command(
        aliases=["server"],
        extras={"category": Category.ECONOMY, "id": 32},
        usage="guild",
    )
    async def guild(self, ctx: commands.Context):
        """Displays infos about the current guild"""
        top = await self._lb(ctx, limit=1)
        guild = await Guild.new(ctx.guild.id)
        badges = " ".join([GUILD_BADGES[b] for b in guild.badges])

        embed = discord.Embed.from_dict(
            {
                "title": f"Information about {ctx.guild.name}",
                "fields": [
                    {"name": "Owner", "value": str(ctx.guild.owner)},
                    {
                        "name": "Killua Badges",
                        "value": (badges if len(badges) > 0 else "No badges"),
                    },
                    {"name": "Combined Jenny", "value": top["points"]},
                    {
                        "name": "Richest Member",
                        "value": f"{top['top'][0]['name']} with {top['top'][0]['points']} jenny",
                    },
                    {
                        "name": "Server created at",
                        "value": self.client.convert_to_timestamp(ctx.guild.id),
                    },
                    {"name": "Members", "value": ctx.guild.member_count},
                ],
                "description": str(ctx.guild.id),
                "thumbnail": {
                    "url": str(ctx.guild.icon.url if ctx.guild.icon else None)
                },
                "color": 0x3E4A78,
            }
        )
        await self.client.send_message(ctx, embed=embed)

    @check()
    @commands.guild_only()
    @commands.hybrid_command(
        aliases=["lb", "top"],
        extras={"category": Category.ECONOMY, "id": 33},
        usage="leaderboard",
    )
    async def leaderboard(self, ctx: commands.Context):
        """Get a leaderboard of members with the most jenny"""
        top = await self._lb(ctx)
        if top["points"] == 0:
            return await ctx.send(
                f"Nobody here has any jenny! Be the first to claim some with `{(await self.client.command_prefix(self.client, ctx.message))[2]}daily`!",
                allowed_mentions=discord.AllowedMentions.none(),
            )
        embed = discord.Embed.from_dict(
            {
                "title": f"Top users on guild {ctx.guild.name}",
                "description": "\n".join(
                    [
                        f"#{p+1} `{x['name']}` with `{x['points']}` jenny"
                        for p, x in enumerate(top["top"])
                    ]
                ),
                "color": 0x3E4A78,
                "thumbnail": {"url": str(ctx.guild.icon.url)},
            }
        )
        await self.client.send_message(ctx, embed=embed)

    @check()
    @commands.hybrid_command(
        aliases=["whois", "p", "user"],
        extras={"category": Category.ECONOMY, "id": 34},
        usage="profile <user(optional)>",
    )
    @discord.app_commands.describe(user="The user to get infos about")
    async def profile(self, ctx: commands.Context, user: str = None):
        """Get infos about a certain discord user with ID or mention"""
        if user is None:
            res = ctx.author
        else:
            res = await self.client.find_user(ctx, user)

            if not res:
                return await ctx.send(
                    f"Could not find user `{user}`",
                    allowed_mentions=discord.AllowedMentions.none(),
                    ephemeral=True,
                )

        embed = await self._getmember(res)
        return await self.client.send_message(
            ctx, embed=embed, ephemeral=hasattr(ctx, "invoked_by_context_menu")
        )

    @check()
    @commands.hybrid_command(
        aliases=["bal", "balance", "points"],
        extras={"category": Category.ECONOMY, "id": 35},
        usage="balance <user(optional)>",
    )
    @discord.app_commands.describe(user="The user to see the number of jenny of")
    async def jenny(self, ctx: commands.Context, user: str = None):
        """Gives you a users balance"""

        if not user:
            res = ctx.author
        else:
            res = await self.client.find_user(ctx, user)

            if not res:
                return await ctx.send("User not found", ephemeral=True)

        balance = (await User.new(res.id)).jenny
        return await ctx.send(
            f"{res.display_name}'s balance is {balance} Jenny",
            ephemeral=hasattr(ctx, "invoked_by_context_menu"),
        )

    @check()
    @commands.hybrid_command(
        extras={"category": Category.ECONOMY, "id": 36}, usage="daily"
    )
    async def daily(self, ctx: commands.Context):
        """Claim your daily Jenny with this command!"""
        now = datetime.now()
        user = await User.new(ctx.author.id)

        if str(user.daily_cooldown) > str(now):  # When the cooldown is still active
            return await ctx.send(
                f"You can claim your daily Jenny the next time <t:{int(user.daily_cooldown.timestamp())}:R>"
            )

        min, max = 50, 100
        if user.is_premium:
            min, max = (
                min * 2,
                max * 2,
            )  # Sadly `min, max *= 2` does not work, this is the only way to fit it in one line
        if ctx.guild and (await Guild.new(ctx.guild.id)).is_premium:
            min, max = min * 2, max * 2
        daily = randint(min, max)
        if user.is_entitled_to_double_jenny:
            daily *= 2

        await user.claim_daily()
        await user.add_jenny(daily)
        await ctx.send(
            f"You claimed your {daily} daily Jenny and hold now on to {user.jenny}"
        )

    @check()
    @commands.hybrid_command(
        extras={"category": Category.ECONOMY, "id": 37}, usage="open"
    )
    async def open(self, ctx: commands.Context):
        """Open a lootbox with an interactive UI"""
        if len((user := await User.new(ctx.author.id)).lootboxes) == 0:
            return await ctx.send("Sadly you don't have any lootboxes!")

        lootboxes = self._fieldify_lootboxes(user.lootboxes)
        embed = discord.Embed.from_dict(
            {
                "title": "Choose a lootbox to open!",
                "fields": lootboxes,
                "color": 0x3E4A78,
            }
        )
        lbs = []
        for l in user.lootboxes:
            if l not in lbs:
                lbs.append(l)

        view = View(ctx.author.id)
        select = Select(
            options=[
                discord.SelectOption(
                    label=LOOTBOXES[lb]["name"],
                    emoji=LOOTBOXES[lb]["emoji"],
                    value=str(lb),
                    description=(
                        d
                        if len((d := LOOTBOXES[lb]["description"])) < 47
                        else d[:47] + "..."
                    ),
                )
                for lb in lbs
            ],
            placeholder="Select a box to open",
        )
        view.add_item(item=select)

        msg = await ctx.send(embed=embed, view=view)
        await view.wait()

        await view.disable(msg)
        if view.timed_out:
            return await ctx.send("Timed out!", ephemeral=True)

        await user.remove_lootbox(view.value)
        values = await LootBox.generate_rewards(view.value)
        box = LootBox(ctx, values)
        return await box.open()

    @check()
    @commands.hybrid_command(
        aliases=["lootboxes", "inv"],
        extras={"category": Category.ECONOMY, "id": 38},
        usage="inventory",
    )
    async def inventory(self, ctx: commands.Context):
        """Displays the owned lootboxes and boosters"""
        if (
            len((user := await User.new(ctx.author.id)).lootboxes) == 0
            and sum(user.boosters.values()) == 0
        ):
            return await ctx.send("Sadly you don't have any lootboxes or boosters!")

        boosters = self._fieldify_boosters(user.boosters)
        lootboxes = self._fieldify_lootboxes(user.lootboxes)
        embed = discord.Embed.from_dict(
            {
                "title": "Lootbox inventory",
                "description": boosters,
                "color": 0x3E4A78,
                "fields": lootboxes,
                "footer": {
                    "text": f"open a lootbox with {(await self.client.command_prefix(self.client, ctx.message))[2]}open"
                },
            }
        )
        embed.timestamp = datetime.now()
        await ctx.send(embed=embed)

    @check()
    @commands.hybrid_command(
        extras={"category": Category.ECONOMY, "id": 39}, usage="boxinfo <box_id>"
    )
    @discord.app_commands.autocomplete(box=lootbox_autocomplete)
    @discord.app_commands.describe(box="The box to get infos about")
    async def boxinfo(self, ctx: commands.Context, box: str):
        """Get infos about any box you desire"""
        if box.isdigit() and not int(box) in LOOTBOXES.keys() or not box.isdigit():
            box = self.client.get_lootbox_from_name(box)
            if not box:
                return await ctx.send("Invalid box name or id", ephemeral=True)

        data = LOOTBOXES[int(box)]

        c_min, c_max = data["cards_total"]
        j_min, j_max = data["rewards"]["jenny"]
        b_min, b_max = data["boosters_total"]
        contains = (
            f"{data['rewards_total']} total rewards\n{f'{c_min}-{c_max}' if c_max != c_min else c_min} cards\n"
            + (
                f"{j_min}-{j_max} jenny per field\n"
                if j_max > 0
                else "No jenny in this box\n"
            )
            + (
                ""
                if c_max == 0
                else f"card rarities: {' or '.join(data['rewards']['cards']['rarities'])}\ncard types: {' or '.join(data['rewards']['cards']['types'])}"
            )
            + (
                (
                    (f"{b_min}" if b_min == b_max else f"\n{b_min}-{b_max}")
                    + f" boosters\nAvailable boosters: {' '.join([BOOSTERS[int(x)]['emoji'] for x in data['rewards']['boosters']])}"
                )
                if b_max != 0
                else ""
            )
        )
        embed = discord.Embed.from_dict(
            {
                "title": f"Infos about lootbox {data['emoji']} {data['name']}",
                "description": data["description"],
                "fields": [
                    {"name": "Contains", "value": contains, "inline": False},
                    {"name": "Price", "value": data["price"], "inline": False},
                    {"name": "Buyable", "value": "Yes" if data["available"] else "No"},
                ],
                "color": 0x3E4A78,
            }
        )
        embed, file = await self.client.make_embed_from_api(
            cast(str, data["image"]).format(
                self.client.api_url(to_fetch=self.client.is_dev)
            ),
            embed,
        )
        await ctx.send(embed=embed, file=file)

    def _booster_from_name(self, name: str):
        for booster, value in BOOSTERS.items():
            if value["name"].lower() == name.lower():
                return booster
        return None

    async def booster_autocomplete(self, _: commands.Context, booster: str):
        if booster.isdigit():
            return [
                discord.app_commands.Choice(name=str(x), value=str(x))
                for x in BOOSTERS.keys()
                if str(x).startswith(booster)
            ]
        return [
            discord.app_commands.Choice(name=BOOSTERS[x]["name"], value=str(x))
            for x in BOOSTERS.keys()
            if cast(str, BOOSTERS[x]["name"]).lower().startswith(booster.lower())
        ]

    @check()
    @commands.hybrid_command(
        extras={"category": Category.ECONOMY, "id": 119},
        usage="boosterinfo <booster_id>",
    )
    @discord.app_commands.autocomplete(booster=booster_autocomplete)
    @discord.app_commands.describe(booster="The booster to get infos about")
    async def boosterinfo(self, ctx: commands.Context, booster: str):
        """Get infos about any booster you desire"""
        if booster.isdigit() and not int(booster) in BOOSTERS.keys():
            booster = self._booster_from_name(booster)
            if not booster:
                return await ctx.send("Invalid booster name or id", ephemeral=True)

        data = BOOSTERS[int(booster)]

        rarities = {
            0.1: "Extremely rate",
            0.2: "Very rare",
            0.3: "Rare",
            0.5: "Uncommon",
            0.7: "Common",
            0.9: "Very common",
        }

        embed = discord.Embed.from_dict(
            {
                "title": f"Infos about booster {data['emoji']} {data['name']}",
                "description": data["description"],
                "fields": [
                    {
                        "name": "Rarity",
                        "value": "-# How rare the booster is\n"
                        + next(
                            (
                                v
                                for k, v in rarities.items()
                                if k
                                >= (
                                    data["probability"]
                                    / sum(
                                        [
                                            BOOSTERS[x]["probability"]
                                            for x in BOOSTERS.keys()
                                        ]
                                    )
                                )
                            ),
                            None,
                        ),
                        "inline": True,
                    },
                    {
                        "name": "Stack-able",
                        "value": "-# If it can be used more than once per box\n"
                        + ("Yes" if data["stackable"] else "No"),
                        "inline": True,
                    },
                ],
                "color": 0x3E4A78,
            }
        )
        embed, file = await self.client.make_embed_from_api(
            cast(str, data["image"]).format(
                self.client.api_url(to_fetch=self.client.is_dev)
            ),
            embed,
        )
        await ctx.send(embed=embed, file=file)


Cog = Economy

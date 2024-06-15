import discord
from discord.ext import commands, tasks

from typing import List, Union, Literal
from aiohttp import ClientSession
from datetime import datetime

from killua.metrics import PREMIUM_USERS
from killua.bot import BaseBot
from killua.utils.checks import check, premium_user_only
from killua.utils.classes import User, Guild, LootBox
from killua.static.enums import Category
from killua.static.constants import PATREON_TIERS, GUILD, BOOSTER_ROLE, PATREON, LOOTBOXES, PREMIUM_BENEFITS, DB

class Patrons:

    def __init__(self, patrons: List[dict]):
        self.patrons = patrons
        self.invalid = [x for x in self.patrons if x["discord"] is None]

    def __iter__(self):
        self.pos = 0
        return self
  
    def __next__(self): # This is to check `if id in Patrons`
        self.pos += 1

        if self.pos > len(self.patrons):
            raise StopIteration

        return self.patrons[self.pos-1]["discord"]


class Patreon:
    """A class which returns all current patreons with the campain specified and their discord id or None"""
    def __init__(self, session: ClientSession, token: str, campain_id: Union[str, int]):
        self.session = session
        self.token = token
        self.campain_id = campain_id
        self.url = f"https://www.patreon.com/api/oauth2/v2/campaigns/{self.campain_id}/members?page%5B100%5D&include=currently_entitled_tiers%2Cuser&fields%5Bmember%5D=full_name%2Cis_follower%2Clast_charge_date%2Clast_charge_status%2Clifetime_support_cents%2Ccurrently_entitled_amount_cents%2Cpatron_status%2Cpledge_relationship_start&fields%5Buser%5D=social_connections&page%5Bcount%5D=100"

    def _int_else(self, i: Union[str, None]) -> Union[int, None]:
        """Turns a string into an integer if it exists, else returns None"""
        return int(i) if i else None

    def _catch(self, d:dict) -> Union[str, None]:
        """Tries to get the discord id from the response, if any step on the way fails it returns None"""
        try:
            return d["attributes"]["social_connections"]["discord"]["user_id"]
        except KeyError: # In case this happens I still want to have a value, just `None`
            return None

    async def _make_request(self, url: str) -> dict:
        """Makes a request to the Patreon API"""
        res = await self.session.get(url, headers={"Authorization": f"Bearer {self.token}"})
        return await res.json()

    async def _paginate(self, data: dict, prev: List[dict]) -> List[dict]:
        """Paginates through all patreons and returns a list of all patreons"""
        if "links" in data.keys():
            res = await self._make_request(data["links"]["next"])
            patrons = [*prev, *self._format_patrons(res)]
            return await self._paginate(res, patrons)
        else:
            return prev

    async def _get(self, data: dict) -> List[dict]:
        """Gets a list of all discord ids of the patrons"""
        prev: List[dict] = self._format_patrons(data)
        if "links" in data.keys():
            return await self._paginate(data, prev)
        else:
            return prev

    def _get_user_info(self, data: list, user: str) -> dict:
        """Finds the relevant info by comparing user ids"""
        return next((x for x in data if "user" in x["relationships"].keys() and x["relationships"]["user"]["data"]["id"] == user), None) # Think this is stupid? Thank Python and Patreon

    def _format_patrons(self, data: dict) -> List[dict]:
        res:List[dict] = []
        for i in data["included"]:
            if i["type"] == "user":
                user = self._get_user_info(data["data"], i["id"])
                try:
                    res.append({"discord": self._int_else(self._catch(i)), "tier": sorted(user["relationships"]["currently_entitled_tiers"]["data"], key=lambda x: int(x["id"]))[0]["id"]})
                except Exception: # If this happens something with the tier went wrong. This means they are no longer subscribed and I want to ignore that case
                    pass

        return res

    async def get_patrons(self) -> Patrons:
        res = await self._make_request(self.url)
        valid = await self._get(res)
        # return valid
        return Patrons(valid)

class Premium(commands.Cog):

    def __init__(self, client: BaseBot):
        self.client = client
        self.invalid = True # this is only `True` the first time the bot starts because the boosters of the support server are not cached at that point, so it avoids removing their badge

    @commands.Cog.listener()
    async def on_ready(self):
        if self.invalid:
            self.get_patrons.start()

    def _get_boosters(self) -> list:
        """Gets a list of all the boosters of the support server"""
        guild = self.client.get_guild(GUILD)
        if guild is None:
            self.invalid = True
            return []
        return [x.id for x in guild.members if BOOSTER_ROLE in [r.id for r in x.roles]]

    def _get_differences(self, current: Patrons, saved: List[dict]) -> List[dict]:
        """Returns a list of dictionaries containing a user id and the badge to assign. If the badge is None, they will loose their premium badges"""
        boosters = self._get_boosters()
        new_patrons = [*[x for x in current.patrons if x["discord"] not in [x["id"] for x in saved]], *[{"discord": b, "tier": list(PATREON_TIERS.keys())[0]} for b in boosters if b not in [s["id"] for s in saved]]]
        # Kinda hacky ways to do it but saves lines
        removed_patrons = [{"discord": x["id"], "tier": None} for x in saved if x["id"] not in current and (x["id"] not in boosters and not self.invalid)]
        different_badges = [x for x in current.patrons if x["tier"] not in [y["id"] for y in saved if y["id"] == x["discord"]]]
        return [*new_patrons, *removed_patrons, *different_badges]

    def _assign_badges(self, diff: List[dict]) -> None:
        """Assigns the changed badges to the users"""
        for d in diff:
            user = User(d["discord"])
            premium_guilds = user.premium_guilds
            badges = user.badges

            for k in PATREON_TIERS.keys():
                if k in badges:
                    badges.remove(k)

            if d["tier"] is None:
                Guild.bullk_remove_premium([int(x) for x in premium_guilds.keys()])
                user.clear_premium_guilds()
            else:
                badges.append(d["tier"])

            user.set_badges(badges)

    def _get_subscription_entitlements(self, all: List[discord.Entitlement]) -> List[discord.Entitlement]:
        """Compares entitlement IDs to cached SKU IDs to determine which are subscriptions"""
        entitlements = []
        for sku in self.client.cached_skus:
            if sku.type != discord.SKUType.subscription: continue # ignore non-subscription SKUs
            if sku.flags.guild_subscription: continue # ignore guild subscriptions
            entitlements.extend([entitlement for entitlement in all if entitlement.sku_id == sku.id and not entitlement.is_expired()])

        return entitlements
    
    def _get_coresponding_consumable_sku(self, ent: discord.Entitlement) -> Union[discord.SKU, None]:
        """Gets the consumable SKU that corresponds to the entitlement"""
        for sku in self.client.cached_skus:
            if sku.type != discord.SKUType.consumable: continue
            if sku.id == ent.sku_id:
                return sku
    
    @commands.Cog.listener()
    async def on_entitlement_create(self, ent: discord.Entitlement):
        self.client.cached_entitlements.append(ent)

        # If the entitlement is a consumable, apply consumable and dm user
        sku = self._get_coresponding_consumable_sku(ent)
        if not sku: return # TODO if subbing for the first time, thank user

        user = User(ent.user_id)
        # Find lootbox
        lootbox, amount = LootBox.get_lootbox_from_sku(sku)
        for _ in range(amount):
            user.add_lootbox(lootbox)

        # DM user
        try:
            user = self.client.get_user(ent.user_id) or await self.client.fetch_user(ent.user_id)
            await user.send(f"Thank you for supporting me! You have received {amount}x {LOOTBOXES[lootbox]['name']}{LOOTBOXES[lootbox]['emoji']}! Open it with `k!open`")
        except discord.HTTPException:
            pass # unable to dm

        await ent.consume()

    @commands.Cog.listener()
    async def on_entitlement_delete(self, ent: discord.Entitlement):
        self.client.cached_entitlements.remove(ent)

    @commands.Cog.listener()
    async def on_entitlement_update(self, ent: discord.Entitlement):
        # Find entitlement by id
        index = next((i for i, e in enumerate(self.client.cached_entitlements) if e.id == ent.id), None)
        if index is None: return

        self.client.cached_entitlements[index] = ent

        # TODO if subscription renewal, thank user

    @tasks.loop(minutes=2)
    async def get_patrons(self):
        saved_patrons = [x for x in DB.teams.find({"badges": {"$in": list(PATREON_TIERS.keys())}})]

        current_patrons = await Patreon(self.client.session, PATREON, "5394117").get_patrons()
        entitelments = self._get_subscription_entitlements(self.client.cached_entitlements)

        # Currently I am only allowed to have one subscription so I don't need to check for the type
        # This is a TODO to make smarter in the future once I am allowed more
        tier_1 = next((k for k, v in PATREON_TIERS.items() if v["id"] == 1), None)

        # Map the entitlements to the discord id
        entitelment_ids = [{"tier": tier_1, "discord": e.user_id} for e in entitelments]

        current_patrons.patrons.extend(entitelment_ids)

        # Save stat to prometheus
        PREMIUM_USERS.set(len(current_patrons.patrons))

        diff = self._get_differences(current_patrons, saved_patrons)
        self._assign_badges(diff)
        self.invalid = False
    
    @get_patrons.before_loop
    async def before_get_patrons(self) -> None:
        # Chunk guild to be able to see who has the booster role
        await self.client.get_guild(GUILD).chunk()
        await self.client.wait_until_ready()

    @commands.hybrid_group()
    async def premium(self, _: commands.Context):
        """Premium commands"""
        ...

    @commands.guild_only()
    @premium_user_only()
    @premium.command(extras={"category": Category.OTHER, "id": 67}, usage="guild <add/remove>")
    @discord.app_commands.describe(action="Wether to add or remove the premium status of the current server")
    async def guild(self, ctx: commands.Context, action: Literal["add", "remove"]):
        """Add or remove the premium status of a guild with this command"""
        if action == "add":

            if not (user:= User(ctx.author.id)).is_premium:
                return await ctx.send("Sadly you aren't a premium subscriber so you don't have premium guilds! Become a premium subscriber here: https://www.patreon.com/KileAlkuri")

            if len(user.premium_guilds.keys()) > PATREON_TIERS[user.premium_tier]["premium_guilds"]:
                return await ctx.send("You first need to remove premium perks from one of your other servers to give this server premium status")

            if (guild:= Guild(ctx.guild.id)).is_premium:
                return await ctx.send("This guild already has the premium status!")

            guild.add_premium()
            user.add_premium_guild(ctx.guild.id)
            await ctx.send("Success! This guild is now a premium guild")

        else:
            
            if not (guild:= Guild(ctx.guild.id)).is_premium:
                return await ctx.send("This guild is not a premium guild, so you don't remove it's premium status! Looking for premium? Visit https://www.patreon.com/KileAlkuri")
            
            if not str(guild.id) in ((user:= User(ctx.author.id)).premium_guilds.keys()):
                return await ctx.send("You are not the one who added the premium status to this server, so you can't remove it")

            if not (diff:= (datetime.now()-user.premium_guilds[str(ctx.guild.id)]).days) > 7:
                return await ctx.send(f"You need to wait {7-int(diff)} more days before you can remove this servers premium status!")

            guild.remove_premium()
            user.remove_premium_guild(ctx.guild.id)
            await ctx.send("Successfully removed this servers premium status!")

    @check()
    @premium_user_only()
    @premium.command(extras={"category": Category.ECONOMY, "id": 68}, usage="weekly")
    async def weekly(self, ctx: commands.Context):
        """Claim a weekly lootbox with this command"""
        user = User(ctx.author.id)

        if user.weekly_cooldown and user.weekly_cooldown > datetime.now():
            cooldown = f"<t:{int(user.weekly_cooldown.timestamp())}:R>"
            return await ctx.send(f"You can claim your weekly lootbox the next time {cooldown}")

        lootbox = LootBox.get_random_lootbox()
        user.claim_weekly()
        user.add_lootbox(lootbox)

        await ctx.send(f"Successfully claimed lootbox: {LOOTBOXES[lootbox]['name']}")

    @check()
    @premium.command(aliases=["support"], extras={"category":Category.FUN, "id": 69}, usage="info")
    async def info(self, ctx: commands.Context):
        """List of all the premium perks that come along with being a patron!"""
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Get premium", url="https://patreon.com/kilealkuri"))
        embed = discord.Embed.from_dict({
            "title": "**Support Killua**",
            "thumbnail":{"url": "https://cdn.discordapp.com/avatars/758031913788375090/e44c0de4678c544e051be22e74bc502d.png?size=1024"},
            "description": PREMIUM_BENEFITS,
            "color": 0x3e4a78
        })
        await self.client.send_message(ctx, embed=embed, view=view)

Cog = Premium
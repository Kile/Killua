import io
from lib2to3.pytree import Base
import sys
import discord

import logging
import traceback
from datetime import datetime
from discord.ext import commands, tasks
from PIL import Image

from killua.bot import BaseBot
from killua.utils.classes import Guild, Book
from killua.static.enums import PrintColors
from killua.static.constants import TOPGG_TOKEN, DBL_TOKEN, PatreonBanner, DB

class Events(commands.Cog):

    def __init__(self, client: BaseBot):
        self.client = client
        self.status_started = False
        self.client.startup_datetime = datetime.now()

    async def _post_guild_count(self) -> None:
        """Posts relevant stats to the botlists Killua is on"""
        data = { # The data for discordbotlist
            "guilds": len(self.client.guilds),
            "users": len(self.client.users)
        }

        await self.client.session.post(f"https://discordbotlist.com/api/v1/bots/756206646396452975/stats", headers={"Authorization": DBL_TOKEN}, data=data)
        await self.client.session.post(f"https://top.gg/api/bots/756206646396452975/stats", headers={"Authorization": TOPGG_TOKEN}, data={"server_count": len(self.client.guilds)})

    async def _load_cards_cache(self) -> None:
        """Downloads all the card images so the image manipulation is fairly fast"""
        cards = [x for x in DB.items.find()]

        if len(cards) == 0:
            return logging.error(f"{PrintColors.WARNING}No cards in the database, could not load cache{PrintColors.ENDC}")

        logging.info(f"{PrintColors.WARNING}Loading cards cache....{PrintColors.ENDC}")
        percentages = [25, 50, 75]
        for p, item in enumerate(cards):
            try:
                if item["_id"] in Book.card_cache:
                    continue # in case the event fires multiple times this avoids using unnecessary cpu power

                async with self.client.session.get(item["Image"]) as res:
                    image_bytes = await res.read()
                    image_card = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
                    image_card = image_card.resize((84, 115), Image.ANTIALIAS)

                Book.card_cache[str(item["_id"])] = image_card
                if len(percentages) >= 1 and (p/len(cards))*100 > (percent:= percentages[0]):
                    logging.info(f"{PrintColors.WARNING}Cache loaded {percent}%...{PrintColors.ENDC}")
                    percentages.remove(percent)
            except Exception as e:
                logging.error(f"{PrintColors.FAIL}Failed to load card {item['_id']} with error: {e}{PrintColors.ENDC}")

        logging.info(f"{PrintColors.OKGREEN}All cards successfully cached{PrintColors.ENDC}")

    async def _set_patreon_banner(self) -> None:
        """Loads the patron banner bytes so it can be quickly sent when needed"""
        res = await self.client.session.get(PatreonBanner.URL)
        image_bytes = await res.read()
        PatreonBanner.VALUE = image_bytes
        logging.info(f"{PrintColors.OKGREEN}Successfully loaded patreon banner{PrintColors.ENDC}")

    def print_dev_text(self) -> None:
        logging.info(f"{PrintColors.OKGREEN}Running bot in dev enviroment...{PrintColors.ENDC}")

    async def cog_load(self):
        #Changing Killua's status
        await self._set_patreon_banner()
        if self.client.is_dev:
            self.print_dev_text()
        else:
            await self._post_guild_count()
            await self._load_cards_cache()

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.status_started:
            self.status.start()
            self.status_started = True

        logging.info(PrintColors.OKGREEN + "Logged in as: " + self.client.user.name + f" (ID: {self.client.user.id})" + PrintColors.ENDC)

    @tasks.loop(hours=12)
    async def status(self):
        await self.client.update_presence() # For some reason this does not work in cog_load because it always fires before the bot is connected and 
        # thus throws an error so I have to do it a bit more hacky in here
        if not self.client.is_dev:
            await self._post_guild_count()

    @status.before_loop
    async def before_status(self):
        await self.client.wait_until_ready()

    @tasks.loop(hours=24)
    async def save_guilds(self):
        # this is currently not used but the earlier we collect this data, the better because I do plan to use it
        if not self.client.is_dev:
            DB.stats.update_one({"_id": "growth"}, {"$push": {"growth": {"date": datetime.now() ,"guilds": len(self.client.guilds), "users": len(self.client.users), "registered_users": DB.teams.count_documents()}}})

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        #Changing the status
        await self.client.update_presence()
        Guild.add_default(guild.id)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        #Changing Killua's status
        await self.client.update_presence()
        Guild(guild.id).delete()
        await self._post_guild_count()

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error):

        if ctx.channel.permissions_for(ctx.me).send_messages and not self.client.is_dev: # we don't want to raise an error inside the error handler when Killua ' send the error because that does not trigger `on_command_error`
            return

        if ctx.command:
            usage = f"`{self.client.command_prefix(self.client, ctx.message)[2]}{(ctx.command.parent.name + ' ') if ctx.command.parent else ''}{ctx.command.usage}`"

        if isinstance(error, commands.BotMissingPermissions):
            return await ctx.send(f"I don't have the required permissions to use this command! (`{', '.join(error.missing_permissions)}`)")

        if isinstance(error, commands.MissingPermissions):
            return await ctx.send(f"You don't have the required permissions to use this command! (`{', '.join(error.missing_permissions)}`)")

        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send(f"Seems like you missed a required argument for this command: `{str(error.param).split(':')[0]}`")

        if isinstance(error, commands.UserInputError):
            return await ctx.send(f"Seems like you provided invalid arguments for this command. This is how you use it: {usage}", allowed_mentions=discord.AllowedMentions.none())

        if isinstance(error, commands.NotOwner):
            return await ctx.send("Sorry, but you need to be the bot owner to use this command")

        if isinstance(error, commands.BadArgument):
            return await ctx.send(f"Could not process arguments. Here is the command should be used: {usage}", allowed_mentions=discord.AllowedMentions.none())

        if isinstance(error, commands.NoPrivateMessage):
            return await ctx.send("This command can only be used inside of a guild")

        if isinstance(error, commands.CommandNotFound) or isinstance(error, commands.CheckFailure): # I don't care if this happens
            return 

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Report bug", url=self.client.support_server_invite))
        await ctx.send(":x: an unexpected error occured. If this should keep happening, please report it by clicking on the button and using `/report` in the support server.", view=view)

        if self.client.is_dev: # prints the full traceback in dev enviroment
            logging.error(PrintColors.FAIL + "Ignoring exception in command {}:".format(ctx.command))
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
            return print(PrintColors.ENDC)
        
        else:
            guild = ctx.guild.id if ctx.guild else "dm channel with "+ str(ctx.author.id)
            command = ctx.command.name if ctx.command else "Error didn't occur during a command"
            logging.error(f"{PrintColors.FAIL}------------------------------------------")
            logging.error(f"An error occurred\nGuild id: {guild}\nCommand name: {command}\nError: {error}")
            logging.error(f"------------------------------------------{PrintColors.ENDC}")

Cog = Events

async def setup(client):
    await client.add_cog(Events(client))
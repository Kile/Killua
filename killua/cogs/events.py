import io
import sys
import discord

import logging
import traceback
from datetime import datetime
from discord.ext import commands, tasks
from PIL import Image
from typing import Dict, List
from matplotlib import pyplot as plt

from killua.bot import BaseBot
from killua.utils.classes import Guild, Book
from killua.static.enums import PrintColors
from killua.static.constants import TOPGG_TOKEN, DBL_TOKEN, PatreonBanner, DB, GUILD

class Events(commands.Cog):

    def __init__(self, client: BaseBot):
        self.client = client
        self.skipped_first = False
        self.status_started = False
        self.log_channel_id = 718818548524384310
        self.client.startup_datetime = datetime.now()

    @property
    def old_commands(self) -> List[str]:
        return self._get_old_commands()

    @property
    def log_channel(self):
        return self.client.get_guild(GUILD).get_channel(self.log_channel_id)

    def _get_old_commands(self) -> List[str]:
        """Gets a list of all commands names without and their aliases"""
        cmds = []
        for command in self.client.tree.walk_commands():
            if not isinstance(command, discord.app_commands.Group) and not command.name == "help" and\
                not command.qualified_name.startswith("jishaku") and \
                    not command.qualified_name.startswith("todo") and \
                        not command.qualified_name.startswith("tag"):
                            cmds.append(command.name)
        return cmds

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
    async def on_message(self, message: discord.Message) -> None:
        prefix = "kil!" if self.client.is_dev else (Guild(message.guild.id).prefix if message.guild else "k!")
        if message.content.startswith(prefix):
            if message.content[len(prefix):].split(" ")[0] in self.old_commands:
                return await message.reply("This command has been moved over to a command group, check `/help` to find the new command and `/update` to see what's changing with Killua.", allowed_mentions=discord.AllowedMentions.none())

    @commands.Cog.listener()
    async def on_ready(self):
        self.save_guilds.start()
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
        from killua.static.constants import daily_users

        if not self.client.is_dev and self.skipped_first:
            DB.const.update_one({"_id": "growth"}, {"$push": {"growth": {"date": datetime.now() ,"guilds": len(self.client.guilds), "users": len(self.client.users), "registered_users": DB.teams.count_documents({}), "daily_users": len(daily_users)}}})
            daily_users = [] # Resetting the daily users list lgtm [py/unused-local-variable]
        elif not self.skipped_first: # We want to avoid saving data each time the bot restarts, start 24h after one
            self.skipped_first = True

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
    async def on_member_join(self, member: discord.Member):
        # Welcomes new member
        if not self.client.is_dev and member.guild.id == GUILD: # In theory it would be cool if the dev bot welcomed you but it just isn't always online
            embed = discord.Embed.from_dict({
                "title": "Welcome to the Killua support server a.k.a. Kile's dev!",
                "description": "You joined. What now?\n\n**Where to go**\n" + \
                    "┗ <#1019657047568035841> to recieve help or report bugs\n" + \
                    "┗ <#787819439596896288> To get some ping roles\n" +\
                    "┗ <#886546434663538728> Good place to check before asking questions\n" +\
                    "┗ <#754063177553150002> To see newest announcements\n" +\
                    "┗ <#757170264294424646> Read up on the newest Killua updates\n" +\
                    "┗ <#716357592493981707> Use bots in here\n" +\
                    "┗ <#811903366925516821> Check if there is any known outage/bug\n\n" +\
                    "Thanks for joining and don't forget to vote for Killua! :)",
                "color": 0x1400ff,
            })
            embed.set_thumbnail(url=self.client.user.avatar.url if self.client.user else None)
            embed.timestamp = datetime.now()

            await self.log_channel.send(content=member.mention, embed=embed)
            # try:
            #     await member.send(embed=embed)
            # except discord.Forbidden:
            #     pass

    def _create_piechart(self, data: List[list], title: str) -> discord.File:
        """Creates a piechart with the given data"""
        data = [l for l in data if l[1] > 0] # We want to avoid a 0% slice

        labels = [x[0] for x in data]
        values = [x[1] for x in data]
        colours = [x[2] for x in data]
        buffer = io.BytesIO()
        plt.pie(values, labels=labels, autopct="%1.1f%%", shadow=True, textprops={'color':"w"}, colors=colours)
        plt.title(title, fontdict={"color": "w"})
        plt.axis("equal")
        plt.tight_layout()
        plt.savefig(buffer, format="png", transparent=True)
        buffer.seek(0)
        plt.close()
        file = discord.File(buffer, filename="piechart.png")
        return file

    def find_counter_start(self, title: str) -> int:
        """Finds where the counter in a poll title starts"""
        revers = title[::-1]
        for i, char in enumerate(revers):
            if char == "`" and revers[i-1] == "[":
                return i+1

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.component:
            if interaction.data["custom_id"] and (interaction.data["custom_id"].startswith("poll:") or interaction.data["custom_id"].startswith("wyr:")):
                _p, action, poll_creator = interaction.data["custom_id"].split(":")
                poll = _p == "poll" # As the logic for polls and wyr overlaps we can use the same code for both, just need to differentiate for a few small things

                if action.startswith("option"):
                    option = int(action.split("-")[1]) if poll else {"a": 1, "b": 2}[action.split("-")[1]]
                    
                    votes: Dict[int, list] = {}

                    for pos, field in enumerate(interaction.message.embeds[0].fields):
                        votes[pos] = [int(v.replace("<@", "").replace(">", "")) for v in field.value.split("\n") if not v == ("No votes" if poll else "No takers")]
                        if interaction.user.id in votes[pos]:
                            if pos == option-1:
                                return await interaction.response.send_message(f"You already {'voted for' if poll else 'chose'} this option!", ephemeral=True)
                            else:
                                votes[pos].remove(interaction.user.id)

                    votes[option-1].append(interaction.user.id)

                    embed = interaction.message.embeds[0]

                    new_embed = discord.Embed(title=embed.title, description=embed.description, color=embed.color)
                    new_embed.set_footer(text=embed.footer.text, icon_url=embed.footer.icon_url)
                    if embed.thumbnail:
                        new_embed.set_thumbnail(url=embed.thumbnail.url)

                    for pos, field in enumerate(embed.fields):
                        new_name = field.name[:-self.find_counter_start(field.name)] + f"`[{str(len(votes[pos]))} " + (f"vote{'s' if len(votes[pos]) != 1 else ''}" if poll else f"{'people' if len(votes[pos]) != 1 else 'person'}") + "]`"
                        if len(votes[pos]) <= 5:
                            value = "\n".join([f"<@{v}>" for v in votes[pos]]) if votes[pos] else ("No votes" if poll else "No takers")
                        else:
                            value = "\n".join([f"<@{v}>" for v in votes[pos]][:5]) + f"\n*+ {len(votes[pos])-5} more...*"
                        new_embed.add_field(name=new_name, value=value, inline=False)

                    await interaction.response.edit_message(embed=new_embed)

                elif action == "close":
                    if interaction.user.id == int(poll_creator):
                        # Create a piechart with the results
                        colours = ["#6aaae8", "#84ae62", "#a58fd0", "#e69639"]
                        piechart = self._create_piechart([[field.name[:-self.find_counter_start(field.name)][3:], 0 if field.value == "No votes" else len(field.value.split("\n")), colours[pos]] for pos, field in enumerate(interaction.message.embeds[0].fields)], 
                        interaction.message.embeds[0].description)

                        new_embed = discord.Embed(title=interaction.message.embeds[0].title + " [closed]", description=interaction.message.embeds[0].description, color=interaction.message.embeds[0].color)
                        new_embed.set_image(url="attachment://piechart.png")

                        colour_emotes = ["\U0001f535", "\U0001f7e2", "\U0001f7e3", "\U0001f7e0"]
                        for pos, field in enumerate(interaction.message.embeds[0].fields):
                            new_embed.add_field(name=field.name + f" {colour_emotes[pos]}", value=field.value, inline=False)

                        new_view = discord.ui.View()
                        for button in interaction.message.components[0].children:
                            new_button = discord.ui.Button(label=button.label, style=button.style, disabled=True)
                            new_view.add_item(new_button)

                        await interaction.message.delete()
                        await interaction.response.send_message(embed=new_embed, file=piechart, view=new_view)
                    else:
                        await interaction.response.send_message("Only the polll author can close this poll!", ephemeral=True)

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
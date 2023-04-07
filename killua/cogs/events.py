import io, re
import sys
import discord

import logging
import traceback
from datetime import datetime
from discord.ext import commands, tasks
from PIL import Image
from typing import Dict, List, Tuple
from matplotlib import pyplot as plt

from killua.bot import BaseBot
from killua.utils.classes import Guild, Book, User
from killua.static.enums import PrintColors
from killua.static.constants import TOPGG_TOKEN, DBL_TOKEN, PatreonBanner, DB, GUILD, MAX_VOTES_DISPLAYED

class Events(commands.Cog):

    def __init__(self, client: BaseBot):
        self.client = client
        self.skipped_first = False
        self.status_started = False
        self.log_channel_id = 718818548524384310

    @property
    def old_commands(self) -> List[str]:
        return self._get_old_commands()

    @property
    def log_channel(self):
        return self.client.get_guild(GUILD).get_channel(self.log_channel_id)

    async def _post_guild_count(self) -> None:
        """Posts relevant stats to the botlists Killua is on"""
        data = { # The data for discordbotlist
            "guilds": len(self.client.guilds)
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
        self.save_guilds.start()
        self.vote_reminders.start()
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

    # @status.before_loop
    # async def before_status(self):
    #     await self.client.wait_until_ready()

    def _date_helper(self, hour: int) -> int:
        if hour > 11:
            return hour - 12
        return hour

    @tasks.loop(minutes=1)
    async def vote_reminders(self):
        enabled = DB.teams.find({"voting_reminder": True})
        for user in enabled:
            user = User(user["id"])
            for site, data in  user.voting_streak.items():
                if not data["last_vote"]:
                    continue
                if self._date_helper(data["last_vote"].hour) == self._date_helper(datetime.now().hour) and \
                    data["last_vote"].minute == datetime.now().minute and \
                        not (int(int(datetime.now().timestamp())/60) == int(int(data["last_vote"].timestamp())/60)): # If they are the same amounts of minutes away from the unix epoch
                        
                    user = self.client.get_user(user.id) or await self.client.fetch_user(user.id)
                    if not user:
                        continue
                    embed = discord.Embed.from_dict({
                        "title": "Vote Reminder",
                        "description": f"Hey {user.name}, you voted the last time <t:{int(data['last_vote'].timestamp())}:R> for Killua on __{site}__. Please consider voting for Killua so you can get your daily rewards and help the bot grow and keep your voting streak 🔥 going! You can toggle these reminders with `/dev voteremind`",
                        "color": 0x3e4a78
                    })
                    view = discord.ui.View()
                    if site == "topgg":
                        view.add_item(discord.ui.Button(label="Vote on top.gg", url=f"https://top.gg/bot/{self.client.user.id}/vote", style=discord.ButtonStyle.link))
                    elif site == "discordbotlist":
                        view.add_item(discord.ui.Button(label="Vote on discordbotlist", url=f"https://discordbotlist.com/bots/killua/upvote", style=discord.ButtonStyle.link))

                    try:
                        await user.send(embed=embed, view=view)
                    except discord.Forbidden:
                        continue

    @tasks.loop(hours=24)
    async def save_guilds(self):
        from killua.static.constants import daily_users

        if not self.client.is_dev and self.skipped_first:
            DB.const.update_one({"_id": "growth"}, {"$push": {"growth": {"date": datetime.now() ,"guilds": len(self.client.guilds), "users": len(self.client.users), "registered_users": DB.teams.count_documents({}), "daily_users": len(daily_users.users)}}})
            daily_users.users = [] # Resetting the daily users list lgtm [py/unused-local-variable]
        elif not self.skipped_first: # We want to avoid saving data each time the bot restarts, start 24h after one
            self.skipped_first = True

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        #Changing the status
        await self.client.update_presence()
        Guild.add_default(guild.id)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
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
                "color": 0x3e4a78,
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
                # for component in interaction.message.components[0].children:
                #     print("Before: ", component.custom_id)

                if interaction.data["custom_id"].split(":")[2].isdigit(): # Backwards compatability
                    split = interaction.data["custom_id"].split(":")
                    _p = split[0]
                    action = split[1]
                    opt_votes = ""
                else: 
                    split = interaction.data["custom_id"].split(":")
                    _p = split[0]
                    action = split[1]
                    opt_votes = split[2]

                poll = _p == "poll" # As the logic for polls and wyr overlaps we can use the same code for both, just need to differentiate for a few small things

                guild = Guild(interaction.guild_id)
                saved = guild.is_premium and poll
            
                if saved:
                    author = guild.polls[str(interaction.message.id)]["author"]
                else:
                    author = interaction.message.components[0].children[-1].custom_id.split(":")[2]

                if action.startswith("opt"):

                    if self.client._encrypt(interaction.user.id, smallest=False) == author or str(author).isdigit() and interaction.user.id == int(author):
                        return await interaction.response.send_message("You cannot vote in your own poll!", ephemeral=True)

                    option = int(action.split("-")[1]) if poll else {"a": 1, "b": 2}[action.split("-")[1]]
                    
                    if not saved: # Determines votes etc from custom ids
                        votes: Dict[int, Tuple[list, list]] = {}

                        old_close = interaction.message.components[0].children[-1].custom_id # as this value is modified in the loop the original value needs to be saved to check it
                        for pos, field in enumerate(interaction.message.embeds[0].fields):
                            child = interaction.message.components[0].children[pos]
                            votes[pos] = [int(v.replace("<@", "").replace(">", "")) for v in field.value.split("\n") if re.match(r"<@!?([0-9]+)>", v)], [v for v in child.custom_id.split(":")[2].split(",") if v != ""] if not child.custom_id.split(":")[2].isdigit() else []
                            encrypted = self.client._encrypt(interaction.user.id)
                            
                            if (interaction.user.id in votes[pos][0] or encrypted in votes[pos][1] or re.findall(rf";{pos+1};[^;:]*{encrypted}(.*?)[;:]", old_close)) and pos == option-1:
                                return await interaction.response.send_message(f"You already {'voted for' if poll else 'chose'} this option!", ephemeral=True)

                            if interaction.user.id in votes[pos][0]:
                                votes[pos][0].remove(interaction.user.id)
                            elif encrypted in votes[pos][1] or encrypted in interaction.message.components[0].children[-1].custom_id:
                                # find component and remove the vote
                                for component in interaction.message.components[0].children:
                                            
                                    if not (encrypted in component.custom_id):
                                        continue

                                    component.custom_id = re.sub(rf"{encrypted},?", "", component.custom_id)
                                            
                                    if encrypted in votes[pos][1]: # Strange that I have to put this check in here again but it sometimes fails without it
                                        votes[pos][1].remove(encrypted)

                        if len(votes[option-1][0]) < MAX_VOTES_DISPLAYED:
                            votes[option-1][0].append(interaction.user.id)
                        elif len(interaction.data["custom_id"] + encrypted) <= 100:
                            votes[option-1][1].append(encrypted)
                            interaction.message.components[0].children[option-1].custom_id = _p + ":" + action + ":" + opt_votes + ("," if opt_votes else "") + encrypted
                        elif len(interaction.message.components[0].children[-1].custom_id) + len(encrypted) + (0 if str(option) in interaction.message.components[0].children[-1].custom_id else 2) <= 100 and poll:
                            # using regex it will find a free space after ;{option}; to put it in
                            # first finding the current thing after ;{option};
                            found = re.findall(rf";{option};([^;:]*)", interaction.message.components[0].children[-1].custom_id)
                            if not found: # If the option has not been added yet
                                custom_id = interaction.message.components[0].children[-1].custom_id.split(":")
                                interaction.message.components[0].children[-1].custom_id = custom_id[0] + ":" + custom_id[1] + ":" + custom_id[2] + ":" + custom_id[3] + "" + f";{option};{encrypted}" + ":"
                            else:
                                if len(found[0]) > 0: # If other users have voted for this option
                                    found_items = str(found[0]).split(",")
                                    found_items.append(encrypted)
                                    interaction.message.components[0].children[-1].custom_id = interaction.message.components[0].children[-1].custom_id.replace(str(found[0]), ",".join(found_items))
                                else: # If the number exists but with no votes
                                    interaction.message.components[0].children[-1].custom_id = interaction.message.components[0].children[-1].custom_id.replace(f";{option};",f";{option};{encrypted}")
                        else:
                            view = discord.ui.View()
                            view.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="Get Premium", url="https://patreon.com/kilealkuri"))
                            if poll:
                                return await interaction.response.send_message(f"The maximum votes on this {'poll' if poll else 'wyr'} has been reached! Make this a premium server to allow more votes! Please that votes started before becomind a premium server will still not be able to recieve more votes.", ephemeral=True, view=view)
                            else:
                                return await interaction.response.send_message(f"The maximum votes on this {'poll' if poll else 'wyr'} has been reached!", ephemeral=True)
                    else:
                        votes: Dict[int, list] = guild.polls[str(interaction.message.id)]["votes"]

                        for pos, field in enumerate(interaction.message.embeds[0].fields):
                            if interaction.user.id in votes[str(pos)] and pos == option-1:
                                return await interaction.response.send_message(f"You already {'voted for' if poll else 'chose'} this option!", ephemeral=True)

                            if interaction.user.id in votes[str(pos)]:
                                votes[str(pos)].remove(interaction.user.id)

                        votes[str(option-1)].append(interaction.user.id)

                        guild.update_poll_votes(interaction.message.id, votes)

                    embed = interaction.message.embeds[0]

                    new_embed = discord.Embed(title=embed.title, description=embed.description, color=embed.color)
                    new_embed.set_footer(text=embed.footer.text, icon_url=embed.footer.icon_url)
                    if embed.thumbnail:
                        new_embed.set_thumbnail(url=embed.thumbnail.url)

                    for pos, field in enumerate(embed.fields):
                        if not saved: # Calculate poll votes if it is not saved
                            close_votes = re.findall(rf";{pos+1};(.*?)[;:]", interaction.message.components[0].children[-1].custom_id)
                            num_of_votes = len(votes[pos][0]) + len(votes[pos][1]) + (len([f for f in str(close_votes[0]).split(",") if f != ""]) if close_votes else 0)
                            new_name = field.name[:-self.find_counter_start(field.name)] + f"`[{num_of_votes} " + (f"vote{'s' if num_of_votes != 1 else ''}" if poll else f"{'people' if num_of_votes != 1 else 'person'}") + "]`"
                            if not votes[pos][1]:
                                value = "\n".join([f"<@{v}>" for v in votes[pos][0]]) if votes[pos][0] else ("No votes" if poll else "No takers")
                            else:
                                cancel_votes = re.findall(rf";{option};([^;:]*)", interaction.message.components[0].children[-1].custom_id)
                                additional_votes = len(votes[pos][1]) + (len(cancel_votes[0].split(",")) if cancel_votes else 0)
                                value = "\n".join([f"<@{v}>" for v in votes[pos][0]]) + f"\n*+ {additional_votes} more...*"
                        else:
                            num_of_votes = len(votes[str(pos)])
                            new_name = field.name[:-self.find_counter_start(field.name)] + f"`[{num_of_votes} " + (f"vote{'s' if num_of_votes != 1 else ''}" if poll else f"{'people' if num_of_votes != 1 else 'person'}") + "]`"
                            if len(votes[str(pos)]) > MAX_VOTES_DISPLAYED:
                                value = "\n".join([f"<@{v}>" for v in votes[str(pos)][:MAX_VOTES_DISPLAYED]]) + f"\n*+ {len(votes[str(pos)])-MAX_VOTES_DISPLAYED} more...*"
                            else:
                                value = "\n".join([f"<@{v}>" for v in votes[str(pos)]]) if votes[str(pos)] else ("No votes" if poll else "No takers")
                        new_embed.add_field(name=new_name, value=value, inline=False)

                    # for component in interaction.message.components[0].children:
                    #     print("After: ", component.custom_id)

                    new_view = discord.ui.View()

                    for component in interaction.message.components[0].children:
                        d = component.to_dict()
                        del d["type"]
                        d["style"] = discord.ButtonStyle(d["style"])
                        new_view.add_item(discord.ui.Button(**d))
                    await interaction.response.edit_message(embed=new_embed, view=new_view)

                elif action == "close":
                    # poll_creator = interaction.message.components[0].children[-1].custom_id.split(":")[2]
                    if not (self.client._encrypt(interaction.user.id, smallest=False) == author or str(author).isdigit() and interaction.user.id == int(author)):
                        return await interaction.response.send_message("Only the polll author can close this poll!", ephemeral=True)

                    # Create a piechart with the results
                    colours = ["#6aaae8", "#84ae62", "#a58fd0", "#e69639"]
                    if not saved:
                        data = [
                            [
                                f"Option {pos+1}", # Calculate the number of votes for each option
                                0 if field.value == "No votes" else len(field.value.split("\n")) + \
                                    len(interaction.message.components[0].children[pos].custom_id.split(":")[2].split(",")) - \
                                        1 if len(field.value.split("\n")) > MAX_VOTES_DISPLAYED else 0 + \
                                            + (len(str(close_votes[0]).split(",")) if (close_votes := re.findall(rf";{pos};[^;:]*", interaction.message.components[0].children[-1].custom_id)) else 0), 
                                colours[pos]
                            ] 
                            for pos, field in enumerate(interaction.message.embeds[0].fields)
                        ]
                    else:
                        votes: Dict[int, list] = guild.polls[str(interaction.message.id)]["votes"]
                        data = [
                            [
                                f"Option {pos+1}",
                                len(votes[str(pos)]),
                                colours[pos]
                            ]
                            for pos, _ in enumerate(interaction.message.embeds[0].fields)
                        ]

                    if not data:
                        return await interaction.response.send_message("There are no votes for this poll!", ephemeral=True)

                    piechart = self._create_piechart(data, interaction.message.embeds[0].description)

                    new_embed = discord.Embed(title=interaction.message.embeds[0].title + " [closed]", description=interaction.message.embeds[0].description, color=interaction.message.embeds[0].color)
                    new_embed.set_image(url="attachment://piechart.png")

                    colour_emotes = ["\U0001f535", "\U0001f7e2", "\U0001f7e3", "\U0001f7e0"]
                    for pos, field in enumerate(interaction.message.embeds[0].fields):
                        new_embed.add_field(name=field.name + f" {colour_emotes[pos]}", value=field.value, inline=False)

                    new_view = discord.ui.View()
                    for button in interaction.message.components[0].children:
                        new_button = discord.ui.Button(label=button.label, style=button.style, disabled=True)
                        new_view.add_item(new_button)

                    if saved:
                        guild.close_poll(str(interaction.message.id))

                    await interaction.message.delete()
                    await interaction.response.send_message(embed=new_embed, file=piechart, view=new_view)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error):

        if ctx.channel.permissions_for(ctx.me).send_messages is False and not self.client.is_dev: # we don't want to raise an error inside the error handler when Killua ' send the error because that does not trigger `on_command_error`
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

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Report bug", url=self.client.support_server_invite))
        await ctx.send(":x: an unexpected error occured. If this should keep happening, please report it by clicking on the button and using `/report` in the support server.", view=view)


Cog = Events
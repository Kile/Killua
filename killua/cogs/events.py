import io, re
import sys
import discord

import logging
import traceback
from asyncio import sleep
from datetime import datetime
from discord.ext import commands, tasks
from PIL import Image
from enum import Enum
from typing import Dict, List, Tuple, Optional, cast
from matplotlib import pyplot as plt
from pymongo.errors import ServerSelectionTimeoutError

from killua.metrics import DAILY_ACTIVE_USERS
from killua.bot import BaseBot
from killua.utils.classes import Guild, Book, User, Card
from killua.static.enums import PrintColors
from killua.static.constants import (
    TOPGG_TOKEN,
    DBL_TOKEN,
    PatreonBanner,
    DB,
    GUILD,
    MAX_VOTES_DISPLAYED,
    CONST_DEFAULT,
)


class SaveType(Enum):
    """
    The 3 types of saving a poll vote
    """

    EmbedDescription = 1
    DesignatedButton = 2
    CloseButton = 3


class Events(commands.Cog):

    def __init__(self, client: BaseBot):
        self.client = client
        self.skipped_first = False
        self.status_started = False
        self.log_channel_id = 718818548524384310

    @property
    def log_channel(self):
        return self.client.get_guild(GUILD).get_channel(self.log_channel_id)

    async def _initialize_card_json(self, retry_timeout=5) -> None:
        """Initializes the card json"""
        status = None
        while status != 200:
            result = await self.client.session.get(
                self.client.api_url(to_fetch=False, is_for_cards=True)
                + "/cards.json"
                + ("?public=true" if self.client.is_dev else ""),
                headers={"Authorization": self.client.secret_api_key},
            )
            status = result.status
            if result.status != 200:
                retry_timeout *= 2
                logging.warning(
                    f"{PrintColors.WARNING}Failed to fetch cards with status code: {result.status}. Will try again in {retry_timeout}s...{PrintColors.ENDC}"
                )
                # If the status code is not 200, wait for a bit and try again
                await sleep(retry_timeout)
            else:
                cards = await result.json()
                Card.raw = cards
                logging.info(
                    PrintColors.OKGREEN
                    + "Successfully fetched and cached cards from "
                    + ("local" if self.client.force_local else "remote")
                    + " using the "
                    + (
                        "public (censored)"
                        if self.client.is_dev
                        else "secret (uncensored)"
                    )
                    + " version"
                    + PrintColors.ENDC
                )
                self.client.dispatch(
                    "cards_loaded"
                )  # Dispatches the event that the cards are loaded

    async def _post_guild_count(self) -> None:
        """Posts relevant stats to the botlists Killua is on"""
        await self.client.session.post(
            f"https://discordbotlist.com/api/v1/bots/756206646396452975/stats",
            headers={"Authorization": DBL_TOKEN},
            data={"guilds": len(self.client.guilds)},
        )
        await self.client.session.post(
            f"https://top.gg/api/bots/756206646396452975/stats",
            headers={"Authorization": "Bearer " + TOPGG_TOKEN},
            data={"server_count": len(self.client.guilds)},
        )

    async def _load_cards_cache(self) -> None:
        """Downloads all the card images so the image manipulation is fairly fast"""

        if len(Card.raw) == 0:
            return logging.error(
                f"{PrintColors.WARNING}No cards cached, could not load image cache{PrintColors.ENDC}"
            )

        token, expiry = self.client.sha256_for_api("all_cards", 180)
        logging.info(
            f"{PrintColors.OKGREEN}Created token to load cards cache{PrintColors.ENDC}"
        )

        logging.info(f"{PrintColors.WARNING}Loading cards cache....{PrintColors.ENDC}")
        percentages = [25, 50, 75]
        for p, item in enumerate(Card.raw):
            try:
                if item["id"] in Book.card_cache:
                    continue  # in case the event fires multiple times this avoids using unnecessary cpu power

                res = await self.client.session.get(
                    self.client.api_url(to_fetch=True)
                    + item["image"]
                    + f"?token={token}&expiry={expiry}"
                )
                image_bytes = await res.read()
                image_card = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
                image_card = image_card.resize((84, 115), Image.LANCZOS)

                Book.card_cache[str(item["_id"])] = image_card
                if len(percentages) >= 1 and (p / len(Card.raw)) * 100 > (
                    percent := percentages[0]
                ):
                    logging.info(
                        f"{PrintColors.WARNING}Cache loaded {percent}%...{PrintColors.ENDC}"
                    )
                    percentages.remove(percent)
            except Exception as e:
                logging.error(
                    f"{PrintColors.FAIL}Failed to load card {item['_id']} with error: {e}{PrintColors.ENDC}"
                )

        logging.info(
            f"{PrintColors.OKGREEN}All cards successfully cached{PrintColors.ENDC}"
        )

    async def _set_patreon_banner(self) -> None:
        """Loads the patron banner bytes so it can be quickly sent when needed"""
        res = await self.client.session.get(PatreonBanner.URL)
        image_bytes = await res.read()
        PatreonBanner.VALUE = image_bytes
        logging.info(
            f"{PrintColors.OKGREEN}Successfully loaded patreon banner{PrintColors.ENDC}"
        )

    async def _insert_const_to_db(self) -> None:
        """If it doesn't exist, insert some constants into the db"""
        # Check if the constants are already in the db
        made_changes = False
        _all = await DB.const.find({}).to_list(length=None)
        for value in CONST_DEFAULT:
            if not any([value["_id"] == x["_id"] for x in _all]):
                made_changes = True
                await DB.const.insert_one(value)
                logging.info(
                    f"{PrintColors.OKGREEN}Inserted constant {value['_id']} into the db because it previously did not exist{PrintColors.ENDC}"
                )
        if not made_changes:
            logging.info(
                f"{PrintColors.OKGREEN}All constants are already in the db, no need for extra inserts{PrintColors.ENDC}"
            )

    def print_dev_text(self) -> None:
        logging.info(
            f"{PrintColors.OKGREEN}Running bot in dev enviroment...{PrintColors.ENDC}"
        )

    async def cog_load(self):
        await self._insert_const_to_db()
        await self._set_patreon_banner()
        if self.client.is_dev:
            self.print_dev_text()
        else:
            await self._post_guild_count()

    @commands.Cog.listener()
    async def on_card_cache_loaded(self):
        if not self.client.is_dev:
            await self._load_cards_cache()

    @commands.Cog.listener()
    async def on_ready(self):
        if len(Card.raw) == 0:
            await self._initialize_card_json()
        if not self.save_guilds.is_running() and not self.client.is_dev:
            self.save_guilds.start()
        if not self.vote_reminders.is_running():
            self.vote_reminders.start()
        if not self.status_started:
            if not self.status.is_running():
                self.status.start()
            self.status_started = True

        logging.info(
            PrintColors.OKGREEN
            + "Logged in as: "
            + self.client.user.name
            + f" (ID: {self.client.user.id}). "
            + f"Highest command ID is: "
            + str(
                sorted(
                    self.client.get_raw_formatted_commands(),
                    key=lambda x: x.extras["id"],
                )[-1].extras["id"]
            )
            + PrintColors.ENDC
        )

    @tasks.loop(hours=12)
    async def status(self):
        await self.client.update_presence()  # For some reason this does not work in cog_load because it always fires before the bot is connected and
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
        try:
            enabled = DB.teams.find({"voting_reminder": True})
            async for user in enabled:
                user = await User.new(user["id"])
                for site, data in user.voting_streak.items():
                    if not data["last_vote"]:
                        continue
                    if (
                        self._date_helper(data["last_vote"].hour)
                        == self._date_helper(datetime.now().hour)
                        and cast(datetime, data["last_vote"]).minute
                        == datetime.now().minute
                        and not (
                            int(int(datetime.now().timestamp()) / 60)
                            == int(
                                int(cast(datetime, data["last_vote"]).timestamp()) / 60
                            )
                        )
                    ):  # If they are the same amounts of minutes away from the unix epoch

                        user = self.client.get_user(
                            user.id
                        ) or await self.client.fetch_user(user.id)
                        if not user:
                            continue
                        embed = discord.Embed.from_dict(
                            {
                                "title": "Vote Reminder",
                                "description": f"Hey {user.display_name}, you voted the last time <t:{int(data['last_vote'].timestamp())}:R> for Killua on __{site}__. Please consider voting for Killua so you can get your daily rewards and help the bot grow and keep your voting streak 🔥 going! You can toggle these reminders with `/dev voteremind`",
                                "color": 0x3E4A78,
                            }
                        )
                        view = discord.ui.View()
                        if site == "topgg":
                            view.add_item(
                                discord.ui.Button(
                                    label="Vote on top.gg",
                                    url=f"https://top.gg/bot/{self.client.user.id}/vote",
                                    style=discord.ButtonStyle.link,
                                )
                            )
                        elif site == "discordbotlist":
                            view.add_item(
                                discord.ui.Button(
                                    label="Vote on discordbotlist",
                                    url=f"https://discordbotlist.com/bots/killua/upvote",
                                    style=discord.ButtonStyle.link,
                                )
                            )

                        try:
                            await user.send(embed=embed, view=view)
                        except discord.Forbidden:
                            continue
        except ServerSelectionTimeoutError:
            return logging.warning(
                f"{PrintColors.WARNING}Could not send vote reminders because the database is not available{PrintColors.ENDC}"
            )

    @tasks.loop(hours=24)
    async def save_guilds(self):
        from killua.static.constants import daily_users

        # Arguably this is a much better way of doing this as otherwise
        # if the bot restarts this will be ignored for a day.
        # While that's true, this could lead to daily users being
        # 0 if it just ran after 24hrs since it is only saved during
        # runtime. I don't want this so I will keep it as it is.
        #
        # Check when the last stats were saved
        # last = await DB.const.find_one({"_id": "growth"})
        # if not last:
        #     return
        # last = last["growth"][-1]["date"]

        # If it has been more than 24 hours since the last save
        if self.skipped_first:
            approx_users = await self.client.get_approximate_user_count()
            approximate_user_install_count = (
                await self.client.application_info()
            ).approximate_user_install_count
            logging.info(PrintColors.OKBLUE + "Saving stats:")
            logging.info(
                "Guilds: {} | Users: {} | Registered Users: {} | Daily Users: {} | Approximate Users: {} | User Installs: {}{}".format(
                    len(self.client.guilds),
                    len(self.client.users),
                    await DB.teams.count_documents({}),
                    len(daily_users.users),
                    approx_users,
                    approximate_user_install_count,
                    PrintColors.ENDC,
                )
            )
            await DB.const.update_one(
                {"_id": "growth"},
                {
                    "$push": {
                        "growth": {
                            "date": datetime.now(),
                            "guilds": len(self.client.guilds),
                            "users": len(self.client.users),
                            "registered_users": await DB.teams.count_documents({}),
                            "daily_users": len(daily_users.users),
                            "approximate_users": approx_users,
                            "user_installs": approximate_user_install_count,
                        }
                    }
                },
            )
            if self.client.run_in_docker:
                DAILY_ACTIVE_USERS.set(len(daily_users.users))
            daily_users.users = []  # Resetting the daily users list
        else:  # We want to avoid saving data each time the bot restarts, start 24h after one
            self.skipped_first = True

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        # Changing the status
        if (
            len(self.client.guilds) % 7 == 0
        ):  # Different number than on_guild_remove so if someone keeps re-adding the bot it doesn't spam the status
            await self.client.update_presence()
        await Guild.add_default(guild.id, guild.member_count)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        # Changing Killua's status
        if len(self.client.guilds) % 10 == 0:
            await self.client.update_presence()
        await (await Guild.new(guild.id)).delete()
        await self._post_guild_count()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        # Welcomes new member
        if (
            not self.client.is_dev and member.guild.id == GUILD
        ):  # In theory it would be cool if the dev bot welcomed you but it just isn't always online
            embed = discord.Embed.from_dict(
                {
                    "title": "Welcome to the Killua support server a.k.a. Kile's dev!",
                    "description": "You joined. What now?\n\n**Where to go**\n"
                    + "┗ <#1019657047568035841> to receive help or report bugs\n"
                    + "┗ <#787819439596896288> To get some ping roles\n"
                    + "┗ <#886546434663538728> Good place to check before asking questions\n"
                    + "┗ <#754063177553150002> To see newest announcements\n"
                    + "┗ <#757170264294424646> Read up on the newest Killua updates\n"
                    + "┗ <#716357592493981707> Use bots in here\n"
                    + "┗ <#811903366925516821> Check if there is any known outage/bug\n\n"
                    + "Thanks for joining and don't forget to vote for Killua! :)",
                    "color": 0x3E4A78,
                }
            )
            embed.set_thumbnail(
                url=self.client.user.avatar.url if self.client.user else None
            )
            embed.timestamp = datetime.now()

            await self.log_channel.send(content=member.mention, embed=embed)
            # try:
            #     await member.send(embed=embed)
            # except discord.Forbidden:
            #     pass

    def _create_piechart(self, data: List[list], title: str) -> discord.File:
        """Creates a piechart with the given data"""
        data = [l for l in data if l[1] > 0]  # We want to avoid a 0% slice

        labels = [x[0] for x in data]
        values = [x[1] for x in data]
        colours = [x[2] for x in data]
        buffer = io.BytesIO()
        plt.pie(
            values,
            labels=labels,
            autopct="%1.1f%%",
            shadow=True,
            textprops={"color": "w"},
            colors=colours,
        )
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
            if char == "`" and revers[i - 1] == "[":
                return i + 1

    async def _end_poll(
        self, interaction: discord.Interaction, guild: Guild, author: int, saved: bool
    ) -> None:
        """
        Ends a poll (option not on wyr)
        """

        # Create a piechart with the results
        colours = ["#6aaae8", "#84ae62", "#a58fd0", "#e69639"]
        if not saved:
            data = [
                [
                    f"Option {pos+1}",  # Calculate the number of votes for each option
                    (
                        0
                        if field.value == "No votes"
                        else (
                            len(field.value.split("\n"))
                            + len(
                                interaction.message.components[0]
                                .children[pos]
                                .custom_id.split(":")[2]
                                .split(",")
                            )
                            - 1
                            if len(field.value.split("\n")) > MAX_VOTES_DISPLAYED
                            else 0
                            + +(
                                len(str(close_votes[0]).split(","))
                                if (
                                    close_votes := re.findall(
                                        rf";{pos};[^;:]*",
                                        interaction.message.components[0]
                                        .children[-1]
                                        .custom_id,
                                    )
                                )
                                else 0
                            )
                        )
                    ),
                    colours[pos],
                ]
                for pos, field in enumerate(interaction.message.embeds[0].fields)
            ]
        else:
            votes: Dict[int, list] = guild.polls[str(interaction.message.id)]["votes"]
            data = [
                [f"Option {pos+1}", len(votes[str(pos)]), colours[pos]]
                for pos, _ in enumerate(interaction.message.embeds[0].fields)
            ]

        if not data:
            return await interaction.response.send_message(
                "There are no votes for this poll!", ephemeral=True
            )

        piechart = self._create_piechart(
            data, interaction.message.embeds[0].description
        )

        new_embed = discord.Embed(
            title=interaction.message.embeds[0].title + " [closed]",
            description=interaction.message.embeds[0].description,
            color=interaction.message.embeds[0].color,
        )
        new_embed.set_image(url="attachment://piechart.png")

        colour_emotes = [
            "\U0001f535",
            "\U0001f7e2",
            "\U0001f7e3",
            "\U0001f7e0",
        ]
        for pos, field in enumerate(interaction.message.embeds[0].fields):
            new_embed.add_field(
                name=field.name + f" {colour_emotes[pos]}",
                value=field.value,
                inline=False,
            )

        new_view = discord.ui.View()
        for button in interaction.message.components[0].children:
            new_button = discord.ui.Button(
                label=button.label, style=button.style, disabled=True
            )
            new_view.add_item(new_button)

        if saved:
            await guild.close_poll(str(interaction.message.id))

        await interaction.message.delete()
        await interaction.response.send_message(
            embed=new_embed, file=piechart, view=new_view
        )

    def _insert_vote_in_close_button(
        self, interaction: discord.Interaction, option: int, encrypted: str
    ) -> str:
        """
        Inserts a vote into the close button custom id.

        The ID of the custom ID would look something like this:

        ```txt
                          Any extra option
                          (not necessarily
                          opt-1, any order)
                                 |
                defines it to be |     Another option
                the close button |   (any order, may not
                       |         |       be present)
                       |         |           |
                poll:close:afhua:1;q3uf,uzfv;3;ioqfnq
                  |         |          |           |
            marks this as   |     who voted that   |
            a poll          |   option (compressed,|
                            |   separated by comma)|
                            |                      |
                      full compressed      Votes for that other
                      ID of the author        option (if any),
                                          same format as before
        ```
        """
        # using regex it will find a free space after ;{option}; to put it in
        # first finding the current thing after ;{option};
        found = re.findall(
            rf";{option};([^;:]*)",
            interaction.message.components[0].children[-1].custom_id,
        )
        if not found:  # If the option has not been added yet
            custom_id = (
                interaction.message.components[0].children[-1].custom_id.split(":")
            )
            interaction.message.components[0].children[-1].custom_id = (
                custom_id[0]
                + ":"
                + custom_id[1]
                + ":"
                + custom_id[2]
                + ":"
                + custom_id[3]
                + ""
                + f";{option};{encrypted}"
                + ":"
            )
        else:
            if len(found[0]) > 0:  # If other users have voted for this option
                found_items = str(found[0]).split(",")
                found_items.append(encrypted)
                interaction.message.components[0].children[-1].custom_id = (
                    interaction.message.components[0]
                    .children[-1]
                    .custom_id.replace(str(found[0]), ",".join(found_items))
                )
            else:  # If the number exists but with no votes
                interaction.message.components[0].children[-1].custom_id = (
                    interaction.message.components[0]
                    .children[-1]
                    .custom_id.replace(f";{option};", f";{option};{encrypted}")
                )

    def _parse_votes_for(
        self, custom_id: str, field: "discord.embeds._EmbedFieldProxy"
    ) -> Tuple[List[int], List[str]]:
        """
        Parses the votes for a poll or wyr
        """
        return (
            [
                int(v.replace("<@", "").replace(">", ""))
                for v in field.value.split("\n")
                if re.match(r"<@!?(\d+)>", v)
            ],
            (
                [v for v in custom_id.split(":")[2].split(",") if v != ""]
                if len(custom_id.split(":")) > 2
                else []
            ),
        )

    def _is_room(
        self,
        where: SaveType,
        interaction: discord.Interaction,
        votes: Dict[int, Tuple[List[int], List[str]]],
        option: int,
        encrypted: str,
        poll: bool = None,
    ) -> bool:
        """
        Checks if there is room for a vote in the UI
        """
        if where == SaveType.EmbedDescription:
            return len(votes[option - 1][0]) < MAX_VOTES_DISPLAYED
        elif where == SaveType.DesignatedButton:
            return len(interaction.data["custom_id"] + encrypted) <= 100
        elif where == SaveType.CloseButton:
            # length of the close button custom ID + length of the encrypted vote +
            # 2 for the comma and the option number
            return (
                len(interaction.message.components[0].children[-1].custom_id)
                + len(encrypted)
                + (
                    0
                    if str(option)
                    in interaction.message.components[0].children[-1].custom_id
                    else 2
                )
                <= 100
                and poll
            )

    async def _process_vote_with_compression(
        self,
        interaction: discord.Interaction,
        option: int,
        action: str,
        poll: bool,
        opt_votes: str,
    ) -> Optional[Dict[int, Tuple[List[int], List[str]]]]:
        """
        If a None is returned, an error was sent and the execution should stop.
        Else the votes are returned.
        """
        votes: Dict[int, Tuple[List[int], List[str]]] = {}
        # This took me a bit to figure out when revisiting this
        # code. What is actually being stored here for each option
        # is:
        #
        # votes = {
        #     0: ( # Option 1
        #           [
        #             # int: Votes for option 1, displayed in the UI
        #             # IDs because it is easy to get from the UI where
        #             # they are represented as <@ID>
        #               1234567890,
        #               1234567890,
        #           ],
        #           [
        #             # str: Votes for option 1, not displayed in the UI,
        #             # instead compressed in the button custom ID because
        #             # it is not easy to save in the UI otherwise
        #               "afhua",
        #               "q3uf",
        #               "uzfv"
        #           ]
        #       )
        # }

        old_close = (
            interaction.message.components[0].children[-1].custom_id
        )  # as this value is modified in the loop the original value needs to be saved to check it
        for pos, field in enumerate(interaction.message.embeds[0].fields):
            child = interaction.message.components[0].children[pos]
            votes[pos] = self._parse_votes_for(child.custom_id, field)
            encrypted = self.client._encrypt(interaction.user.id)

            if (
                interaction.user.id in votes[pos][0]
                or encrypted in votes[pos][1]
                or re.findall(rf";{pos+1};[^;:]*{encrypted}(.*?)[;:]", old_close)
            ) and pos == option - 1:
                # Already voted for this option
                return await interaction.response.send_message(
                    f"You already {'voted for' if poll else 'chose'} this option!",
                    ephemeral=True,
                )

            if interaction.user.id in votes[pos][0]:
                votes[pos][0].remove(interaction.user.id)
            elif (
                encrypted in votes[pos][1]
                or encrypted in interaction.message.components[0].children[-1].custom_id
            ):
                # find component and remove the vote if in close button
                for component in interaction.message.components[0].children:

                    if not (encrypted in component.custom_id):
                        continue

                    component.custom_id = re.sub(
                        rf"{encrypted},?", "", component.custom_id
                    )

                    if (
                        encrypted in votes[pos][1]
                    ):  # Strange that I have to put this check in here again but it sometimes fails without it
                        # Update 19/07/2024: Idk if this is still needed but I am too scared to remove it
                        votes[pos][1].remove(encrypted)

        if self._is_room(
            SaveType.EmbedDescription, interaction, votes, option, encrypted
        ):
            # When there is room for more votes in the UI
            # add the vote to the int of votes
            # to update visually
            votes[option - 1][0].append(interaction.user.id)
        elif self._is_room(
            SaveType.DesignatedButton, interaction, votes, option, encrypted
        ):
            # When there is no room in the UI but there is room
            # in the close button custom ID, add the vote to the
            # custom ID to update
            votes[option - 1][1].append(encrypted)
            interaction.message.components[0].children[option - 1].custom_id = (
                ("poll" if poll else "wyr")
                + ":"
                + action
                + ":"
                + opt_votes
                + ("," if opt_votes else "")
                + encrypted
            )
        elif self._is_room(
            SaveType.CloseButton, interaction, votes, option, encrypted, poll
        ):
            # When there is no room in the UI and the designated
            # close button custom ID but there is room in the
            # close button custom ID, add the vote to the custom
            # ID to update
            self._insert_vote_in_close_button(interaction, option, encrypted)
        else:
            # When there is no room in the UI and the designated
            # close button custom ID and there is no room in the
            # close button custom ID, send a message that the
            # poll is full
            view = discord.ui.View()
            view.add_item(
                discord.ui.Button(
                    style=discord.ButtonStyle.link,
                    label="Get Premium",
                    url="https://patreon.com/kilealkuri",
                )
            )
            if poll:
                return await interaction.response.send_message(
                    f"The maximum votes on this {'poll' if poll else 'wyr'} has been reached! Make this a premium server to allow more votes! Please that votes started before becomind a premium server will still not be able to recieve more votes.",
                    ephemeral=True,
                    view=view,
                )
            else:
                return await interaction.response.send_message(
                    f"The maximum votes on this {'poll' if poll else 'wyr'} has been reached!",
                    ephemeral=True,
                )
        return votes

    async def _process_vote_with_db(
        self,
        interaction: discord.Interaction,
        guild: Guild,
        option: int,
        poll: bool,
    ) -> Dict[str, List[int]]:
        """
        If the poll is saved in the database, this function
        processes the vote

        Only available for premium guilds
        """
        votes: Dict[int, List[int]] = guild.polls[str(interaction.message.id)]["votes"]

        for pos, _ in enumerate(interaction.message.embeds[0].fields):
            if interaction.user.id in votes[str(pos)] and pos == option - 1:
                return await interaction.response.send_message(
                    f"You already {'voted for' if poll else 'chose'} this option!",
                    ephemeral=True,
                )

            if interaction.user.id in votes[str(pos)]:
                votes[str(pos)].remove(interaction.user.id)

        votes[str(option - 1)].append(interaction.user.id)

        await guild.update_poll_votes(interaction.message.id, votes)
        return votes

    def _set_new_field_name_for_unsaved(
        self,
        field: "discord.embeds._EmbedFieldProxy",
        votes: Dict[int, Tuple[List[int], List[str]]],
        pos: int,
        interaction: discord.Interaction,
        poll: bool,
        option: int,
    ) -> Tuple[str, str]:
        close_votes = re.findall(
            rf";{pos+1};(.*?)[;:]",
            interaction.message.components[0].children[-1].custom_id,
        )
        num_of_votes = (
            len(votes[pos][0])
            + len(votes[pos][1])
            + (
                len([f for f in str(close_votes[0]).split(",") if f != ""])
                if close_votes
                else 0
            )
        )
        new_name = (
            field.name[: -self.find_counter_start(field.name)]
            + f"`[{num_of_votes} "
            + (
                f"vote{'s' if num_of_votes != 1 else ''}"
                if poll
                else f"{'people' if num_of_votes != 1 else 'person'}"
            )
            + "]`"
        )
        if not votes[pos][1]:
            value = (
                "\n".join([f"<@{v}>" for v in votes[pos][0]])
                if votes[pos][0]
                else ("No votes" if poll else "No takers")
            )
        else:
            cancel_votes = re.findall(
                rf";{option};([^;:]*)",
                interaction.message.components[0].children[-1].custom_id,
            )
            additional_votes = len(votes[pos][1]) + (
                len(cancel_votes[0].split(",")) if cancel_votes else 0
            )
            value = (
                "\n".join([f"<@{v}>" for v in votes[pos][0]])
                + f"\n*+ {additional_votes} more...*"
            )

        return new_name, value

    def _set_new_field_name_for_saved(
        self,
        field: "discord.embeds._EmbedFieldProxy",
        votes: Dict[str, List[int]],
        pos: int,
        poll: bool,
    ) -> Tuple[str, str]:
        num_of_votes = len(votes[str(pos)])
        new_name = (
            field.name[: -self.find_counter_start(field.name)]
            + f"`[{num_of_votes} "
            + (
                f"vote{'s' if num_of_votes != 1 else ''}"
                if poll
                else f"{'people' if num_of_votes != 1 else 'person'}"
            )
            + "]`"
        )
        if len(votes[str(pos)]) > MAX_VOTES_DISPLAYED:
            value = (
                "\n".join([f"<@{v}>" for v in votes[str(pos)][:MAX_VOTES_DISPLAYED]])
                + f"\n*+ {len(votes[str(pos)])-MAX_VOTES_DISPLAYED} more...*"
            )
        else:
            value = (
                "\n".join([f"<@{v}>" for v in votes[str(pos)]])
                if votes[str(pos)]
                else ("No votes" if poll else "No takers")
            )
        return new_name, value

    async def _process_vote(
        self,
        interaction: discord.Interaction,
        guild: Guild,
        action: str,
        saved: bool,
        poll: bool,
        opt_votes: str,
    ) -> None:
        """
        Processes a vote in a poll or wyr
        """

        option = (
            int(action.split("-")[1])
            if poll
            else {"a": 1, "b": 2}[action.split("-")[1]]
        )

        if not saved:  # Determines votes etc from custom ids
            votes = await self._process_vote_with_compression(
                interaction, option, action, poll, opt_votes
            )
        else:
            votes = await self._process_vote_with_db(interaction, guild, option, poll)

        if votes is None:
            return

        embed = interaction.message.embeds[0]

        new_embed = discord.Embed(
            title=embed.title,
            description=embed.description,
            color=embed.color,
        )
        new_embed.set_footer(text=embed.footer.text, icon_url=embed.footer.icon_url)
        if embed.thumbnail:
            new_embed.set_thumbnail(url=embed.thumbnail.url)

        for pos, field in enumerate(embed.fields):
            if not saved:  # Calculate poll votes if it is not saved
                new_name, value = self._set_new_field_name_for_unsaved(
                    field, votes, pos, interaction, poll, option
                )
            else:
                new_name, value = self._set_new_field_name_for_saved(
                    field, votes, pos, poll
                )
            new_embed.add_field(name=new_name, value=value, inline=False)

        new_view = discord.ui.View()

        for component in interaction.message.components[0].children:
            d = component.to_dict()
            del d["type"]
            d["style"] = discord.ButtonStyle(d["style"])
            new_view.add_item(discord.ui.Button(**d))
        await interaction.response.edit_message(embed=new_embed, view=new_view)

    def is_author(self, interaction: discord.Interaction, author: int) -> bool:
        return (
            self.client._encrypt(interaction.user.id, smallest=False) == author
            or str(author).isdigit()
            and interaction.user.id == int(author)
        )

    async def _process_votable(self, interaction: discord.Interaction) -> None:
        """
        Processes a wyr or poll interaction (button click)
        """
        if (
            interaction.data["custom_id"].split(":")[2].isdigit()
        ):  # Backwards compatibility
            split = interaction.data["custom_id"].split(":")
            _p = split[0]
            action = split[1]
            opt_votes = ""
        else:
            split = interaction.data["custom_id"].split(":")
            _p = split[0]
            action = split[1]
            opt_votes = split[2]

        poll = (
            _p == "poll"
        )  # As the logic for polls and wyr overlaps we can use the same code for both, just need to differentiate for a few small things

        guild = await Guild.new(interaction.guild_id)
        saved = guild.is_premium and poll

        if saved:
            author = guild.polls[str(interaction.message.id)]["author"]
        else:
            author = (
                interaction.message.components[0].children[-1].custom_id.split(":")[2]
            )

        if action.startswith("opt"):
            if self.is_author(interaction, author):
                return await interaction.response.send_message(
                    "You cannot vote in your own poll!", ephemeral=True
                )
            await self._process_vote(interaction, guild, action, saved, poll, opt_votes)
        elif action == "close":
            if not self.is_author(interaction, author):
                return await interaction.response.send_message(
                    "Only the poll author can close this poll!", ephemeral=True
                )
            await self._end_poll(interaction, guild, author, saved)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if (
            interaction.type == discord.InteractionType.component
            and interaction.data["custom_id"]
            and (
                interaction.data["custom_id"].startswith("poll:")
                or interaction.data["custom_id"].startswith("wyr:")
            )
        ):
            await self._process_votable(interaction)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error):

        if (
            not self.client.is_user_installed(ctx)
            and ctx.channel.permissions_for(ctx.me).send_messages is False
            and not self.client.is_dev
            and not isinstance(error, discord.Forbidden)
        ):
            # we don't want to raise an error inside the error handler when Killua sends the error message because that does not trigger `on_command_error`
            return

        if ctx.command:
            usage = f"`{(await self.client.command_prefix(self.client, ctx.message))[2]}{(ctx.command.parent.name + ' ') if ctx.command.parent else ''}{ctx.command.usage}`"

        if isinstance(error, commands.BotMissingPermissions):
            return await ctx.send(
                f"I don't have the required permissions to use this command! (`{', '.join(error.missing_permissions)}`)"
            )

        if isinstance(error, commands.MissingPermissions):
            return await ctx.send(
                f"You don't have the required permissions to use this command! (`{', '.join(error.missing_permissions)}`)"
            )

        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send(
                f"Seems like you missed a required argument for this command: `{str(error.param).split(':')[0]}`"
            )

        if isinstance(error, commands.UserInputError):
            return await ctx.send(
                f"Seems like you provided invalid arguments for this command. This is how you use it: {usage}",
                allowed_mentions=discord.AllowedMentions.none(),
            )

        if isinstance(error, commands.NotOwner):
            return await ctx.send(
                "Sorry, but you need to be the bot owner to use this command"
            )

        if isinstance(error, commands.BadArgument):
            return await ctx.send(
                f"Could not process arguments. Here is the command should be used: {usage}",
                allowed_mentions=discord.AllowedMentions.none(),
            )

        if isinstance(error, commands.NoPrivateMessage):
            return await ctx.send("This command can only be used inside of a guild")

        if isinstance(error, commands.CommandNotFound) or isinstance(
            error, commands.CheckFailure
        ):  # I don't care if this happens
            return

        if isinstance(error, discord.HTTPException) and error.code == 200000:
            return await ctx.send(
                "The content of this message was blocked by automod. Please respect the rules of the server.",
                ephemeral=True,
            )

        if self.client.is_dev:  # prints the full traceback in dev enviroment
            # CRITICAL for the dev bot instead of error is because it makes it easier spot
            # errors my code caused and not the library itself
            logging.critical(
                PrintColors.FAIL
                + "Ignoring exception in command {}:".format(ctx.command)
            )
            traceback.print_exception(
                type(error), error, error.__traceback__, file=sys.stderr
            )
            return logging.info(PrintColors.ENDC)

        else:
            guild = (
                ctx.guild.id if ctx.guild else "dm channel with " + str(ctx.author.id)
            )
            command = (
                ctx.command.name
                if ctx.command
                else "Error didn't occur during a command"
            )
            logging.info(  # Info so only a single "critical" log is saved
                f"{PrintColors.FAIL}------------------------------------------"
            )
            logging.critical(
                f"An error occurred\nGuild id: {guild}\nCommand name: {command}\nError: \n"
                + "".join(
                    traceback.format_exception(
                        etype=type(error), value=error, tb=error.__traceback__
                    )
                )
            )
            logging.info(
                f"------------------------------------------{PrintColors.ENDC}"
            )
        if (
            (isinstance(error, discord.NotFound) and error.code == 10062)
            or (isinstance(error, discord.HTTPException) and error.code == 50027)
            or isinstance(error, discord.Forbidden)
        ):
            # This is the error code for unknown interaction. This means the error occurred
            # running a slash command or button or whatever where it failed to find the interaction
            # Because of this, following up will also fail so we just return
            return
        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(label="Report bug", url=self.client.support_server_invite)
        )
        try:
            await ctx.send(
                ":x: an unexpected error occurred. If this should keep happening, please report it by clicking on the button and using `/report` in the support server.",
                view=view,
            )
        except (discord.Forbidden, discord.NotFound):
            pass  # This theoretically should be covered by all the cases above,
            # but handling it again here can't hurt


Cog = Events

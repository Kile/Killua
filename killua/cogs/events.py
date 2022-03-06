import io
import sys
import discord
import traceback

from datetime import datetime
from discord.utils import find
from discord.ext import commands, tasks
from PIL import Image

from killua.utils.classes import Guild, Book, PrintColors
from killua.static.constants import TOPGG_TOKEN, DBL_TOKEN, items, teams, PatreonBanner, stats

class Events(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.status.start()

    async def _post_guild_count(self) -> None:
        data = {
            "guilds": len(self.client.guilds),
            "users": len(self.client.users)
        }

        await self.client.session.post(f"https://discordbotlist.com/api/v1/bots/756206646396452975/stats", headers={"Authorization": DBL_TOKEN}, data=data)
        await self.client.session.post(f"https://top.gg/api/bots/756206646396452975/stats", headers={"Authorization": TOPGG_TOKEN}, data={"server_count": len(self.client.guilds)})

    async def _load_cards_cache(self) -> None:
        cards = [x for x in items.find()]

        if len(cards) == 0:
            return print(f"{PrintColors.WARNING}No cards in the database, could not load cache{PrintColors.ENDC}")

        print(f"{PrintColors.WARNING}Loading cards cache....{PrintColors.ENDC}")
        percentages = [25, 50, 75]
        for p, item in enumerate(cards):
            try:
                if item["_id"] in Book.card_cache:
                    continue # in case the event fires multiple times this avoids using unnecessary cpu power

                async with self.client.session.get(item["Image"]) as res:
                    image_bytes = await res.read()
                    image_card = Image.open(io.BytesIO(image_bytes)).convert('RGBA')
                    image_card = image_card.resize((84, 115), Image.ANTIALIAS)

                Book.card_cache[str(item["_id"])] = image_card
                if len(percentages) >= 1 and (p/len(cards))*100 > (percent:= percentages[0]):
                    print(f"{PrintColors.WARNING}Cache loaded {percent}%...{PrintColors.ENDC}")
                    percentages.remove(percent)
            except Exception as e:
                print(f"{PrintColors.FAIL}Failed to load card {item['_id']} with error: {e}{PrintColors.ENDC}")

        print(f"{PrintColors.OKGREEN}All cards successfully cached{PrintColors.ENDC}")

    async def _set_patreon_banner(self) -> None:
        res = await self.client.session.get(PatreonBanner.URL)
        image_bytes = await res.read()
        PatreonBanner.VALUE = image_bytes
        print(f"{PrintColors.OKGREEN}Successfully loaded patreon banner{PrintColors.ENDC}")

    def print_dev_text(self) -> None:
        print(f"{PrintColors.OKGREEN}Running bot in dev enviroment...{PrintColors.ENDC}")

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{PrintColors.HEADER}{PrintColors.OKGREEN}------")
        print('Logged in as: ' + self.client.user.name + f" (ID: {self.client.user.id})")
        print(f"------{PrintColors.ENDC}")
        self.client.startup_datetime = datetime.utcnow()

    @tasks.loop(hours=12)
    async def status(self):
        await self.client.update_presence()
        if not self.client.is_dev:
            await self._post_guild_count()

    @status.before_loop
    async def before_status(self):
        await self.client.wait_until_ready()

    @tasks.loop(hours=24)
    async def save_guilds(self):
        # this is currently not used but the earlier we collect this data, the better becaase I do plan to use it
        if not self.client.is_dev:
            stats.update_one({"_id": "growth"}, {"$push": {"growth": {"date": datetime.utcnow() ,"guilds": len(self.client.guilds), "users": len(self.client.users), "registered_users": teams.count_documents()}}})

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        #Changing the status
        await self.client.update_presence()
        Guild.add_default(guild.id)

        general = find(lambda x: x.name == 'general',  guild.text_channels)
        if general and general.permissions_for(guild.me).send_messages:
            prefix = Guild(guild.id).prefix
            embed = discord.Embed.from_dict({
                'title': 'Hello {}!'.format(guild.name),
                'description': f'Hi, my name is Killua, thank you for choosing me! \n\nTo get some info about me, use `{prefix}info`\n\nTo change the server prefix, use `{prefix}prefix <new prefix>` (you need administrator perms for that\n\nFor more commands, use `{prefix}help` to see every command\n\nPlease consider leaving feeback with `{prefix}fb` as this helps me improve Killua',
                'color': 0x1400ff
            })
            await general.send(embed=embed)
        await self._post_guild_count()

    @commands.Cog.listener()
    async def on_connect(self):
        #Changing Killua's status
        await self.client.update_presence()
        await self._set_patreon_banner()
        if self.client.is_dev:
            self.print_dev_text()
        else:
            await self._post_guild_count()
            await self._load_cards_cache()

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        #Changing Killua's status
        await self.client.update_presence()
        Guild(guild.id).delete()
        await self._post_guild_count()

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):

        if ctx.channel.permissions_for(ctx.me).send_messages and not self.client.is_dev: # we don't want to raise an error inside the error handler when Killua can't send the error because that does not trigger `on_command_error`
            return

        if ctx.command:
            usage = f"`{self.client.command_prefix(self.client, ctx.message)[2]}{(ctx.command.parent.name + ' ') if ctx.command.parent else ''}{ctx.command.usage}`"

        if isinstance(error, commands.BotMissingPermissions):
            return await ctx.send(f"I don\'t have the required permissions to use this command! (`{', '.join(error.missing_permissions)}`)")

        if isinstance(error, commands.MissingPermissions):
            return await ctx.send(f"You don\'t have the required permissions to use this command! (`{', '.join(error.missing_permissions)}`)")

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
            print(PrintColors.FAIL + "Ignoring exception in command {}:".format(ctx.command), file=sys.stderr)
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
            return print(PrintColors.ENDC)
        
        else:
            guild = ctx.guild.id if ctx.guild else "dm channel with "+ str(ctx.author.id)
            command = ctx.command.name if ctx.command else "Error didn't occur during a command"
            print(f'{PrintColors.FAIL}------------------------------------------')
            print(f'An error occurred\nGuild id: {guild}\nCommand name: {command}\nError: {error}')
            print(f'------------------------------------------{PrintColors.ENDC}')

Cog = Events

def setup(client):
    client.add_cog(Events(client))
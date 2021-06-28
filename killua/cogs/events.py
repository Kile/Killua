import json
import dbl
import discord
from datetime import datetime
from discord.utils import find
from discord.ext import commands, tasks
from killua.functions import p
from killua.classes import User, Guild
from killua.constants import PREMIUM_ROLES
with open('config.json', 'r') as config_file:
	config = json.loads(config_file.read())

class Events(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.token = config['dbl']
        self.dblpy = dbl.DBLClient(self.client, self.token, autopost=True)
        self.status.start()

    @commands.Cog.listener()
    async def on_ready(self):
        print('------')
        print('Logged in as: ' + self.client.user.name + f" (ID: {self.client.user.id})")
        print('------')
        self.client.startup_datetime = datetime.now()

    @tasks.loop(hours=12)
    async def status(self):
        await p(self)

    @status.before_loop
    async def before_status(self):
        await self.client.wait_until_ready()

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        #Changing the status
        await p(self)
        Guild.add_default(guild.id)

        general = find(lambda x: x.name == 'general',  guild.text_channels)
        if general and general.permissions_for(guild.me).send_messages:
            embed = discord.Embed.from_dict({
                'title': 'Hello {}!'.format(guild.name),
                'description': f'Hi, my name is Killua, thank you for choosing me! \n\nTo get some info about me, use `k!info`\n\nTo change the server prefix, use `k!prefix <new prefix>` (you need administrator perms for that\n\nFor more commands, use `k!help` to see every command\n\nPlease consider leaving feeback with `k!fb` as this helps me improve Killua',
                'color': 0x1400ff
            })
            await general.send(embed=embed)

    @commands.Cog.listener()
    async def on_connect(self):
        #Changing Killua's status
        await p(self)


    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        #Changing Killua's status
        await p(self)
        Guild(guild.id).delete()

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        # The purpose of this function is to kinda automate premium badges
        if not before.guild:
            return
        if not before.guild.id == 715358111472418908:
            return

        s = list(PREMIUM_ROLES.keys())

        common_elements = set(s).intersection([x.id for x in before.roles])
        if common_elements:
            for element in common_elements:
                if element in s and not element in [x.id for x in after.roles]:
                    User(after.user.id).remove_badge(PREMIUM_ROLES[element], premium=True)
                    return await after.user.send('Your Killua premium subscription ran out! Your premium permissions have sadly been taken :c. I hope you enjoyed your time as Killua supporter. (If you see this message after this you left Killuas server please rejoin to get Premium permissions again as you need to be on the server for that)')

        common_elements = set(s).intersection([x.id for x in after.roles])
        if common_elements:
            for element in common_elements:
                if element in s and not element in [x.id for x in before.roles]:
                    User(after.user.id).add_badge(PREMIUM_ROLES[element], premium=True)
                    return await after.user.send('Thank you for becoming a premium supporter! Check out your shiney badges with `k!profile` and have fun with your new perks!')

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        #This handels the k!bug cooldown
        if isinstance(error, commands.CommandOnCooldown):
            m, s = divmod(round(ctx.command.get_cooldown_retry_after(ctx)), 60)

            return await ctx.send(f'Wait {m:02d} minutes and {s:02d} seconds before using the command again, thank you for helping to improve killua :3')

        if isinstance(error, commands.BotMissingPermissions):
            return await ctx.send(f"I don\'t have the required permissions to use this command! (`{', '.join(error.missing_perms)}`)")

        if isinstance(error, commands.MissingPermissions):
            return await ctx.send(f"You don\'t have the required permissions to use this command! (`{', '.join(error.missing_perms)}`)")

        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send(f"Seems like you missed a required argument for this command: `{str(error.param).split(':')[0]}`")

        guild = ctx.guild.id if ctx.guild else "dm channel with "+ str(ctx.author.id)
        command = ctx.command.name if ctx.command else "Error didn't occur during a command"
        print('------------------------------------------')
        print(f'An error occured\nGuild id: {guild}\nCommand name: {command}\nError: {error}')
        print('------------------------------------------')

Cog = Events

def setup(client):
    client.add_cog(Events(client))
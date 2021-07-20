import discord
from discord.ext import commands
from killua.checks import check
from killua.classes import Category

class Feedback(commands.Cog):

    def __init__(self, client):
        self.client = client

    @check()
    @commands.command(extras={"category":Category.OTHER}, usage="bug <command> <text>")
    @commands.cooldown(rate=1, per=3600, type=commands.BucketType.guild)
    async def bug(self, ctx, command=None, *, bug=None):
        """Report Killua bugs with this command! For more info on how to report a bug, use `k!bug`."""
        if command:
            
            if self.client.get_command(command.lower()) is None and command.lower() != 'other':
                return ctx.send('Command not found. To report bugs not bound to a command, use `other` here')

            if bug is None:
                return await ctx.send('Please tell us what exactly the with the provided command is. For more info on how to do that, use `k!bug`')

            if command.lower() == 'other':
                matter = f'Bug regarding no spefific command'
            else:
                matter = f'Bug regarding the command `{command.lower()}`'

            embed = discord.Embed.from_dict({
                'title': f'Bug report from guild {ctx.guild.name} (ID: {ctx.guild.id})',
                'description': f'''{matter}  \n\n**Provided information:**\n\n{bug}\n\nReported by **{ctx.author}**''',
                'color': 0x1400ff
            })
            
            channel = self.client.get_channel(757201547204493381)

            message = await channel.send(embed=embed)
            await message.add_reaction('\U00002705')
            await message.add_reaction('\U0000274c')

            await ctx.send(':white_check_mark: thanks for reporting a bug! The bug will be looked at as soon as possible!')
        else:
            ctx.command.reset_cooldown(ctx)
            embed = discord.Embed.from_dict({
                'title': f'Bug reporting',
                'description': f'''Report a Killua bug by providing the command where the bug occurs, if it is no command use `other`
            
            After that please describe what should happen and what in reality happens, also how to reproduce the bug. Example:
            
            ```css
    k!bug ban Expectation: when I provide no reason the bot says 'no reason' Reality: The bot says 'None' as the reason
            
    Reproduction: ban a member without providing a reason```''',
                'color': 0x1400ff
            })

            await ctx.send(embed=embed)

    @check()
    @commands.command(aliases=['fb'], extras={"category":Category.OTHER}, usage="feedback <type> <text>")
    @commands.cooldown(rate=1, per=3600, type=commands.BucketType.user)
    async def feedback(self, ctx, Type=None, *, feedback=None):
        """Submit feedback to Killua with this command! For more information on how do send what, use `k!fb`."""
        if Type:
            
            if not Type.lower() in ['topic', '8ball', 'hug', 'apply', 'general', 'idea', 'feature-request', 'complain', 'compliment']:
                ctx.command.reset_cooldown(ctx)
                return ctx.send('Type not found. To see what types of feeback you can submit, use `k!fb`')

            if feedback is None:
                return await ctx.send('Please tell us what you have to say about the chosen point. For more info use `k!fb`')

            embed = discord.Embed.from_dict({
                'title': f'Feedback from guild {ctx.guild.name} (ID: {ctx.guild.id})',
                'description': f'''Type of feedback: `{Type}`  \n\n**Provided feedback:**\n\n{feedback}\n\nFeedback by **{ctx.author}**''',
                'color': 0x1400ff
            })
            
            channel = self.client.get_channel(790002080625983558)

            message = await channel.send(embed=embed)
            await message.add_reaction('\U00002705')
            await message.add_reaction('\U0000274c')

            await ctx.send(':white_check_mark: thanks for sending your feedback! The feedback will be looked at as soon as possible!')
        else:
            ctx.command.reset_cooldown(ctx)
            embed = discord.Embed.from_dict({
                'title': f'Sending feedback',
                'description': f'''Since this bot is in its early stages, feedback of users is of highest importance
            
    You can submit 9 types of feedback:

    `topic` - suggestion for a topic for `k!topic`
    `8ball` - suggestion for a response for `k8ball`
    `hug` - submit a hug text or image (Killua only) 
    `apply` - apply for the team, we are looking for artists, programmer, people looking out for the server etc. Of course being part of the team comes with it's advantages
    `general` - you just wanna give general feedback to us, no specific or too many cathegories for the other options
    `idea` - you have a good idea for a command (like `k!book <booktitle>`, a idea I had today and I wil implement cause it's cool). Please describe it as detailed as possible though
    `feature`-request - request a feature, kinda like idea but idk. Again, lease describe it as detailed as possible
    `complain` - complain about something
    `compliment` -  compliment a feature of Killua

    **This command has a 1 hour cooldown, for bug reporting please use `k!bug`, abuse will lead to blacklisting**
    [Support server](https://discord.gg/be4nvwq7rZ)''',
                'color': 0x1400ff
            })

            await ctx.send(embed=embed)

Cog = Feedback

def setup(client):
  client.add_cog(Feedback(client))

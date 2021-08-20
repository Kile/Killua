import discord
from discord.ext import commands

from typing import Union, List, Tuple
import random
import asyncio
import math

from killua.paginator import View
from killua.classes import User, ConfirmButton, Category
from killua.checks import blcheck

class RpsChoice(discord.ui.View):

    def __init__(self, user:discord.Member, **kwargs):
        super().__init__(**kwargs)
        self.user = user

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not (val := interaction.user.id == self.user.id):
            await interaction.response.defer()
        return val

    @discord.ui.select(placeholder="Choose what to pick", min_values=1, max_values=1, options=[discord.SelectOption(label="rock", value="-1", emoji="\U0001f5ff"), discord.SelectOption(label="paper", value="0", emoji="\U0001f4c4"), discord.SelectOption(label="scissors", value="1", emoji="\U00002702")])
    async def select(self, select: discord.ui.Select, interaction: discord.Interaction):
        self.value = int(select.values[0])
        for c in self.children:
            c.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

class Rps:
    
    def __init__(self, ctx:commands.Context, points:int=None, other:discord.Member=None):
        self.ctx = ctx
        self.points = points
        self.other = other
        self.emotes = {
            0: ":page_facing_up:",
            -1: ":moyai:",
            1: ":scissors:"
        }

    async def _dmcheck(self, user:discord.User) -> bool:
        """Checks if a users dms are open by sending them an empty message and either recieving an error for can't send an empty message or not allowed"""
        try:
            await user.send('')
        except Exception as e:
            if isinstance(e, discord.Forbidden):
                return False
            if isinstance(e, discord.HTTPException):
                return True
            return True


    def _result(self, p:int, q:int) -> int:
        """Evaluates who won, by doing very smart math"""
        return int(math.sin(math.pi/12*(q-p)*((q-p)**2+5)))

    async def _send_rps_embed(self) -> discord.Message:
            embed = discord.Embed.from_dict({
                'title': f'{self.ctx.author.display_name} against {self.other.display_name or self.ctx.me.display_name}: **Rock... Paper... Scissors!**',
                'image': {'url': 'https://media1.tenor.com/images/dc503adb8a708854089051c02112c465/tenor.gif?itemid=5264587'},
                'color': 0x1400ff
            })

            await self.ctx.send(embed=embed)
    
    async def _timeout(self, players:list, data:List[Tuple[discord.Message, discord.ui.View]]) -> None:
        """A way to handle a timeout of not responding to Killua in dms"""
        for x in players:
            if x.id in [v.user.id for m, v in data]:
                await x.send('Sadly the other player has not responded in time')
            else:
                await x.send('Too late, time to respond is up!')

    async def _wait_for_response(self, users:List[discord.Member]) -> Union[None, List[asyncio.Future]]:
        data = []
        for u in users:
            view = RpsChoice(user=u, timeout=None)
            msg = await u.send("You chose to play Rock Paper Scissors, what\'s your choice Hunter?", view=view)
            data.append((msg, view))

        done, pending = await asyncio.wait([v.wait() for m, v in data], return_when=asyncio.ALL_COMPLETED, timeout=100)

        for m, v in data:
            for child in v.children:
                child.disabled = True
            edited = await m.edit(view=v)

        if False in [x.done() == True for x in [*done, *pending]]:
            # Handles the case that one or both players don't respond to the dm in time
            return await self._timeout(users, data)

        return [v for m, v in data]

    async def _eval_outcome(self, winlose:int, choice1, choice2, player1:discord.Member, player2:discord.Member) -> discord.Message:
        """Evaluates the outcome, informs the players and handles the points """
        p1 = User(player1.id)
        p2 = User(player2.id)
        if winlose == -1:
            if self.points:
                p1.add_jenny(self.points)
                if player2 != self.ctx.me:
                    p2.remove_jenny(self.points)
                return await self.ctx.send(f'{self.emotes[choice1]} > {self.emotes[choice2]}: {player1.mention} won against {player2.mention} winning {self.points} Jenny which adds to a total of {p1.jenny + self.points}')
            else:
                return await self.ctx.send(f'{self.emotes[choice1]} > {self.emotes[choice2]}: {player1.mention} won against {player2.mention}')
        if winlose == 0:
            return await self.ctx.send(f'{self.emotes[choice1]} = {self.emotes[choice2]}: {player1.mention} tied against {player2.mention}')
        if winlose == 1:
            if self.points:
                p1.remove_jenny(self.points)
                if player2 != self.ctx.me:
                    p2.add_jenny(self.points)
                return await self.ctx.send(f'{self.emotes[choice1]} < {self.emotes[choice2]}: {player1.mention} lost against {player2.mention} losing {self.points} Jenny which leaves them a total of {p1.jenny - self.points}')
            else:
                return await self.ctx.send(f'{self.emotes[choice1]} < {self.emotes[choice2]}: {player1.mention} lost against {player2.mention}')

    async def singleplayer(self) -> Union[None, discord.Message]:
        """Handles the case of the user playing against the bot"""
        await self._send_rps_embed()

        resp = await self._wait_for_response([self.ctx.author])
        if not resp:
            return

        c2 = random.choice(['paper', 'rock', 'scissors'])
        winlose = self._result(resp[0].value, c2)
        await self._eval_outcome(winlose, resp[0].value, c2, self.ctx.author, self.ctx.me)

    async def multiplayer(self) -> Union[None, discord.Message]:
        """Handles the case of the user playing against anself.other user"""

        if await self._dmcheck(self.ctx.author) is False:
            return await self.ctx.send(f'You need to open your dm to Killua to play {self.ctx.author.mention}')
        if await self._dmcheck(self.other) is False:
            return await self.ctx.send(f'{self.other.name} needs to open their dms to Killua to play')

        if blcheck(self.other.id) is True:
            return await ctx.send('You can\'t play against someone blacklisted')

        view = ConfirmButton(self.other.id, timeout=80)
        msg = await self.ctx.send(f'{self.ctx.author.mention} challenged {self.other.mention} to a game of Rock Paper Scissors! Will **{self.other.name}** accept the challange?', view=view)
        await view.wait()

        for child in view.children:
            child.disabled = True

        await msg.edit(view=view)

        if not view.value:
            if view.timed_out:
                return await self.ctx.send(f'Sadly no response...')
            else:
                return await self.ctx.send(f"{self.other.display_name} doesn't want to play... maybe they do after a hug?")

        await self._send_rps_embed()
        res = await self._wait_for_response([self.ctx.author, self.other])
        if not res:
            return
        winlose = self._result(res[0].value, res[1].value)
        await self._eval_outcome(winlose, res[0].value, res[1].value, res[0].user, res[1].user)

    async def start(self) -> None:
        """The function starting the game"""
        if self.other == self.ctx.me:
            await self.singleplayer()
        else:
            await self.multiplayer()

class CountButtons(discord.ui.Button):
    """The code for every button used in the game"""
    def __init__(self, solutions: dict, index:int, correct:bool=None, **kwargs):
        self.index = index # the position the button is on. Starts with 1
        self.solutions = solutions # The solutions in the format {number: correct_button_index}
        self.correct = correct # If the button is correct
        super().__init__(style=discord.ButtonStyle.grey if correct is None else (discord.ButtonStyle.green if correct else discord.ButtonStyle.red), **kwargs)

    def _create_view(self, correct:bool) -> View:
        """Creates a new view after the callback depending on if the result was correct or not"""
        for c in self.view.children:
            if correct:
                c.correct=True if c.index == self.index else c.correct
                c.disabled=True if c.index == self.index or self.view.stage-1 == len(self.solutions) else c.disabled
                c.label=str(self.view.stage-1) if c.index == self.index else c.label
                c.style=discord.ButtonStyle.success if c.index == self.index else c.style
            else:
                c.correct=False if c.index == self.index else c.correct
                c.disabled=True
                c.label=str(self.view.stage) if c.index == self.solutions[self.view.stage] else c.label
                c.style=discord.ButtonStyle.red if c.index == self.index else c.style
            
        return self.view

    async def _respond(self, correct:bool, last:bool, view:View, interaction:discord.Interaction) -> discord.Message:
        """Responds with the new view"""
        if correct and last:
            return await interaction.response.edit_message(content="Congrats, you move on to the next level!", view=view)
        if not correct:
            return await interaction.response.edit_message(content="Oh no! This was not the right order! Better luck next time", view=view)
        if not last:
            return await interaction.response.edit_message(content="Can you remember?", view=view)

    async def callback(self, interaction: discord.Interaction):
        """Is called when a button is clicked and determines wether it was correct or not, then passes that on to other functions"""
        self.view.correct:bool = self.solutions[self.view.stage] == self.index # if the button was correct
        last: bool = self.view.stage == len(self.solutions) # if this is the last stage

        if self.view.correct:
            self.view.stage += 1

        view = self._create_view(self.view.correct)
        await self._respond(self.view.correct, last, view, interaction)

        if not self.view.correct or last:
            self.view.stop()

class CountGame:
    """A game where you have to remember numbers and type them in the right order"""
    def __init__(self, ctx, difficulty: Union["easy", "hard"]):
        self.ctx = ctx
        self.user = User(ctx.author.id)
        self.difficulty = difficulty
        self.level = 1

    def _handle_reward(self) -> int:
        """Creates a jenny reward based on the level and difficulty"""
        return int(random.randint(20, 30) * self.level * (0.5 if self.difficulty == "easy" else 1))

    def _assign_until_unique(self, already_assigned:List[int]) -> int:
        """Picks one random free spot to put the next number in"""
        r = random.randint(1, 25)
        if r in already_assigned:
            return self._assign_until_unique(already_assigned)
        else:
            return r

    def _create_solutions(self, keep_used:bool) -> None:
        """Creates the solution dictionary"""
        res:dict = (self.solutions if hasattr(self, "solutions") else {}) if keep_used else {} 
        for i in range(1 if keep_used else self.level):
            res[len(res)+1 if keep_used else i+1] = self._assign_until_unique(list(res.values()))
        self.solutions = res

    async def _send_solutions(self, msg:discord.Message=None) -> discord.Message:
        """Sends the solutions before hiding them"""
        view = View(self.ctx.author.id)
        view.stage = 1
        for i in range(25):
            view.add_item(discord.ui.Button(label=str([k for k, v in self.solutions.items() if v-1 == i][0]) if i+1 in list(self.solutions.values()) else " ", disabled=True, style=discord.ButtonStyle.grey))
        if not msg:
            msg = await self.ctx.send("Press the buttons in the order displayed as soon as the time starts. Good luck!", view=view)
        else:
            await msg.edit("One more button to remember. Get ready!", view=view)
            
        await asyncio.sleep(3 if self.level == 1 else (self.level*2*(0.5 if self.difficulty == "easy" else 1)))
        return msg

    async def _handle_game(self, msg:discord.Message) -> discord.Message:
        """The core of the game, creates the buttons and waits until the buttons return a result and handles it"""
        view = View(self.ctx.author.id, timeout=self.level*10*(0.5 if self.difficulty == "easy" else 1))
        view.stage = 1
        for i in range(25):
            view.add_item(CountButtons(self.solutions, i+1, label=" "))
        await msg.edit(content="Can you remember?", view=view)
        await view.wait()

        if not hasattr(view, "correct") or not view.correct: # This happens when the user has lost the game or it timed out
            reward = self._handle_reward()
            resp = "Too slow!" if not hasattr(view, "correct") else "Wrong choice!"
            for child in view.children:
                child.disabled = True
            await msg.edit(view=view)
            self.user.add_jenny(reward)
            return await self.ctx.send(resp + " But well done, you made it to level " + str(self.level) + " which brings you a reward of " + str(reward) + " Jenny!")

        self.level += 1

        if self.level == 26:
            reward = self._handle_reward()
            return await self.ctx.send("Well done, you completed the game! Your reward is " + str(reward) + " Jenny. Keep up the great work!")

        await asyncio.sleep(5)
        self._create_solutions(self.difficulty == "easy")
        new_msg = await self._send_solutions(msg)        
        await self._handle_game(new_msg)

    async def start(self):
        """The function to call to start the game"""
        self._create_solutions(self.difficulty == "easy")
        msg = await self._send_solutions()
        await self._handle_game(msg)

class Games(commands.Cog):

    def __init__(self, client):
        self.client = client

    @commands.command(extras={"category": Category.GAMES}, usage="count <easy/hard>")
    async def count(self, ctx, difficulty:str="easy"):
        """See how many numbers you can remember with this count game!"""
        if not difficulty.lower() in  ["easy", "hard"]:
            return await ctx.send("Invalid difficulty")
        game = CountGame(ctx, difficulty.lower())
        await game.start()

    @commands.command(extras={"category":Category.GAMES}, usage="rps <user> <points(optional)>")
    async def rps(self, ctx, member: discord.Member, points: int=None):
        """Play Rock Paper Scissors with your friends! You can play investing Jenny or just for fun."""
        
        if member.id == ctx.author.id:
            return await ctx.send('Baka! You can\'t play against yourself')
        
        if not member.bot:
            opponent = User(member.id)
        elif member.bot and member != ctx.me:
            return await ctx.send('Beep-boop, if you wanna play against a bot, play against me!')
        
        p2 = opponent.jenny if member != ctx.me else False

        user = User(ctx.author.id)

        p1 = user.jenny
    
        if points:
            if points <= 0 or points > 100:
                return await ctx.send(f'You can only play using 1-100 Jenny')

            if p1 < points:
                return await ctx.send(f'You do not have enough Jenny for that. Your current balance is `{p1}`')
            if not p2 is False and p2 < points:
                return await ctx.send(f'Your opponent does not have enough Jenny for that. Their current balance is `{p2}`')
    
        game = Rps(ctx, points, member)
        await game.start()

Cog = Games

def setup(client):
    client.add_cog(Games(client))
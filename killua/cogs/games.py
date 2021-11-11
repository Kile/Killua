import discord
from discord.ext import commands

from typing import Union, List, Tuple
from aiohttp import ClientSession
import random
import asyncio
import math

from killua.utils.paginator import View
from killua.utils.classes import User, ConfirmButton, Category
from killua.utils.checks import blcheck, check
from killua.utils.help import Select

class Trivia:
    """Handles a trivia game"""

    def __init__(self, ctx:commands.Context, difficulty:str, session: ClientSession):
        self.url = f"https://opentdb.com/api.php?amount=1&difficulty={difficulty}&type=multiple"
        self.difficulty = difficulty.lower()
        self.session = session
        self.ctx = ctx
        self.timed_out = False
        self.result = None
        self.rewards = {
            "easy": (5, 10),
            "medium": (10, 20),
            "hard": (20, 30)
        }

    async def _get(self) -> dict:
        """Requests the trivia url"""
        res = await self.session.get(self.url)
        self.res = await res.json()
        self.failed = (self.res["response_code"] != 0)

    def _create_embed(self) -> discord.Embed:
        """Creates the trivia embed"""
        question = self.data['question'].replace('&quot;', '"').replace("&#039;", "'")
        self.embed = discord.Embed.from_dict({
            "title": f"Trivia of category {self.data['category']}",
            "description": f"**difficulty:** {self.data['difficulty']}\n\n**Question:**\n{question}",
            "color": 0x1400ff
        })

    def _create_view(self) -> None:
        """Creates a select with the options needed"""
        self.view = View(self.ctx.author.id)
        self.data["incorrect_answers"].append(self.data["correct_answer"])
        self.options = random.sample(self.data["incorrect_answers"], k=4)
        self.correct_index = self.options.index(self.data["correct_answer"])
        self.view.add_item(Select(options=[discord.SelectOption(label=x if len(x) < 50 else x[:47] + "...", value=str(i)) for i, x in enumerate(self.options)]))

    async def create(self) -> None:
        """Creates all properties necessary"""
        await self._get()
        if not self.failed:
            self.data = self.res["results"][0]
            self._create_embed()
            self._create_view()

    async def send(self) -> Union[discord.Message, None]:
        """Sends the embed and view and awaits a response"""
        if self.failed:
            return await self.ctx.send(":x: There was an issue with the API. Please try again. If this should happen frequently, please report it")
        self.msg = await self.ctx.bot.send_message(self.ctx, embed=self.embed, view=self.view)
        await self.view.wait()
        await self.view.disable(self.msg)

        if not hasattr(self.view, "value"):
            self.timed_out = True
        else:
            self.result = self.view.value

    async def send_result(self) -> None:
        """Sends the result of the trivia and hands out jenny as rewards"""
        if self.failed:
            return

        elif self.timed_out:
            await self.ctx.send("Timed out!", reference=self.msg)

        elif self.result != self.correct_index:
            await self.ctx.send(f"Sadly not the right answer! The answer was {self.correct_index+1}) {self.options[self.correct_index]}")

        else:
            user = User(self.ctx.author.id)
            rew = random.randint(*self.rewards[self.difficulty])
            if user.is_entitled_to_double_jenny:
                rew *= 2
            user.add_jenny(rew)
            await self.ctx.send(f"Correct! Here are {rew} Jenny as a reward!")


class Rps:
    """A class handling someone playing rps alone or with someone else"""
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

    def _get_options(self) -> List[discord.SelectOption]:
        """Returns a new instance of the option list so it doesn't get mixed up when editing"""
        return [discord.SelectOption(label="rock", value="-1", emoji="\U0001f5ff"), discord.SelectOption(label="paper", value="0", emoji="\U0001f4c4"), discord.SelectOption(label="scissors", value="1", emoji="\U00002702")]

    def _result(self, p:int, q:int) -> int:
        """Evaluates who won, by doing very smart math"""
        return int(math.sin(math.pi/12*(q-p)*((q-p)**2+5)))

    async def _send_rps_embed(self) -> discord.Message:
            embed = discord.Embed.from_dict({
                'title': f'{self.ctx.author.display_name} against {self.other.display_name or self.ctx.me.display_name}: **Rock... Paper... Scissors!**',
                'image': {'url': 'https://media1.tenor.com/images/dc503adb8a708854089051c02112c465/tenor.gif?itemid=5264587'},
                'color': 0x1400ff
            })

            await self.ctx.bot.send_message(self.ctx, embed=embed)
    
    async def _timeout(self, players:list, data:List[Tuple[discord.Message, discord.ui.View]]) -> None:
        """A way to handle a timeout of not responding to Killua in dms"""
        for x in players:
            if x.id in [v.user.id for m, v in data]:
                await x.send('Sadly the other player has not responded in time')
            else:
                await x.send('Too late, time to respond is up!')

    async def _wait_for_response(self, users:List[discord.Member]) -> Union[None, List[View]]:
        data = []
        for u in users:
            view = View(user_id=u.id, timeout=None)
            select = Select(options=self._get_options())
            view.add_item(select)
            view.user = u
            msg = await u.send("You chose to play Rock Paper Scissors, what\'s your choice Hunter?", view=view)
            data.append((msg, view))

        done, pending = await asyncio.wait([v.wait() for m, v in data], return_when=asyncio.ALL_COMPLETED, timeout=100)

        for m, v in data:
            await v.disable(m)

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
                return await self.ctx.send(f'{self.emotes[choice1]} > {self.emotes[choice2]}: {player1.mention} won against {player2.mention} winning {self.points} Jenny which adds to a total of {p1.jenny}')
            else:
                return await self.ctx.send(f'{self.emotes[choice1]} > {self.emotes[choice2]}: {player1.mention} won against {player2.mention}')
        elif winlose == 0:
            return await self.ctx.send(f'{self.emotes[choice1]} = {self.emotes[choice2]}: {player1.mention} tied against {player2.mention}')
        elif winlose == 1:
            if self.points:
                p1.remove_jenny(self.points)
                if player2 != self.ctx.me:
                    p2.add_jenny(self.points)
                return await self.ctx.send(f'{self.emotes[choice1]} < {self.emotes[choice2]}: {player1.mention} lost against {player2.mention} losing {self.points} Jenny which leaves them a total of {p1.jenny}')
            else:
                return await self.ctx.send(f'{self.emotes[choice1]} < {self.emotes[choice2]}: {player1.mention} lost against {player2.mention}')

    async def singleplayer(self) -> Union[None, discord.Message]:
        """Handles the case of the user playing against the bot"""
        await self._send_rps_embed()

        resp = await self._wait_for_response([self.ctx.author])
        if not resp:
            return

        c2 = random.randint(-1, 1)
        winlose = self._result(resp[0].value, c2)
        await self._eval_outcome(winlose, resp[0].value, c2, self.ctx.author, self.ctx.me)

    async def multiplayer(self) -> Union[None, discord.Message]:
        """Handles the case of the user playing against anself.other user"""

        if await self._dmcheck(self.ctx.author) is False:
            return await self.ctx.send(f'You need to open your dm to Killua to play {self.ctx.author.mention}')
        if await self._dmcheck(self.other) is False:
            return await self.ctx.send(f'{self.other.name} needs to open their dms to Killua to play')

        if blcheck(self.other.id) is True:
            return await self.ctx.send('You can\'t play against someone blacklisted')

        view = ConfirmButton(self.other.id, timeout=80)
        msg = await self.ctx.send(f'{self.ctx.author.mention} challenged {self.other.mention} to a game of Rock Paper Scissors! Will **{self.other}** accept the challange?', view=view)
        await view.wait()
        await view.disable(msg)

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
        self.view.correct = self.solutions[self.view.stage] == self.index # if the button was correct
        last: bool = self.view.stage == len(self.solutions) # if this is the last stage

        if self.view.correct:
            self.view.stage += 1

        view = self._create_view(self.view.correct)
        await self._respond(self.view.correct, last, view, interaction)

        if not self.view.correct or last:
            self.view.stop()

class CountGame:
    """A game where you have to remember numbers and type them in the right order"""
    def __init__(self, ctx, difficulty: str):
        self.ctx = ctx
        self.user = User(ctx.author.id)
        self.difficulty = difficulty
        self.level = 1

    def _handle_reward(self) -> int:
        """Creates a jenny reward based on the level and difficulty"""
        return ((2 if self.user.is_entitled_to_double_jenny else 1) * int(random.randint(20, 30) * self.level * (0.5 if self.difficulty == "easy" else 1))) if self.level > 1 else 0

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
            msg = await self.ctx.bot.send_message(self.ctx, content="Press the buttons in the order displayed as soon as the time starts. Good luck!", view=view)
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

    @check(500)
    @commands.command(extras={"category": Category.GAMES}, usage="count <easy/hard>")
    async def count(self, ctx, difficulty:str="easy"):
        """See how many numbers you can remember with this count game!"""
        if not difficulty.lower() in  ["easy", "hard"]:
            return await ctx.send("Invalid difficulty")
        game = CountGame(ctx, difficulty.lower())
        await game.start()

    @check(30)
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

    @check(20)
    @commands.command(extras={"category": Category.GAMES}, usage="trivia <easy/medium/hard(optional)>")
    async def trivia(self, ctx, difficulty:str="easy"):
        """Play trivial and earn some jenny if you're right!"""
        if not difficulty.lower() in ["easy", "medium", "hard"]:
            return await ctx.send("Invalid difficulty! Please either choose one of the following: `easy`, `medium`, `hard`")

        game = Trivia(ctx, difficulty, self.client.session)
        await game.create()
        await game.send()
        await game.send_result()

Cog = Games

def setup(client):
    client.add_cog(Games(client))
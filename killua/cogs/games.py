import discord
from discord.ext import commands

import re
import random
import asyncio
import math
from aiohttp import ClientSession
from urllib.parse import unquote
from typing import Union, List, Tuple, Literal

from killua.bot import BaseBot
from killua.utils.paginator import View
from killua.utils.classes import CardLimitReached, User
from killua.utils.interactions import ConfirmButton
from killua.static.cards import Card
from killua.static.enums import Category, GameOptions
from killua.static.constants import ALLOWED_AMOUNT_MULTIPLE, DB
from killua.utils.checks import blcheck, check
from killua.utils.interactions import Select, Button

leaderboard_options = [
    discord.app_commands.Choice(name="global", value="global"),
    discord.app_commands.Choice(name="server", value="server")
]

class PlayAgainButton(discord.ui.Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.label = "Play Again"
        self.__clicked = None
        self.custom_id = "play_again"

    async def callback(self, interaction: discord.Interaction):

        if not self.__clicked:
            self.label = "[1/2] Play Again"
            self.__clicked = interaction.user
            await interaction.response.edit_message(view=self.view)

        else:
            if self.__clicked == interaction.user:
                self.label = "Play Again"
                self.__clicked = None
                await interaction.response.edit_message(view=self.view)
            else:
                self.label = "[2/2] Play Again"
                self.view.value = True
                await interaction.response.edit_message(view=self.view)
                self.view.stop()


class RpsSelect(discord.ui.Select):
    """Creates a select menu to confirm an rps choice"""
    def __init__(self, options, **kwargs):
        super().__init__( 
            min_values=1, 
            max_values=1, 
            options=options,
            **kwargs
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.value = int(interaction.data["values"][0])
        for opt in self.options:
            if opt.value == str(self.view.value):
                opt.default = True
        self.disabled = True
        await interaction.response.edit_message(view=self.view)
        self.view.stop()

class Trivia:
    """Handles a trivia game"""

    def __init__(self, ctx: commands.Context, difficulty: str, session: ClientSession):
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
        question = unquote(self.data["question"])
        question = re.sub("&.*?;", "", question) # Yes, apparently unqote is not enough to remove all html entities
        self.embed = discord.Embed.from_dict({
            "title": f"Trivia of category {self.data['category']}",
            "description": f"**difficulty:** {self.data['difficulty']}\n\n**Question:**\n{question}",
            "color": 0x3e4a78
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
        user = User(self.ctx.author.id)

        if self.failed:
            return

        elif self.timed_out:
            await self.ctx.send("Timed out!", reference=self.msg)

        elif self.result != self.correct_index:
            user.add_trivia_stat("wrong", self.difficulty)
            await self.ctx.send(f"Sadly not the right answer! The answer was {self.correct_index+1}) {self.options[self.correct_index]}")

        else:
            rew = random.randint(*self.rewards[self.difficulty])
            if user.is_entitled_to_double_jenny:
                rew *= 2
            user.add_jenny(rew)
            user.add_trivia_stat("right", self.difficulty)
            await self.ctx.send(f"Correct! Here are {rew} Jenny as a reward!")


class Rps:
    """A class handling someone playing rps alone or with someone else"""
    def __init__(self, ctx: commands.Context, points: int = None, other: discord.Member = None):
        self.ctx = ctx
        self.points = points
        self.other = other
        self.emotes = {
            0: ":page_facing_up:",
            -1: ":moyai:",
            1: ":scissors:"
        }

    async def _dmcheck(self, user: discord.User) -> bool:
        """Checks if a users dms are open by sending them an empty message and either recieving an error for can't send an empty message or not allowed"""
        try:
            await user.send("")
        except Exception as e:
            if isinstance(e, discord.Forbidden):
                return False
            if isinstance(e, discord.HTTPException):
                return True
            return True

    def _get_options(self) -> List[discord.SelectOption]:
        """Returns a new instance of the option list so itdoesn't get mixed up when editing"""
        return [discord.SelectOption(label="rock", value="-1", emoji="\U0001f5ff"), discord.SelectOption(label="paper", value="0", emoji="\U0001f4c4"), discord.SelectOption(label="scissors", value="1", emoji="\U00002702")]

    def _result(self, p: int, q: int) -> int:
        """Evaluates who won, by doing very smart math. -1 means player p won, 0 means it was a tie, 1 means player q won"""
        return int(math.sin(math.pi/12*(q-p)*((q-p)**2+5)))

    async def _send_rps_embed(self) -> discord.Message:
        """Sends a confirming embed"""
        embed = discord.Embed.from_dict({
            "title": f"{self.ctx.author.display_name} against {self.other.display_name or self.ctx.me.display_name}: **Rock... Paper... Scissors!**",
            "image": {"url": "https://media1.tenor.com/images/dc503adb8a708854089051c02112c465/tenor.gif?itemid=5264587"},
            "color": 0x3e4a78
        })

        await self.ctx.bot.send_message(self.ctx, embed=embed)
    
    async def _timeout(self, players: list, data: List[Tuple[discord.Message, View]]) -> None:
        """A way to handle a timeout of not responding to Killua in dms"""
        for x in players:
            if x.id in [v.user.id for _, v in data if v.value is not None]:
                await x.send("Sadly the other player has not responded in time")
            else:
                await x.send("Too late, time to respond is up!")

    async def _wait_for_response(self, users: List[discord.Member]) -> Union[None, List[View]]:
        data = []
        for u in users:
            view = View(user_id=u.id, timeout=None)
            select = RpsSelect(options=self._get_options())
            view.add_item(select)
            view.user = u
            msg = await u.send("You chose to play Rock Paper Scissors, what's your choice Hunter?", view=view)
            data.append((msg, view))

        done, pending = await asyncio.wait([v.wait() for _, v in data], return_when=asyncio.ALL_COMPLETED, timeout=100)

        for m, v in data:
            await v.disable(m)

        if False in [x.done() == True for x in [*done, *pending]]:
            # Handles the case that one or both players don't respond to the dm in time
            return await self._timeout(users, data)

        return [v for _, v in data]

    async def check_for_achivement(self, player: discord.User) -> None:
        """Checks wether someone has earend the "rps master" achivement"""
        user = User(player.id)
        if not "rps_master" in user.achievements and user.rps_stats["pve"]["won"] >= 25:
            user.add_achievement(["rps_master"])
            card = Card(83)
            try:
                if len(card.owners) >= (card.limit * ALLOWED_AMOUNT_MULTIPLE):
                    user.add_jenny(1000)
                    await player.send(f"By defeating me 25 times you have earned the **RPS Master** achievemt! Sadly the normal reward, the card \"{card.name}\" {card.emoji}, is currently owned by too many people, so insead you get **1000 Jenny** as a reward!")
                else:
                    user.add_card(83)
                    await player.send(f"By defeating me 25 times you have earned the **RPS Master** achievemt! As a reward you recieve the card \"{card.name}\" {card.emoji}")
            except CardLimitReached:
                user.add_jenny(1000)
                await player.send(f"By defeating me 25 times you have earned the **RPS Master** achievemt! Sadly you have no space in your book for the normal reward, the card \"{card.name}\" {card.emoji}, so insead you get **1000 Jenny** as a reward!")

    async def _eval_outcome(self, winlose: int, choice1: int, choice2: int, player1:discord.Member, player2: discord.Member, view: View) -> discord.Message:
        """Evaluates the outcome, informs the players and handles the points """
        p1 = User(player1.id)
        p2 = User(player2.id)
        if winlose == -1:
            p1.add_rps_stat("won", player2 == self.ctx.me)
            p2.add_rps_stat("lost", player1 == self.ctx.me)
            await self.check_for_achivement(player1)

            if self.points:
                p1.add_jenny(self.points)
                if player2 != self.ctx.me:
                    p2.remove_jenny(self.points)
                return await self.ctx.send(f"{self.emotes[choice1]} > {self.emotes[choice2]}: {player1.mention} won against {player2.mention} winning {self.points} Jenny which adds to a total of {p1.jenny}", view=view)
            else:
                return await self.ctx.send(f"{self.emotes[choice1]} > {self.emotes[choice2]}: {player1.mention} won against {player2.mention}", view=view)

        elif winlose == 0:
            p1.add_rps_stat("tied", player2 == self.ctx.me)
            if player2 != self.ctx.me:
                p2.add_rps_stat("tied", player1 == self.ctx.me)
            return await self.ctx.send(f"{self.emotes[choice1]} = {self.emotes[choice2]}: {player1.mention} tied against {player2.mention}", view=view)

        elif winlose == 1:
            p1.add_rps_stat("lost", player2 == self.ctx.me)
            p2.add_rps_stat("won", player1 == self.ctx.me)
            await self.check_for_achivement(player2)

            if self.points:
                p1.remove_jenny(self.points, player2 == self.ctx.me)
                if player2 != self.ctx.me:
                    p2.add_jenny(self.points)
                return await self.ctx.send(f"{self.emotes[choice1]} < {self.emotes[choice2]}: {player1.mention} lost against {player2.mention} losing {self.points} Jenny which leaves them a total of {p1.jenny}", view=view)
            else:
                return await self.ctx.send(f"{self.emotes[choice1]} < {self.emotes[choice2]}: {player1.mention} lost against {player2.mention}", view=view)

    def _play_again_view(self, players: List[discord.Member]) -> View:
        """Creates a button that, if clicked by both players, automatically launches another game"""
        view = View(user_id=[x.id for x in players])
        button = PlayAgainButton()
        view.add_item(button)
        return view

    async def singleplayer(self) -> Union[None, discord.Message]:
        """Handles the case of the user playing against the bot"""
        await self._send_rps_embed()

        resp = await self._wait_for_response([self.ctx.author])
        if not resp:
            return

        c2 = random.randint(-1, 1)
        winlose = self._result(resp[0].value, c2)

        view = View(user_id=self.ctx.author.id)
        button = Button(label="Play again", style=discord.ButtonStyle.grey)
        view.add_item(button)

        msg =await self._eval_outcome(winlose, resp[0].value, c2, self.ctx.author, self.ctx.me, view)

        await view.wait()
        await view.disable(msg) 
        if not view.value or view.timed_out:
            pass
        else:
            await self.singleplayer()

    async def multiplayer(self, replay: bool = False) -> Union[None, discord.Message]:
        """Handles the case of the user playing against self.other user"""
        if not replay:
            if await self._dmcheck(self.ctx.author) is False:
                return await self.ctx.send(f"You need to open your dm to Killua to play {self.ctx.author.mention}")
            if await self._dmcheck(self.other) is False:
                return await self.ctx.send(f"{self.other.name} needs to open their dms to Killua to play")

            if blcheck(self.other.id) is True:
                return await self.ctx.send("You can't play against someone blacklisted")

            view = ConfirmButton(self.other.id, timeout=80)
            msg = await self.ctx.send(f"{self.ctx.author.mention} challenged {self.other.mention} to a game of Rock Paper Scissors! Will **{self.other}** accept the challange?", view=view)
            await view.wait()
            await view.disable(msg)

            if not view.value:
                if view.timed_out:
                    return await self.ctx.send(f"Sadly no response...")
                else:
                    return await self.ctx.send(f"{self.other.display_name} doesn't want to play... maybe they do after a hug?")

        await self._send_rps_embed()
        res = await self._wait_for_response([self.ctx.author, self.other])
        if not res:
            return
        winlose = self._result(res[0].value, res[1].value)

        view = self._play_again_view([self.ctx.author, self.other])
        msg = await self._eval_outcome(winlose, res[0].value, res[1].value, res[0].user, res[1].user, view)
        await view.wait()
        await view.disable(msg) 
        if not view.value or view.timed_out:
            pass
        else:
            await self.multiplayer(replay=True)


    async def start(self) -> None:
        """The function starting the game"""
        if self.other == self.ctx.me:
            await self.singleplayer()
        else:
            await self.multiplayer()

class CountButtons(discord.ui.Button):
    """The code for every button used in the game"""
    def __init__(self, solutions: dict, index: int, correct: bool = None, **kwargs):
        self.index = index # the position the button is on. Starts with 1
        self.solutions = solutions # The solutions in the format {number: correct_button_index}
        self.correct = correct # If the button is correct
        super().__init__(style=discord.ButtonStyle.grey if correct is None else (discord.ButtonStyle.green if correct else discord.ButtonStyle.red), **kwargs)

    def _create_view(self, correct: bool) -> View:
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

    async def _respond(self, correct: bool, last: bool, view: View, interaction: discord.Interaction) -> discord.Message:
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
    def __init__(self, ctx: commands.Context, difficulty: str):
        self.ctx = ctx
        self.user = User(ctx.author.id)
        self.difficulty = difficulty
        self.level = 1

    def _handle_reward(self) -> int:
        """Creates a jenny reward based on the level and difficulty"""
        return ((2 if self.user.is_entitled_to_double_jenny else 1) * int(random.randint(20, 30) * self.level * (0.5 if self.difficulty == "easy" else 1))) if self.level > 1 else 0

    def _assign_until_unique(self, already_assigned: List[int]) -> int:
        """Picks one random free spot to put the next number in"""
        r = random.randint(1, 25)
        if r in already_assigned:
            return self._assign_until_unique(already_assigned)
        else:
            return r

    def _create_solutions(self, keep_used: bool) -> None:
        """Creates the solution dictionary"""
        res: dict = (self.solutions if hasattr(self, "solutions") else {}) if keep_used else {} 
        for i in range(1 if keep_used else self.level):
            res[len(res)+1 if keep_used else i+1] = self._assign_until_unique(list(res.values()))
        self.solutions = res

    async def _send_solutions(self, msg: discord.Message = None) -> discord.Message:
        """Sends the solutions before hiding them"""
        view = View(self.ctx.author.id)
        view.stage = 1
        for i in range(25):
            view.add_item(discord.ui.Button(label=str([k for k, v in self.solutions.items() if v-1 == i][0]) if i+1 in list(self.solutions.values()) else " ", disabled=True, style=discord.ButtonStyle.grey))
        if not msg:
            msg = await self.ctx.bot.send_message(self.ctx, content="Press the buttons in the order displayed as soon as the time starts. Good luck!", view=view)
        else:
            await msg.edit(content="One more button to remember. Get ready!", view=view)
            
        await asyncio.sleep(3 if self.level == 1 else (self.level*2*(0.5 if self.difficulty == "easy" else 1)))
        return msg

    async def _handle_game(self, msg: discord.Message) -> discord.Message:
        """The core of the game, creates the buttons and waits until the buttons return a result and handles it"""
        view = View(self.ctx.author.id, timeout=self.level*10*(0.5 if self.difficulty == "easy" else 1))
        view.stage = 1
        for i in range(25):
            view.add_item(CountButtons(self.solutions, i+1, label="\u200b", custom_id=str(i+1)))
        await msg.edit(content="Can you remember?", view=view)
        await view.wait()

        if not hasattr(view, "correct") or not view.correct: # This happens when the user has lost the game or it timed out
            reward = self._handle_reward()
            resp = "Too slow!" if not hasattr(view, "correct") else "Wrong choice!"
            for child in view.children:
                child.disabled = True
            await msg.edit(view=view)
            self.user.add_jenny(reward)

            if self.level-1 > self.user.counting_highscore[self.difficulty]:
                self.user.set_counting_highscore(self.difficulty, self.level-1)
                return await self.ctx.send(resp + " But well done, you made it to level " + str(self.level) + ", your new **personal best**, which brings you a reward of " + str(reward) + " Jenny!")
            else:
                return await self.ctx.send(resp + " But well done, you made it to level " + str(self.level) + ", which brings you a reward of " + str(reward) + " Jenny!")


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

class Games(commands.GroupCog, group_name="games"):

    def __init__(self, client: BaseBot):
        self.client = client

    @check(500)
    @commands.hybrid_command(extras={"category": Category.GAMES, "id": 40}, usage="count <easy/hard>")
    @discord.app_commands.describe(difficulty="The difficulty to play in")
    async def count(self, ctx: commands.Context, difficulty: Literal["easy", "hard"] = "easy"):
        """See how many numbers you can remember with this count game!"""
        game = CountGame(ctx, difficulty)
        await game.start()

    @check(30)
    @commands.hybrid_command(extras={"category": Category.GAMES, "id": 41}, usage="rps <user> <points(optional)>")
    @discord.app_commands.describe(
        member="The person to challenge",
        points="The points to play for"
    )
    async def rps(self, ctx: commands.Context, member: discord.Member, points: int = None):
        """Play Rock Paper Scissors with your friends! You can play investing Jenny or just for fun."""
        
        if member.id == ctx.author.id:
            return await ctx.send("Baka! You can't play against yourself")
        
        if not member.bot:
            opponent = User(member.id)
        elif member.bot and member != ctx.me:
            return await ctx.send("Beep-boop, if you wanna play against a bot, play against me!")
        
        p2 = opponent.jenny if member != ctx.me else False

        user = User(ctx.author.id)

        p1 = user.jenny
    
        if points:
            if points <= 0 or points > 100:
                return await ctx.send(f"You can only play using 1-100 Jenny")

            if p1 < points:
                return await ctx.send(f"You do not have enough Jenny for that. Your current balance is `{p1}`")
            if not p2 is False and p2 < points:
                return await ctx.send(f"Your opponent does not have enough Jenny for that. Their current balance is `{p2}`")
    
        game = Rps(ctx, points, member)
        await game.start()

    @check(20)
    @commands.hybrid_command(extras={"category": Category.GAMES, "id": 42}, usage="trivia <easy/medium/hard(optional)>")
    @discord.app_commands.describe(difficulty="The difficulty of the question")
    async def trivia(self, ctx: commands.Context, difficulty: Literal["easy", "medium", "hard"] = "easy"):
        """Play trivia and earn some jenny if you get the answer right!"""
        await ctx.defer()
        game = Trivia(ctx, difficulty, self.client.session)
        await game.create()
        await game.send()
        await game.send_result()

    @check()
    @commands.hybrid_command(extras={"category": Category.GAMES, "id": 43}, usage="stats <game> <user(optional)>")
    @discord.app_commands.describe(member="The person to check the stats of")
    async def gstats(self, ctx: commands.Context, game_type: Literal["rps", "counting", "trivia"], member: discord.Member = None):
        """Check the game stats of yourself or another user"""
        if not member:
            member = ctx.author

        game_type = getattr(GameOptions, game_type) # I cannot use the enum directly due to a library limitation with enums as annotations in message commands

        user = User(member.id)

        if game_type == GameOptions.rps:
            pve_played = (user.rps_stats["pve"]["tied"] + user.rps_stats["pve"]["lost"] + user.rps_stats["pve"]["won"])
            pve_win_rate = int(100*(user.rps_stats["pve"]["won"]/pve_played)) if pve_played != 0 else 0

            pvp_played = (user.rps_stats["pvp"]["tied"] + user.rps_stats["pvp"]["lost"] + user.rps_stats["pvp"]["won"])
            pvp_win_rate = int(100*(user.rps_stats["pvp"]["won"]/pvp_played)) if pvp_played != 0 else 0

            await ctx.send(embed=discord.Embed(
                title=f"{member.name}'s RPS stats",
                description=f"**__PVE__**:\n:crown: Win rate: {pve_win_rate}%\n\n Wins: {user.rps_stats['pve']['won']}\nDraws: {user.rps_stats['pve']['tied']}\nLosses: {user.rps_stats['pve']['lost']}" + \
                    f"\n\n**__PVP__**:\n:crown: Win rate: {pvp_win_rate}%\n\n Wins: {user.rps_stats['pvp']['won']}\nDraws: {user.rps_stats['pvp']['tied']}\nLosses: {user.rps_stats['pvp']['lost']}",
                color=0x3e4a78
            ))

        elif game_type == GameOptions.trivia:
            overall_right = user.trivia_stats["easy"]["right"] + user.trivia_stats["medium"]["right"] + user.trivia_stats["hard"]["right"]
            overall_wrong = user.trivia_stats["easy"]["wrong"] + user.trivia_stats["medium"]["wrong"] + user.trivia_stats["hard"]["wrong"]

            win_rate_overall = int(100*(overall_right/(overall_right + user.trivia_stats["easy"]["wrong"] + user.trivia_stats["medium"]["wrong"] + user.trivia_stats["hard"]["wrong"]))) if overall_wrong != 0 else 0

            easy_played = user.trivia_stats["easy"]["wrong"] + user.trivia_stats["easy"]["right"]
            win_rate_easy = int(100*(user.trivia_stats["easy"]["right"]/easy_played)) if easy_played != 0 else 0

            medium_played = user.trivia_stats["medium"]["wrong"] + user.trivia_stats["medium"]["right"]
            win_rate_medium = int(100*(user.trivia_stats["medium"]["right"]/medium_played)) if medium_played != 0 else 0

            hard_played = user.trivia_stats["hard"]["wrong"] + user.trivia_stats["hard"]["right"]
            win_rate_hard = int(100*(user.trivia_stats["hard"]["right"]/hard_played)) if hard_played != 0 else 0

            await ctx.send(embed=discord.Embed(
                title=f"{member.name}'s Trivia stats",
                description=f"__Overall correctness__: {win_rate_overall}%\n\n__Hard__:\nRight answers: {user.trivia_stats['hard']['right']}\nWrong answers: {user.trivia_stats['hard']['wrong']}\n{win_rate_hard}% correct\n\n__Medium__:\nRight answers: {user.trivia_stats['medium']['right']}\nWrong answers: {user.trivia_stats['medium']['wrong']}\n{win_rate_medium}% correct\n\n__Easy__:\nRight answers: {user.trivia_stats['easy']['right']}\nWrong answers: {user.trivia_stats['easy']['wrong']}\n{win_rate_easy}% correct",
                color=0x3e4a78
            ))

        elif game_type == GameOptions.counting:
            await ctx.send(embed=discord.Embed(
                title=f"{member.name}'s Counting stats",
                description=f"High score easy mode: {user.counting_highscore['easy']}\n\nHigh score hard mode: {user.counting_highscore['hard']}",
                color=0x3e4a78
            ))

    @check()
    @commands.hybrid_command(extras={"category": Category.GAMES, "id": 44}, usage="leaderboard <game> <global/server(optional)>", aliases=["glb"])
    @discord.app_commands.describe(game="The game to check the leaderboard of", where="Whether to show the global or server leaderboard")
    async def gleaderboard(self, ctx: commands.Context, game: Literal["rps", "counting", "trivia"], where: Literal["global", "server"] = "global"):
        """Checks the top 10 players of a game, globally or on the server."""
        game = getattr(GameOptions, game)  # I cannot use the enum directly due to a library limitation with enums as annotations in message commands
        all: List[dict] = list(DB.teams.find({} if where == "global" else {"id": {"$in": [m.id for m in ctx.guild.members]}}))

        if game == GameOptions.rps:
            top_5_pve: List[dict] = all
            top_5_pve.sort(key=lambda x: dict(x).get("stats", {}).get("rps", {}).get("pve", {}).get("won", 0), reverse=True)

            top_5_pvp: List[dict] = all
            top_5_pvp.sort(key=lambda x: dict(x).get("stats", {}).get("rps", {}).get("pvp", {}).get("won", 0), reverse=True)

            embed = discord.Embed(title="Global RPS leaderboard", description="**PVE**", color=0x3e4a78)
            for pos, player in enumerate(top_5_pve[:5]):
                # user = self.client.get_user(player["_id"])
                # if user:
                wins = player.get("stats", {}).get("rps", {}).get("pve", {}).get("won", 0)
                embed.description += f"\n**{pos+1}.** <@{player['id']}> - {wins} win{'s' if wins != 1 else ''}"

            embed.description += "\n\n**PVP**"

            for pos, player in enumerate(top_5_pvp[:5]):
                # user = self.client.get_user(player["_id"])
                # if user:
                wins = player.get("stats", {}).get("rps", {}).get("pvp", {}).get("won", 0)
                embed.description += f"\n**{pos+1}.** <@{player['id']}> - {wins} win{'s' if wins != 1 else ''}"

            await ctx.send(embed=embed)

        elif game == GameOptions.trivia:
            top_5_hard = all
            top_5_hard.sort(key=lambda x: dict(x).get("stats", {}).get("trivia", {}).get("hard", {}).get("right", 0), reverse=True)

            top_5_medium = all
            top_5_medium.sort(key=lambda x: dict(x).get("stats", {}).get("trivia", {}).get("medium", {}).get("right", 0), reverse=True)

            top_5_easy = all
            top_5_easy.sort(key=lambda x: dict(x).get("stats", {}).get("trivia", {}).get("easy", {}).get("right", 0), reverse=True)

            embed = discord.Embed(title="Global Trivia leaderboard", description="**Hard**", color=0x3e4a78)
            for pos, player in enumerate(top_5_hard[:5]):
                # user = self.client.get_user(player["_id"])
                # if user:
                right_answers = player.get("stats", {}).get("trivia", {}).get("hard", {}).get("right", 0)
                embed.description += f"\n**{pos+1}.** <@{player['id']}> - {right_answers} right answer{'s' if right_answers != 1 else ''}"
                    
            embed.description += "\n\n**Medium**"

            for pos, player in enumerate(top_5_medium[:5]):
                # user = self.client.get_user(player["_id"])
                # if user:
                right_answers = player.get("stats", {}).get("trivia", {}).get("medium", {}).get("right", 0)
                embed.description += f"\n**{pos+1}.** <@{player['id']}> - {right_answers} right answer{'s' if right_answers != 1 else ''}"

            embed.description += "\n\n**Easy**"

            for pos, player in enumerate(top_5_easy[:5]):
                # user = self.client.get_user(player["_id"])
                # if user:
                right_answers = player.get("stats", {}).get("trivia", {}).get("easy", {}).get("right", 0)
                embed.description += f"\n**{pos+1}.** <@{player['id']}> - {right_answers} right answer{'s' if right_answers != 1 else ''}"

            await ctx.send(embed=embed)

        elif game == GameOptions.counting:
            top_5_hard = all
            top_5_hard.sort(key=lambda x: dict(x).get("stats", {}).get("counting_highscore", {}).get("hard", 0), reverse=True)

            top_5_easy = all
            top_5_easy.sort(key=lambda x: dict(x).get("stats", {}).get("counting_highscore", {}).get("easy", 0), reverse=True)

            embed = discord.Embed(title="Global Counting leaderboard", description="**Hard**", color=0x3e4a78)
            for pos, player in enumerate(top_5_hard[:5]):
                # user = self.client.get_user(player["_id"])
                # if user:
                embed.description += f"\n**{pos+1}.** <@{player['id']}> - {player.get('stats', {}).get('counting_highscore', {}).get('hard', 0)} high score"
                    
            embed.description += "\n\n**Easy**"

            for pos, player in enumerate(top_5_easy[:5]):
                # user = self.client.get_user(player["_id"])
                # if user:
                embed.description += f"\n**{pos+1}.** <@{player['id']}> - {player.get('stats', {}).get('counting_highscore', {}).get('easy', 0)} high score"

            await ctx.send(embed=embed)

Cog = Games
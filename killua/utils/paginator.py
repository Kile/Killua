from __future__ import annotations

import discord
from discord.ext import commands
import datetime
from inspect import iscoroutinefunction
from .interactions import View

from typing import List, Union, Type, TypeVar, Coroutine, Tuple, Callable

E = TypeVar("E", discord.Embed, Type[discord.Embed])
R = TypeVar("R", discord.Embed, Type[discord.Embed], Tuple[Union[discord.Embed, Type[discord.Embed]], discord.File])
T = TypeVar("T")

class ButtonEmoji:
    FIRST_PAGE = "<:left_double_arrow:882751419529175152>"
    BACKWARDS = "<:left_arrow:882751271457685504>"
    FORWARD = "<:right_arrow:882751138548551700>"
    LAST_PAGE = "<:right_double_arrow:882752531124584518>"
    STOP = "<:stop:882750820867788860>"

class Color:
    BLURPLE = discord.ButtonStyle.blurple
    GREY = discord.ButtonStyle.grey
    RED = discord.ButtonStyle.red
    GREEN = discord.ButtonStyle.green


class DefaultEmbed(discord.Embed):
    """The default embed to use if no embed is provided"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.color = 0x1400ff
        self.timestamp = datetime.datetime.utcnow()
        self.set_footer()

class Buttons(View):
    """The core of the paginator"""
    def __init__(self, 
            user_id:int, 
            pages:Union[List[Union[str, int, dict]], None], 
            timeout:int,
            page:int, 
            max_pages:int,
            func:Union[Callable[[int, E, T], R], Coroutine[int, E, T, R], None], 
            embed:E,
            defer:bool,
            has_file:bool,
            paginator:Paginator,
            **kwargs
            ):

        super().__init__(user_id=user_id, timeout=timeout)
        self.pages = pages
        self.page = page
        self.max_pages = max_pages
        self.func = func
        self.embed = embed
        self.defer = defer
        self.has_file = has_file
        self.paginator = paginator
        self.file = None
        self.ignore = False
        self.messsage = None
        self._disable_on_end()

    def _disable_on_end(self) -> None:
        """
        Disables the buttons which skip to last/first page if you are on the last/first page. 
        Looks a bit hacky to not behave weirdly when the subclass changes the arrangement of the buttons, so it doesn't index but check for the emoji
        """

        for c in self.children:
            c.disabled = False
        
        if self.page == self.max_pages:
            for b in self.children:
                if str(b.emoji) == ButtonEmoji.LAST_PAGE:
                    b.disabled = True
                    break

        if self.page == 1:
            for b in self.children:
                if str(b.emoji) == ButtonEmoji.FIRST_PAGE:
                    b.disabled = True
                    break

    async def _get_embed(self) -> None:
        """Creates the embed for the next page"""
        if self.func:
            self.embed = (self.func(self.page, self.embed, self.pages)) if not iscoroutinefunction(self.func) else (await self.func(self.page, self.embed, self.pages))
        else:
            self.embed.description = str(self.pages[self.page-1])

        if isinstance(self.embed, DefaultEmbed):
            self.embed.set_footer(text= f"Page {self.page}/{self.max_pages}")

    async def _handle_file(self, interaction: discord.Interaction) -> None:
        """Handles the case of `has_file` being `True`"""
        await interaction.response.defer()
        await interaction.message.delete()

        self.ignore = True
        self.stop()
        self.paginator.page = self.page # setting that to be up to date
        await self.paginator.__class__(**vars(self.paginator)).start() # purpose of this is that this calls the subclasses `start` if a subclass exists

    async def _edit_message(self, interaction: discord.Interaction) -> None:
        """Gets the new embed and edits the message"""
        self._disable_on_end()
        self.message = interaction.message
        if self.has_file:
            return await self._handle_file(interaction)
        if self.defer:
            await interaction.response.edit_message(content="processing...", embed=interaction.message.embeds[0], view=None)
            await self._get_embed()
            await interaction.message.edit(content=None, embed=self.embed, view=self)
        else:
            await self._get_embed()
            await interaction.response.edit_message(embed=self.embed, view=self)

    @discord.ui.button(emoji=ButtonEmoji.FIRST_PAGE, style=Color.BLURPLE, disabled=True)
    async def first_page(self, button: discord.ui.button, interaction: discord.Interaction):
        self.page = 1
        await self._edit_message(interaction)

    @discord.ui.button(emoji=ButtonEmoji.BACKWARDS, style=Color.BLURPLE)
    async def backwards(self, button: discord.ui.button, interaction: discord.Interaction):
        self.page = self.page - 1 if self.page > 1 else self.max_pages
        await self._edit_message(interaction)

    @discord.ui.button(emoji=ButtonEmoji.STOP, style=Color.RED)
    async def delete(self, button: discord.ui.button, interaction: discord.Interaction):
        await interaction.message.delete()
        self.ignore = True
        self.stop()

    @discord.ui.button(emoji=ButtonEmoji.FORWARD, style=Color.BLURPLE)
    async def forward(self, button: discord.ui.button, interaction: discord.Interaction):
        self.page = self.page + 1 if not self.page >= self.max_pages else 1
        await self._edit_message(interaction)

    @discord.ui.button(emoji=ButtonEmoji.LAST_PAGE, style=Color.BLURPLE)
    async def last_page(self, button: discord.ui.button, interaction: discord.Interaction):
        self.page = self.max_pages
        await self._edit_message(interaction)


class Paginator:
    """
    A generic Paginator which supports the following:
        - execution more than the 3 seconds allowed by buttons; resolved by set `defer` to `True`
        - sending embeds with attachments. All that's needed is to set `has_file` to `True` and let `func` return a tuple of Embed, File
        - supporting very custom embed creation. By passing in a function with the arguments `page, embed, pages`, 
        the returned embed from that function will be the page. The function can be a Coroutine
        - passing in own sublasses of `discord.Embed` to use
        - defining when the menu times out

    The paginator will disable all buttons after the timeout has run out. 
    The paginator will not run into any ratelimiting issues except for when `defer` or `has_file` is `True`
    The paginator supports subclassing to for example modify buttons
    """
    def __init__(self,
        ctx:commands.Context,
        pages:Union[List[Union[str, int, dict]], None]=None,
        timeout:Union[int, float]=200,
        page:int=1, 
        max_pages:Union[int, None]=None,
        func:Union[Callable[[int, E, T], R], Coroutine[int, E, T, R], None]=None, 
        embed:E=None,
        defer:bool=False, # In case a pageturn can exceed 3 seconds this has to be set to True
        has_file:bool=False,
        **kwargs
        ):

        self.ctx = ctx
        self.pages = pages
        self.max_pages = max_pages or len(self.pages)
        self.timeout = timeout
        self.page = page
        self.func = func
        self.defer = defer
        self.embed = embed or DefaultEmbed()
        self.has_file = has_file
        self.file = None
        self.user_id = self.ctx.author.id
        self.paginator = self
        self.view = Buttons(user_id=self.user_id, pages=self.pages, timeout=self.timeout, page=self.page, max_pages=self.max_pages, func=self.func, embed=self.embed, defer=defer, has_file=self.has_file, paginator=self.paginator)

    async def _get_first_embed(self) -> None:
        """Gets the first embed to send"""
        if self.func:
            res = (self.func(self.page, self.embed, self.pages)) if not iscoroutinefunction(self.func) else (await self.func(self.page, self.embed, self.pages))
            if isinstance(res, tuple):
                self.embed, self.file = res
            else:
                self.embed = res
        else:
            desc = str(self.pages[self.page-1])
            self.embed.description = desc
        if isinstance(self.embed, DefaultEmbed):
            self.embed.set_footer(text=f"Page {self.page}/{self.max_pages}")

    async def _start(self) -> View:
        """A seperate method so overwriting `start` can still use the logic of the normal paginator"""
        await self._get_first_embed()
        self.view.message = (await self.ctx.bot.send_message(self.ctx, file=self.file, embed=self.embed, view=self.view)) if self.file else (await self.ctx.bot.send_message(self.ctx, embed=self.embed, view=self.view))
        
        await self.view.wait()

        if not self.view.ignore: # This is False when the message has been deleted/should not get their buttons disabled
            await self.view.disable(self.view.message) # disabling the views children

        return self.view # this is important for subclassing

    async def start(self) -> View:
        """This method simply calls the private one so it's easy to overwrite"""
        return await self._start()
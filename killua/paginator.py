from __future__ import annotations

import discord
from discord.ext import commands
import asyncio
import datetime
from inspect import iscoroutinefunction

from typing import List, Union, Type, TypeVar, Coroutine, Tuple
from collections.abc import Callable

from enum import Enum

E = TypeVar(Union[discord.Embed, Type[discord.Embed]])
R = TypeVar(Union[E, Tuple[E, discord.File]])
T = TypeVar("T")

class Button(Enum):
    FIRST_PAGE = "\U000023ea"
    BACKWARDS = "\U000025c0"
    FORWARD = "\U000025b6"
    LAST_PAGE = "\U000023e9"
    STOP = "\U000023f9"

class Color(Enum):
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

class View(discord.ui.View):
    """Subclassing this for buttons enabled us to not have to define interaction_check anymore, also not if we want a select menu"""
    def __init__(self, user_id:int, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id == self.user_id

class Buttons(View):
    """The core of the paginator"""
    def __init__(self, 
            user_id:int, 
            pages:Union[List[Union[str, int, dict]], None], 
            timeout:int,
            page:int, 
            max_pages:int,
            func:Union[Callable[[int, E, T], R], Coroutine[[int, E, T], R], None], 
            embed:E, 
            defer:bool,
            has_file:bool,
            paginator: Paginator,
            **kwargs
            ):

        super().__init__(user_id=user_id, timeout=timeout, **kwargs)
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

    async def _get_embed(self) -> None:
        if self.func:
            embed = (self.func(self.page, self.embed, self.pages)) if not iscoroutinefunction(self.func) else (await self.func(self.page, self.embed, self.pages))
        else:
            self.embed.description = str(self.pages[self.page-1])
            embed = self.embed # kinda hacky ngl, but else self.embed has a footer if the function does not create its own embed it will get stuck on Page 1/x
        if not embed.footer:
            embed.set_footer(text= f"Page {self.page}/{self.max_pages}")
        self.embed = embed

    async def _handle_file(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        await interaction.message.delete()

        self.ignore = True
        self.stop()
        await Paginator(self.paginator.ctx, self.paginator.pages, self.paginator.timeout, self.page, self.max_pages, self.func, self.paginator.embed, self.defer, self.has_file).start()

    async def _edit_message(self, interaction: discord.Interaction) -> None:
        self.message = interaction.message
        if self.has_file:
            return await self._handle_file(interaction)
        if self.defer:
            await interaction.response.edit_message(content="processing...", attachments=None, embed=interaction.message.embeds[0], view=None)
            await self._get_embed()
            await interaction.message.edit(content=None, embed=self.embed, view=self)
        else:
            await self._get_embed()
            await interaction.response.edit_message(embed=self.embed, view=self)

    @discord.ui.button(emoji=Button.FIRST_PAGE.value, style=Color.BLURPLE.value)
    async def first_page(self, button: discord.ui.button, interaction: discord.Interaction):
        self.page = 1
        await self._edit_message(interaction)

    @discord.ui.button(emoji=Button.BACKWARDS.value, style=Color.BLURPLE.value)
    async def backwards(self, button: discord.ui.button, interaction: discord.Interaction):
        self.page = self.page - 1 if self.page > 1 else self.max_pages
        await self._edit_message(interaction)

    @discord.ui.button(emoji=Button.STOP.value, style=Color.BLURPLE.value)
    async def delete(self, button: discord.ui.button, interaction: discord.Interaction):
        await interaction.message.delete()
        self.ignore = True
        self.stop()

    @discord.ui.button(emoji=Button.FORWARD.value, style=Color.BLURPLE.value)
    async def forward(self, button: discord.ui.button, interaction: discord.Interaction):
        self.page = self.page + 1 if not self.page >= self.max_pages else 1
        await self._edit_message(interaction)

    @discord.ui.button(emoji=Button.LAST_PAGE.value, style=Color.BLURPLE.value)
    async def last_page(self, button: discord.ui.button, interaction: discord.Interaction):
        self.page = self.max_pages
        await self._edit_message(interaction)

class Disabled(discord.ui.View):
    """Basically a Button class but all buttons are disabled"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @discord.ui.button(emoji=Button.FIRST_PAGE.value, style=Color.BLURPLE.value, disabled=True)
    async def first_page(self, button: discord.ui.button, interaction: discord.Interaction):
        pass

    @discord.ui.button(emoji=Button.BACKWARDS.value, style=Color.BLURPLE.value, disabled=True)
    async def backwards(self, button: discord.ui.button, interaction: discord.Interaction):
        pass

    @discord.ui.button(emoji=Button.STOP.value, style=Color.BLURPLE.value, disabled=True)
    async def delete(self, button: discord.ui.button, interaction: discord.Interaction):
        pass

    @discord.ui.button(emoji=Button.FORWARD.value, style=Color.BLURPLE.value, disabled=True)
    async def forward(self, button: discord.ui.button, interaction: discord.Interaction):
        pass

    @discord.ui.button(emoji=Button.LAST_PAGE.value, style=Color.BLURPLE.value, disabled=True)
    async def last_page(self, button: discord.ui.button, interaction: discord.Interaction):
        pass

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
    """
    def __init__(self,
        ctx:commands.Context,
        pages:Union[List[Union[str, int, dict]], None]=None,
        timeout:Union[int, float]=200,
        page:int=1, 
        max_pages:Union[int, None]=None,
        func:Union[Callable[[int, E, T], R], Coroutine[[int, E, T], R], None]=None, 
        embed:E=DefaultEmbed(),
        defer:bool=False, # In case a pageturn can exceed 3 seconds this has to be set to True
        has_file:bool=False
        ):

        self.ctx = ctx
        self.pages = pages
        self.max_pages = max_pages or len(self.pages)
        self.timeout = timeout
        self.page = page
        self.func = func
        self.embed = embed
        self.has_file = has_file
        self.file = None
        self.view = Buttons(user_id=self.ctx.author.id, pages=self.pages, timeout=self.timeout, page=self.page, max_pages=self.max_pages, func=self.func, embed=self.embed, defer=defer, has_file=self.has_file, paginator=self)

    async def _get_first_embed(self) -> None:
        if self.func:
            res = (self.func(self.page, self.embed, self.pages)) if not iscoroutinefunction(self.func) else (await self.func(self.page, self.embed, self.pages))
            if isinstance(res, tuple):
                self.embed, self.file = res
            else:
                self.embed = res
        else:
            desc = str(self.pages[self.page-1])
            self.embed.description = desc
        if not self.embed.footer:
            self.embed.set_footer(text=f"Page {self.page}/{self.max_pages}")

    async def start(self):
        await  self._get_first_embed()
        self.view.message = (await self.ctx.send(file=self.file, embed=self.embed, view=self.view)) if self.file else (await self.ctx.send(embed=self.embed, view=self.view))
        
        await asyncio.wait_for(self.view.wait(), timeout=None)
        if self.view.ignore: # This is True when the message has been deleted/should not get their buttons disabled
            return
        try:
            await self.view.message.edit(view=Disabled())
        except discord.NotFound: # This is a library bug atm. It will raise a NotFound even though the message was edited
            pass
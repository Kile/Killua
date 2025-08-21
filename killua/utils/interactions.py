import discord

from typing import Union, List, Any


class View(discord.ui.View):
    """Subclassing this for buttons enabled us to not have to define interaction_check anymore, also not if we want a select menu"""

    def __init__(self, user_id: Union[int, List[int]], **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.value: Any = None
        self.timed_out = False
        self.interaction = None

    async def on_timeout(self) -> None:
        self.timed_out = True

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if isinstance(self.user_id, int):
            if not (val := interaction.user.id == self.user_id):
                await interaction.response.defer()
        else:
            if not (val := (interaction.user.id in self.user_id)):
                await interaction.response.defer()
        self.interaction = interaction  # So we can respond to it anywhere
        return val

    async def disable(self, msg: discord.Message) -> Union[discord.Message, None]:
        """ "Disables the children inside of the view"""
        if not [
            c for c in self.children if not c.disabled
        ]:  # if every child is already disabled, we don't need to edit the message again
            return

        for c in self.children:
            c.disabled = True

        if self.interaction and not self.interaction.response.is_done():
            await self.interaction.response.edit_message(view=self)
        else:
            try:
                await msg.edit(view=self)
            except discord.HTTPException:
                pass  # Idk why but this can be Forbidden


class Modal(discord.ui.Modal):  # lgtm [py/missing-call-to-init]
    """A modal for various usages"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.interaction: discord.Interaction = None
        self.timed_out = False

    async def on_timeout(self) -> None:
        self.timed_out = True

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Called when the modal is submitted"""
        self.interaction = interaction


class Select(discord.ui.Select):
    """Creates a select menu to view the command groups"""

    def __init__(self, options, disable: bool = False, **kwargs):
        super().__init__(min_values=1, max_values=1, options=options, **kwargs)
        self.disable = disable

    async def callback(self, interaction: discord.Interaction):
        self.view.value = int(interaction.data["values"][0])
        for opt in self.options:
            if opt.value == str(self.view.value):
                opt.default = True

        if self.disable:
            await self.view.disable(interaction.message)

        self.view.stop()


class Button(discord.ui.Button):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def callback(self, _: discord.Interaction):
        self.view.value = self.custom_id
        self.view.stop()

class ConfirmButtonRow(discord.ui.ActionRow):
    def __init__(self, view: 'ConfirmButton') -> None:
        self.__view = view
        super().__init__()

    @discord.ui.button(
        label="confirm", style=discord.ButtonStyle.green, custom_id="confirm"
    )
    async def confirm(self, *_):
        print("Confirming")
        self.__view.value = True
        self.__view.timed_out = False
        self.__view.stop()

    @discord.ui.button(label="cancel", style=discord.ButtonStyle.red, custom_id="cancel")
    async def cancel(self, *_):
        self.__view.value = False
        self.__view.timed_out = False
        self.__view.stop()

class ConfirmButton(discord.ui.LayoutView):
    """A button that is used to confirm a certain action or deny it"""

    def __init__(self, user_id: int, text: str, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.timed_out = (
            False  # helps subclasses using Button to have set this to False
        )
        self.interaction = None
        self.value = False
        self.buttons = ConfirmButtonRow(self)
        container = discord.ui.Container(
            discord.ui.TextDisplay(
                content=text,
            ),
            self.buttons,
            accent_colour=discord.Colour.blurple(),
        )
        self.add_item(container)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not (val := interaction.user.id == self.user_id):
            await interaction.response.defer()
        self.interaction = interaction
        return val

    async def disable(self, msg: discord.Message) -> discord.Message:
        for child in self._children[0]._children[1]._children:
            # I tried to do this more dynamically but it didn't work
            child.disabled = True
        if self.interaction and not self.interaction.response.is_done():
            await self.interaction.response.edit_message(view=self)
        else:
            try:
                await msg.edit(view=self)
            except discord.HTTPException:
                pass  # Idk why but this can be Forbidden

    async def on_timeout(self):
        self.timed_out = True

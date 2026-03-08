import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
from typing import Optional

class ConfirmView(View):
    """Simple confirmation view with Yes/No buttons"""

    def __init__(self, user_id: int):
        super().__init__(timeout=30)
        self.user_id = user_id
        self.value = None

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You cannot interact with this confirmation.", ephemeral=True)
            return
        self.value = True
        self.stop()
        await interaction.response.edit_message(content="✅ Confirmed.", view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You cannot interact with this confirmation.", ephemeral=True)
            return
        self.value = False
        self.stop()
        await interaction.response.edit_message(content="❌ Cancelled.", view=None)
import discord
from discord.ext import commands
from deep_translator import (GoogleTranslator,
PonsTranslator,
LingueeTranslator,
MyMemoryTranslator,
YandexTranslator,
DeepL,
QCRI,
single_detection,
batch_detection)

class translate(commands.Cog):

  def __init__(self, client):
    self.client = client
<<<<<<< HEAD

=======
>>>>>>> ea404b285b0ca4aaf61355811118727e8a1affaf
    
  @commands.command()
  async def translate(self, ctx, source, target, *,args):

    langs_list = GoogleTranslator.get_supported_languages()
    

    embed = discord.Embed.from_dict({ 'title': f'Translation',
    'description': f'```\n{args}```\n`{source}` -> `{target}`\n',
    'color': 0x1400ff})

    try:
        translated = GoogleTranslator(source=source, target=target).translate(text=args)
        embed.description = embed.description + '\nSucessfully translated by Google Translator:'
    except Exception as ge:
        error = f'Google error: {ge}\n'
        
            
        try:
            embed.description = embed.description + '\nSucessfully translated by MyMemoryTranslator:'
            translated = MyMemoryTranslator(source=source, target=target).translate(text=args)
        except Exception as me:
            error = error + f'MyMemoryTranslator error: {me}\n'
            return await ctx.send(error)
            
    embed.description = embed.description + f'```\n{translated}```'
    
    await ctx.send(embed=embed)
    
<<<<<<< HEAD

Cog = translate

=======
Cog = translate
>>>>>>> ea404b285b0ca4aaf61355811118727e8a1affaf
    
def setup(client):
  client.add_cog(translate(client))

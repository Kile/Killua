import discord
from discord.ext import commands
from killua.functions import custom_cooldown, blcheck
from deep_translator import (GoogleTranslator,
PonsTranslator,
LingueeTranslator,
MyMemoryTranslator,
YandexTranslator,
DeepL,
QCRI,
single_detection,
batch_detection)


class Translate(commands.Cog):

  def __init__(self, client):
    self.client = client

    
  @commands.command()
  @custom_cooldown(10)
  async def translate(self, ctx, source, target, *,args):
    if blcheck(ctx.author.id) is True:
      return

    langs_list = GoogleTranslator.get_supported_languages()
    #h Translate anything to 20+ languages with this command! 
    #t Around 1 hour
    #u translate <source_lang> <target_lang> <text>

    embed = discord.Embed.from_dict({ 'title': f'Translation',
    'description': f'```\n{args}```\n`{source}` -> `{target}`\n',
    'color': 0x1400ff})

    try:
        translated = GoogleTranslator(source=source.lower(), target=target.lower()).translate(text=args)
        embed.description = embed.description + '\nSucessfully translated by Google Translator:'
    except Exception as ge:
        error = f'Google error: {ge}\n'
        
            
        try:
            embed.description = embed.description + '\nSucessfully translated by MyMemoryTranslator:'
            translated = MyMemoryTranslator(source=source.lower(), target=target.lower()).translate(text=args)
        except Exception as me:
            error = error + f'MyMemoryTranslator error: {me}\n'
            return await ctx.send(error)
            
    embed.description = embed.description + f'```\n{translated}```'
    
    await ctx.send(embed=embed)
    


Cog = Translate

    
def setup(client):
  client.add_cog(Translate(client))

import discord
import io
import aiohttp
from discord.ext import commands

class api(commands.Cog):
  
  def __init_(self, client):
    self.client = client
  
  @commands.command()
  async def urban(self, ctx, content):
    session = aiohttp.ClientSession() 
    headers = {'Content-Type': 'application/json',
        'Authorization': 'Bearer 16c6fa735e974848ea8395a4160b8'} 
    body = {
        'args': { 'text': content }
      } 
    #t 2-3 hours
    #c Using fAPI
    
    async with session.post('https://fapi.wrmsr.io/urban', headers=headers, json=body) as r: 
        response = await r.json()

    if response == []:
        sesssion.close
        return await ctx.send(':x: Not found')

    
    desc = urbandesc(response)
    embed = discord.Embed.from_dict({
            'title': f'Results for **{content}**',
            'description': desc,

            'color': 0x1400ff
            })
    await ctx.send(embed=embed)
    session.close
    

  @commands.command()
  async def cmm(self, ctx, *, content):
    #c Change my mind!
    #t Around 1-2 hours
    session = aiohttp.ClientSession() 
    headers = {'Content-Type': 'application/json',
        'Authorization': 'Bearer 16c6fa735e974848ea8395a4160b8'} 
    body = {
        'args': { 'text': content }
      } 
    
    async with session.post('https://fapi.wrmsr.io/changemymind', headers=headers, json=body) as r: 
        image_bytes = await r.read()
        file = discord.File(io.BytesIO(image_bytes), filename="image.png")
    await ctx.send(file=file)
    session.close
    
  @commands.command()
  async def quote(self, ctx, quotist: discord.Member, *, content):
    #t 2 hours
    #c powered by fAPI
    light = False
    compact = False
    name = ''
    now = datetime.now()
    message = content
    realcolor = quotist.color
    hours = f"{now:%I}"
    if int(hours) < 10:
        hours = hours[1:]
    if str(quotist.color) == '#000000':
        realcolor = '#ffffff'
    else:
        realcolor = str(quotist.color)

    if content.startswith('-l'):
        light = True
        message = content[2:]
        if realcolor == '#ffffff':
            realcolor = '#000000'
    if content.startswith('-c'):
        compact = True
        message = content[2:]
    if message.startswith(' -c'):
        compact = True
        message = message[3:]
    if message.startswith(' -l'):
        light = True
        message = message[3:]
        if realcolor == '#ffffff':
            realcolor = '#000000'

    if quotist.nick:
        name = quotist.nick
    else: 
        name = quotist.name
    session = aiohttp.ClientSession() 
    headers = {'Content-Type': 'application/json',
        'Authorization': 'Bearer 16c6fa735e974848ea8395a4160b8'} 
    body = {
        'args': { 'message': {'content': message},
        'author': {'color': realcolor,
        'bot': quotist.bot,
        'username': str(name),
        'avatarURL': str(quotist.avatar_url)},
        'timestamp':  f'Today at {hours}:{now:%M %p}',
        'light': light,
        'compact': compact}
      } 
    
    async with session.post('https://fapi.wrmsr.io/quote', headers=headers, json=body) as r: 
        image_bytes = await r.read()
        file = discord.File(io.BytesIO(image_bytes), filename="absolutelyreal.png")
    await ctx.send(file=file)

    
def urbandesc(array):  
    desc = f'''**__{array[0]["header"]}__**
**Meaning** \n{array[0]["meaning"]}\n
**Example** \n{array[0]["example"]}\n'''
    
    try:
        desc = desc + f'''\n**__{array[2]["header"]}__**
    **Meaning** \n{array[2]["meaning"]}\n
    **Example** \n{array[2]["example"]}\n\n'''
    except Exception as e:
        print('no')
    try:
        desc = desc + f'''\n**__{array[3]["header"]}__**
    **Meaning** \n{array[3]["meaning"]}\n
    **Example** \n{array[3]["example"]}\n\n'''
    except Exception as e:
        print('no')

    return desc

  def setup(client):
    client.add_cog(api(client))

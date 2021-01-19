import inspect
import discord
from discord.ext import commands
import time
from datetime import datetime, timedelta
import random
import typing
from random import randint
from killua.functions import custom_cooldown, blcheck


answers = ['Yep', 'You are kidding, right?', 'I think you know that better than me', 'I am sorry to break it to you but... no', 'I don\'t think so', 'Yes, no more info needed', 'No! Why would you ask that?', 'Let\'s do it!', 'Did you ask your mom?', 'I seriously don\'t think that is a good idea', 'Could you repeat that?', 'Well... maybe', 'Anything is possible']
topics = ['What\'s your favorite animal?', 'What is your favorite TV show?', 'If you could go anywhere in the world, where would you go?', 'What did you used to do, stopped and wish you hadn\'t?', 'What was the best day in your life?', 'For what person are you the most thankful for?', 'What is and has always been your least favorite subject?', 'What always makes you laugh and/or smile when you think about it?', 'Do you think there are aliens?', 'What is your earliest memory?', 'What\'s your favorite drink?', 'Where do you like going most for vacation?', 'What motivates you?', 'What is the best thing about school/work?', 'What\'s better, having high expectations or having low expectations?', 'What was the last movie you saw?', 'Have you read anything good recently?', 'What is your favorite day of the year?', 'What kind of music do you like to listen to?', 'What things are you passionate about?', 'What is your favorite childhood memory?', 'If you could acquire any skill, what would you choose?', 'What is the first thing that you think of in the morning?', 'What was the biggest life change you have gone through?', 'What is your favorite song of all time?', 'If you won $1 million playing the lottery, what would you do?', 'How would you know if you were in love?', 'If you could choose to have any useless super power, what would you pick?',
'Who is your role model?'. 'What\'s the best food you have ever eaten?', 'What accomplishment are you most proud of?', 'Would you rather be the most popular kid in school or the smartest kid in school?', 'Do you prefer to cook or order take out?', 'What is your dream job?' 'What\'s your ideal way to celebrate your birthday?', 'What is a short/long term goal of yours?', 'What are your three must have smart phone apps?', 'Would you rather be the smartest moron or dumbest genius?', 'What was the last gift that you received?', 'If you could give one piece of advice to the whole world, what would it be?', 'Describe your perfect day.', 'How would you define success?', 'What is the first thing that you notice when meeting someone new?', 'Do you prefer to take baths or showers?', 'Do you like to sing out loud when no one else is around?6']
huggif = [f'https://i.pinimg.com/originals/66/9b/67/669b67ae57452f7afbbe5252b6230f85.gif', f'https://i.pinimg.com/originals/70/83/0d/70830dfba718d62e7af95e74955867ac.jpg', 'https://cdn.discordapp.com/attachments/756945125568938045/756945463432839168/image0.gif', 'https://cdn.discordapp.com/attachments/756945125568938045/756945308381872168/image0.gif', 'https://cdn.discordapp.com/attachments/756945125568938045/756945151191941251/image0.gif', 'https://pbs.twimg.com/media/Dl4PPE4UUAAsb7c.jpg', 'https://encrypted-tbn0.gstatic.com/images?q=tbn%3AANd9GcSJgTjRyQW3NzmDzlvskIS7GMjlFpyS7yt_SQ&usqp=CAU', 'https://static.zerochan.net/Hunter.x.Hunter.full.1426317.jpg', 'https://encrypted-tbn0.gstatic.com/images?q=tbn%3AANd9GcQJjVWplBdqrasz8Fh-7nDkxRjnnNBqk0bZlQ&usqp=CAU', 'https://i.pinimg.com/originals/75/2e/0a/752e0a5f813400dfebe322fc8b0ad0ae.jpg', 'https://thumbs.gfycat.com/IllfatedComfortableAplomadofalcon-small.gif', 'https://steamuserimages-a.akamaihd.net/ugc/492403625757327002/9B089509DDCB6D9F8E11446C7F1BC29B9BA57384/', f'https://cdn.discordapp.com/attachments/756945125568938045/758235270524698634/image0.gif', f'https://cdn.discordapp.com/attachments/756945125568938045/758236571974762547/image0.jpg', 'https://cdn.discordapp.com/attachments/756945125568938045/758236721216749638/image0.jpg', 'https://cdn.discordapp.com/attachments/756945125568938045/758237082484473856/image0.jpg', 
'https://cdn.discordapp.com/attachments/756945125568938045/758237352756903936/image0.png', 'https://cdn.discordapp.com/attachments/756945125568938045/758237832954249216/image0.jpg', 'https://i.pinimg.com/originals/22/66/3e/22663e7f60734f141c72ca659a3a90cc.jpg', 'https://i.pinimg.com/originals/c5/38/d5/c538d54e493b118683c48ccbd0020311.jpg', 'https://wallpapercave.com/wp/wp6522234.jpg', 'https://i.pinimg.com/originals/48/db/98/48db98dac9d67143c4244991cb84b4f1.jpg', 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQjXQW8tVJfFmPz8qokH3u7maX6haz_6Uyx2w&usqp=CAU', 'https://i.pinimg.com/originals/f3/17/1b/f3171b2bb05b6c6ad90e6c094737d7e9.png', 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQrukypBFocf_oqpSSJmEpzx5sLjnpUJqMD4Q&usqp=CAU', 'https://images-wixmp-ed30a86b8c4ca887773594c2.wixmp.com/f/edb16fd5-2978-4a97-8568-7472c3205405/dbfi6uq-32adf5b9-e2d0-4892-8026-97012b9ae0d1.png/v1/fit/w_300,h_900,q_70,strp/happy_bday_killua_by_queijac_dbfi6uq-300w.jpg?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1cm46YXBwOiIsImlzcyI6InVybjphcHA6Iiwib2JqIjpbW3siaGVpZ2h0IjoiPD05MjkiLCJwYXRoIjoiXC9mXC9lZGIxNmZkNS0yOTc4LTRhOTctODU2OC03NDcyYzMyMDU0MDVcL2RiZmk2dXEtMzJhZGY1YjktZTJkMC00ODkyLTgwMjYtOTcwMTJiOWFlMGQxLnBuZyIsIndpZHRoIjoiPD05MDAifV1dLCJhdWQiOlsidXJuOnNlcnZpY2U6aW1hZ2Uub3BlcmF0aW9ucyJdfQ.ETgcZiDvdTQpDPQTQiMwW8ELS3xVXH_4nFYzEFpXJ8Y']
hugtext = [f'**(a)** hugs **(u)** as strong as they can', f'**(a)** hugs **(u)** and makes sure to not let go', f'**(a)** gives **(u)** the longest hug they have ever seen', f'**(a)** cuddles **(u)**', f'**(a)** uses **(u)** as a teddybear', f'**(a)** hugs **(u)** until all their worries are gone and 5 minutes longer',f'**(a)** clones themself and together they hug **(u)**', f'**(a)** jumps in **(u)**\'s arms', f'**(a)** gives **(u)** a bearhug', f'**(a)** finds a lamp with a Jinn and gets a wish. So they wish to hug **(u)**', f'**(a)** asks **(u)** for motivation and gets a hug','**(a)** looks at the floor, then up, then at the floor again and finnally hugs **(u)** with passion', '**(a)** looks deep into **(u)**\'s eyes and them gives them a hug', '**(a)** could do their homework but instead they decide to hug **(u)**']


class smallcommands(commands.Cog):

    def __init__(self, client):
        self.client = client
        
    @commands.command()
    async def say(self, ctx, *, content):
      if blcheck(ctx.author.id) is True:
        return
      #h Let's Killua say what is specified with this command. Possible abuse leads to this being restricted 
      #r user ID: 606162661184372736
      #t 5 minutes
      if ctx.author.id == 606162661184372736:
        await ctx.message.delete()
        await ctx.send(content)
        
    @commands.command()
    async def ping(self, ctx):
      if blcheck(ctx.author.id) is True:
        return
      #c pong
      #t 5 min
      #h Standart of seeing if the bot is working
    
      start = time.time()
      msg = await ctx.send('Pong!')
      end = time.time()
      await msg.edit(content = str('Pong in `' + str(1000 * (end - start))) + '` ms')
      
    @commands.command(name='topic')
    async def topic(self, ctx):
      if blcheck(ctx.author.id) is True:
        return
      #c constantly updating!
      #h From a constatnly updating list of topics to talk about one is chosen here
      await ctx.send(random.choice(topics))
      
    @commands.command()
    async def hi(self, ctx):
      if blcheck(ctx.author.id) is True:
        return
      #c The first command on Killua...
      #t 5 min
      #h This is just here because it was Killua's first command and I can't take that from him :3
      await ctx.send("Hello " + str(ctx.author)) 

    @commands.command(aliases=['8ball'])
    @custom_cooldown(2)
    async def ball(self, ctx, *, question):
      if blcheck(ctx.author.id) is True:
        return
      #h Ask Killua anything and he will answer
      #t 15 minutes
      embed = discord.Embed.from_dict({
        'title': f'8ball has spoken 🎱',
          'description': f'You asked:\n```\n{question}\n```\nMy answer is:\n```\n{random.choice(answers)}```',
          'footer': {'icon_url': str(ctx.author.avatar_url), 'text': f'Asked by {ctx.author}'},
          'color': 0x1400ff
      })
      await ctx.send(embed=embed)

    @commands.command(aliases=['av', 'a'])
    async def avatar(self, ctx, user: typing.Union[discord.User, int]=None):
      if blcheck(ctx.author.id) is True:
        return
      if not user:
        embed = avatar(ctx.author)
        return await ctx.send(embed=embed)
        #Showing the avatar of the author if no user is provided
      if isinstance(user, discord.User):
        embed = avatar(user)
        return await ctx.send(embed=embed)
        #If the user args is a mention the bot can just get everything from there
      try:
        newuser = await self.client.fetch_user(user)
        embed = avatar(newuser)
        return await ctx.send(embed=embed)
        #If the args is an integer the bot will try to get a user with the integer as ID
      except:
        return await ctx.send('Invalid user')

    @commands.command()
    async def hug(self, ctx, members: commands.Greedy[discord.Member]=None):
        if members:
            if ctx.author == members[0]:
                return await ctx.send(f'Someone hug {ctx.author.name}!')

            memberlist = ''
            for member in list(dict.fromkeys(members)):
                if list(dict.fromkeys(members))[-1] == member and len(list(dict.fromkeys(members))) != 1:
                    memberlist = memberlist + f' and {member.name}'
                else:
                    if list(dict.fromkeys(members))[0] == member:
                        memberlist = f'{member.name}'
                    else:
                        memberlist = memberlist + f', {member.name}'

            embed = discord.Embed.from_dict({
                'title': random.choice(hugtext).replace('(a)', ctx.author.name).replace('(u)', memberlist),
                'image':{
                    'url': random.choice(huggif)},

                'color': 0x1400ff
                })
            await ctx.send(embed=embed)
        else:
            await ctx.send('You provided no one to hug.. Should- I hug you?')
            def check(m):
                return m.content.lower() == 'yes' and m.author == ctx.author

            msg = await self.client.wait_for('message', check=check, timeout=60) 
            embed = discord.Embed.from_dict({
                'title': random.choice(hugtext).replace('(a)', 'Killua').replace('(u)',ctx.author.name),
                'image':{
                    'url': random.choice(huggif)
                },
                'color': 0x1400ff
                })
            await ctx.send(embed=embed) 
        
'''function avatar
Input:
user: the user to get the avatar from

Returns:
embed: an embed with the users avatar

Purpose: 
"outsourcing" a bit of the avatar command
'''
      
def avatar(user):
    #constructing the avatar embed
    embed = discord.Embed.from_dict({
        'title': f'Avatar of {user}',
        'image': {'url': str(user.avatar_url)},
        'color': 0x1400ff
    })
    return embed

Cog = smallcommands

def setup(client):
    client.add_cog(smallcommands(client))

import discord
from discord.ext import commands
from killua.functions import custom_cooldown, blcheck
import requests
from bs4 import BeautifulSoup

class web_scraping(commands.Cog):

    def __init__(self, client):
        self.client = client

    @commands.command(aliases=['b'])
    @custom_cooldown(10)
    async def book(self, ctx, *,book):
        #checking if the user is blacklisted
        #h With this command you can search for books! Just say the book title and look through the results
        if blcheck(ctx.author.id) is True:
            return
        #Looking for the book with this function
        embed = getBook(book, 0)
        #Sending the best result for the book
        msg = await ctx.send(embed=embed)
        #arrow backwards
        await msg.add_reaction('\U000025c0')
        #arrow forwards
        await msg.add_reaction('\U000025b6')
        #function making the user able to go to the next result with reactions
        await pageturn(msg, 0, book, self, ctx)

        

async def pageturn(msg:discord.Message, page:int, book:str, self, ctx):
    def check(reaction, user):
        #Checking if everything is right, the bot's reaction does not count
        return user == ctx.author and reaction.message.id == msg.id and user != ctx.me and(reaction.emoji == '\U000025b6' or reaction.emoji == '\U000025c0')
    try:
        reaction, user = await self.client.wait_for('reaction_add', timeout=120, check=check)
    #after 120 seconds the user reactions are removed 
    except asyncio.TimeoutError:
        await msg.remove_reaction('\U000025c0', ctx.me)
        await msg.remove_reaction('\U000025b6', ctx.me)
    else:
        if reaction.emoji == '\U000025b6':
            #forward emoji
            if page+1 == getBookCount(book):
                #If the user at the last result it will go back to nr one
                page = 0
            else:
                page = page+1
            #Getting the new infos for the next result
            embed = getBook(book, page)
            #Editing the existing embed with the result
            await msg.edit(embed=embed)
            try:
                await msg.remove_reaction('\U000025b6', ctx.author)
                #If permission and if the reaction is still there it will remove the authors reaction
            except:
                pass
            #It calls itself so that we have a loop which makes the user able to turn pages as much as they want
            await pageturn(msg, page, book, self, ctx)
        if reaction.emoji == '\U000025c0':
            if page+1 == 1:
                #Going back to the last result if 'back' is pressed on the first result
                page = getBookCount(book)-1       
            else:
                page = page-1
            #Crafting new book embed
            embed = getBook(book, page)
            try:
                await msg.remove_reaction('\U000025c0', ctx.author)
                #If permission and if the reaction is still there it will remove the authors reaction
            except:
                pass
            #Editing the embed to the right book
            await msg.edit(embed=embed)
            #function calls itself for the user to be able to press another reaction
            await pageturn(msg, page, book, self, ctx)

def getBookCount(name):
    #This function gets the number of total book results by taking in the books name
    # get the web page (id only for this website)
    page = BeautifulSoup(requests.get('https://www.goodreads.com/search?q=' + name).content, 'html.parser')
    return len(page.find_all('div', class_="u-anchorTarget"))

def getBook(name:str, nr:int):
    #This is the essential function getting infos about a book by taking the name and the number of the result list
    # get the id of the book (id only for this website)
    page = BeautifulSoup(requests.get('https://www.goodreads.com/search?q=' + name).content, 'html.parser')
    try:
        bookNr = page.find_all('div', class_="u-anchorTarget")[nr].attrs['id']
        #If there are no results this will raise an error, in that case Killua will say so
    except Exception as e: 
        print(e)
        return discord.Embed.from_dict({
            'title': '🤷‍♀️',
            'description': 'No results found',
            'color': 0x1400ff
        })

    bookn = getBookCount(name)
    # get the book
    book = BeautifulSoup(requests.get('https://www.goodreads.com/book/show/' + bookNr).content, 'html.parser')
    # get the book values
    try:
        rating = starRating = " ".join((str)(book.find('span', itemprop="ratingValue").text).split())
    except: 
        rating = "-"
    try:
        isbn = " ".join((str)(book.find_all('div', class_="infoBoxRowItem")[1].text).split())
    except:
        isbn = '-'
    try:
        name = " ".join((str)(book.find('div', class_="infoBoxRowItem").text).split())
    except:
        name = '-'
    try:
        author = " ".join((str)(book.find('a', class_="authorName").find_all('span')[0].text).split())
    except:
        author = '-'
    try:
        description = " ".join((str)(book.find('div', id="description").find(style="display:none").text).split())
        if description.startswith('Alternate cover for this ISBN can be found here'):
            description = description.replace('Alternate cover for this ISBN can be found here', '')
    except:
        description = '-'
    try:
        language = " ".join((str)(book.find('div', itemprop="inLanguage").text).split())
    except:
        language = '-'
    try:
        pages = " ".join((str)(book.find('span', itemprop="numberOfPages").text).split())
    except:
        pages = '-'
    #If a certain thing isn't specified such as number of pages, it is now replaced with '-'

    try:
        img_url = " ".join((str)(book.find('div', class_="bookCoverPrimary").find('img').attrs['src']).split())
    except:
        img_url = 'https://upload.wikimedia.org/wikipedia/commons/f/fc/No_picture_available.png';      

    if len(description) > 1700:
        description = description[:1700]+ '...'
    #Making sure embed limit isn't exceeded
    
    if len(name) > 256:
        name = name[:253] + '...'
    #Making sure title limit isn't exceeded
 
    return discord.Embed.from_dict({
        'title': f'Book: {name}',
        'thumbnail':{
            'url': img_url},
        'description': f'{nr+1}/{bookn}\n**Rating:** {rating}/5\n**Author:** {author}\n**Language:** {language}\n**Number of pages:** {pages}\n**Book description:**\n{description}',
        'footer': {'text': f'ISBN: {isbn}'},
        'color': 0x1400ff
    }) #returning the fresh crafted embed with all the information


    

Cog = web_scraping

def setup(client):
  client.add_cog(web_scraping(client))
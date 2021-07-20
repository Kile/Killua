import discord
from discord.ext import commands
from killua.checks import check
import requests
from bs4 import BeautifulSoup
import asyncio
from killua.classes import Category
from killua.paginator import Paginator

class WebScraping(commands.Cog):

    def __init__(self, client):
        self.client = client

    def _has_results(self, page) -> bool:
        """Checks if there are any results before activating the paginator"""
        try:
            bookNr = page.find_all('div', class_="u-anchorTarget")[0].attrs['id']
            #If there are no results this will raise an error, in that case Killua will say so
        except Exception as e: 
            return False
        return True

    def getBookCount(self, page) -> int:
        """
        Input:
        name: The name of the book

        Returns:
        number of results

        Purpose:
        To get the number of results
        """
        #This function gets the number of total book results by taking in the books name
        # get the web page (id only for this website)
        return len(page.find_all('div', class_="u-anchorTarget"))


    async def getBook(self, nr:int, name:str, pages) -> discord.Embed:
        """
        Input:
        name (str): name of the book
        nr (int): number of result

        Returns:
        embed: the embed with the informations about the book

        Purpose:
        Get result x of book with title y
        """
        #This is the essential function getting infos about a book by taking the name and the number of the result list
        # get the id of the book (id only for this website)
        bookNr = pages.find_all('div', class_="u-anchorTarget")[nr].attrs['id']
        # get the book
        res = await self.client.session.get('https://www.goodreads.com/book/show/' + bookNr)
        content = await res.text()
        book = BeautifulSoup(content.encode(), 'html.parser')
        # get the book values
        try:
            rating = " ".join((str)(book.find('span', itemprop="ratingValue").text).split())
        except Exception: 
            rating = "-"
        try:
            isbn = " ".join((str)(book.find_all('div', class_="infoBoxRowItem")[1].text).split())
            if not isnb.isdigit():
                isbn = '-'
        except Exception:
            isbn = '-'
        try:
            name = " ".join((str)(book.find('div', class_="bookCoverPrimary").find('img').attrs['alt']).split())
        except Exception:
            name = '-'
        try:
            author = " ".join((str)(book.find('a', class_="authorName").find_all('span')[0].text).split())
        except Exception:
            author = '-'
        try:
            description = " ".join((str)(book.find('div', id="description").find(style="display:none").text).split())
            if description.startswith('Alternate cover for this ISBN can be found here'):
                description = description.replace('Alternate cover for this ISBN can be found here', '')
        except Exception:
            description = '-'
        try:
            language = " ".join((str)(book.find('div', itemprop="inLanguage").text).split())
        except Exception:
            language = '-'
        try:
            pages = " ".join((str)(book.find('span', itemprop="numberOfPages").text).split())
        except Exception:
            pages = '-'
        #If a certain thing isn't specified such as number of pages, it is now replaced with '-'

        try:
            img_url = " ".join((str)(book.find('div', class_="bookCoverPrimary").find('img').attrs['src']).split())
        except Exception:
            img_url = 'https://upload.wikimedia.org/wikipedia/commons/f/fc/No_picture_available.png';      

        if len(description) > 1000:
            description = description[:1000]+ '...'
        #Making sure embed limit isn't exceeded
        
        if len(name) > 256:
            name = name[:253] + '...'
        #Making sure title limit isn't exceeded
    
        return discord.Embed.from_dict({
            'title': f'Book: {name}',
            'thumbnail':{
                'url': img_url},
            'description': f'\n**Rating:** {rating}/5\n**Author:** {author}\n**Language:** {language}\n**Number of pages:** {pages}\n**Book description:**\n{description}\n**ISBN:**{isbn}',
            'color': 0x1400ff
        }) #returning the fresh crafted embed with all the information

    @check(12)
    @commands.command(aliases=['n', 'search-book', 'sb'], extras={"category":Category.FUN}, usage="novel <title>")
    async def novel(self, ctx, *,book):
        """With this command you can search for books! Just say the book title and look through the results"""
        response = await self.client.session.get(f"https://www.goodreads.com/search?q={book}")
        content = await response.text()
        p = BeautifulSoup(content.encode(), 'html.parser')
        if not self._has_results(p):
            return await ctx.send("No results found")

        async def make_embed(page, embed, pages):
            return await self.getBook(page-1, book, pages)

        await Paginator(ctx, p, max_pages=self.getBookCount(p), func=make_embed, defer=True).start()

    

Cog = WebScraping

def setup(client):
  client.add_cog(WebScraping(client))

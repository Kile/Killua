import re
import discord
from discord.ext import commands
from bs4 import BeautifulSoup
from html import escape
from json import loads
from typing import Union
from pypxl import PxlClient
from urllib.parse import unquote

from killua.bot import BaseBot
from killua.utils.checks import check
from killua.utils.paginator import Paginator
from killua.static.enums import Category
from killua.static.constants import PXLAPI

from typing import Any, Callable

class WebScraping(commands.Cog):

    def __init__(self, client: BaseBot):
        self.client = client
        self.pxl = PxlClient(token=PXLAPI, stop_on_error=False, session=self.client.session)
        self.headers = {
            "dnt": "1",
            "accept-encoding": "gzip, deflate, sdch",
            "x-requested-with": "XMLHttpRequest",
            "accept-language": "en-GB,en-US;q=0.8,en;q=0.6,ms;q=0.4",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36",
            "accept": "application/json, text/javascript, */*; q=0.01",
            "referer": "https://duckduckgo.com/",
            "authority": "duckduckgo.com",
        }
        self._init_menus()

    def _init_menus(self) -> None:
        menus = []
        menus.append(discord.app_commands.ContextMenu(
            name='google',
            callback=self.client.callback_from_command(self.google, message=True)
        ))

        for menu in menus:
            self.client.tree.add_command(menu)

    def _try_else(self, x: Any, f: Callable[[Any], str], e: str = None) -> str:
        """Returns a book info it it exists, else "-" or e if provided"""
        try:
            return " ".join(f(x).split())
        except Exception:
            return e or "-" 

    def _has_results(self, page: BeautifulSoup) -> bool:
        """Checks if there are any results before activating the paginator"""
        try:
            page.find_all("div", class_="u-anchorTarget")[0].attrs["id"]
            #If there are no results this will raise an error, in that case Killua will say so
        except Exception: 
            return False
        return True

    def getBookCount(self, page) -> int:
        """Gets the number of results for a book"""
        #This function gets the number of total book results by taking in the books name
        # get the web page (id only for this website)
        return len(page.find_all("div", class_="u-anchorTarget"))


    async def getBook(self, nr: int, name: str, pages: BeautifulSoup) -> discord.Embed:
        """Get result x of a book with title y"""
        #This is the essential function getting infos about a book by taking the name and the number of the result list
        # get the id of the book (id only for this website)
        bookNr = pages.find_all("div", class_="u-anchorTarget")[nr].attrs["id"]
        # get the book
        res = await self.client.session.get("https://www.goodreads.com/book/show/" + bookNr)
        content = await res.text()
        book = BeautifulSoup(content.encode(), "html.parser")
        # get the book values

        rating = self._try_else(book, lambda book: book.find("span", itemprop="ratingValue").text)
        name = self._try_else(book, lambda book: book.find("div", class_="bookCoverPrimary").find("img").attrs["alt"])
        language = self._try_else(book, lambda book: book.find("div", itemprop="inLanguage").text)
        pages = self._try_else(book, lambda book: book.find("span", itemprop="numberOfPages").text)
        author = self._try_else(book, lambda book: book.find("a", class_="authorName").find_all("span")[0].text)
        img_url = self._try_else(book, lambda book: book.find("div", class_="bookCoverPrimary").find("img").attrs["src"], "https://upload.wikimedia.org/wikipedia/commons/f/fc/No_picture_available.png")
        isbn = self._try_else(book, lambda book:  book.find_all("div", class_="infoBoxRowItem")[1].text)
        description = self._try_else(book, lambda book: book.find("div", id="description").find(style="display:none").text)

        # Special cases
        if not isbn.isdigit():
            isbn = "-"

        if description.startswith("Alternate cover for this ISBN can be found here"):
            description = description.replace("Alternate cover for this ISBN can be found here", "")

        if len(description) > 1000:
            description = description[:1000]+ "..."
        #Making sure embed limit isn"t exceeded
        
        if len(name) > 256:
            name = name[:253] + "..."
        #Making sure title limit isn"t exceeded
    
        return discord.Embed.from_dict({
            "title": name,
            "thumbnail":{
                "url": img_url},
            "description": f"\n**Rating:** {rating}/5\n**Author:** {author}\n**Language:** {language}\n**Number of pages:** {pages}\n**Book description:**\n{description}\n**ISBN:**{isbn}",
            "color": 0x1400ff
        }) #returning the fresh crafted embed with all the information

    @commands.hybrid_group()
    async def web(self, _: commands.Context):
        """Web search commands"""
        pass

    @check(12)
    @web.command(aliases=["n", "search-book", "sb"], extras={"category":Category.FUN}, usage="book <title>")
    @discord.app_commands.describe(book="The name of the book to loock for")
    async def book(self, ctx: commands.Context, *, book: str):
        """With this command you can search for books! Just say the book title and look through the results"""
        response = await self.client.session.get(f"https://www.goodreads.com/search?q={book}")
        content: str = await response.text()
        p = BeautifulSoup(content.encode(), "html.parser")
        if not self._has_results(p):
            return await ctx.send("No results found")
        await ctx.channel.typing()
        await ctx.send("Processing...", ephemeral=True)
        async def make_embed(page, _, pages):
            return await self.getBook(page-1, book, pages)

        await Paginator(ctx, p, max_pages=self.getBookCount(p), func=make_embed, defer=True).start()

    async def _get_token(self, query: str) -> Union[str, None]:
        """Gets a new token to be used in the image search"""
        try:
            res = await self.client.session.get(f"https://duckduckgo.com/?q={escape(query)}")

            if not res.status == 200:
                return

            token = re.search(r"vqd='(.*?)'", str(BeautifulSoup(await res.text(), "html.parser"))).group(1)
            return token
        except Exception:
            return None

    @check(4)
    @web.command(aliases=["image", "i"], extras={"category":Category.FUN}, usage="img <query>")
    @discord.app_commands.describe(query="What image to look for")
    async def img(self, ctx: commands.Context, *, query: str):
        """Search for any image you want"""

        token = await self._get_token(query)

        if not token:
            return await ctx.send("Something went wrong... If this keeps happening please contact the developer")

        base = "https://duckduckgo.com/i.js?l=wt-wt&o=json&q={}&vqd={}&f=,,,&p=1"
        url = base.format(escape(query), token)

        response = await self.client.session.get(url, headers=self.headers)
        match = re.search(r"'results':\[{(.*?)}]", str(await response.text()))
        if not match:
            return await ctx.send("There were no images found matching your query")
        results = loads("[{" + match.group(1) + "}]")
        # An increadibly hacky way to get the list of results because the response is not in the correct format
        # and just weird
        links = [r["image"] for r in results if r["image"]]

        def make_embed(page, embed, pages):
            embed.title = "Results for query " + query
            embed.set_image(url=pages[page-1])
            return embed

        return await Paginator(ctx, links, func=make_embed).start()

    @check(2)
    @web.command(aliases=["g","search"], extras={"category":Category.FUN}, usage="google <query>")
    @discord.app_commands.describe(text="The query to search for")
    async def google(self, ctx: commands.Context, *, text: str):
        """Get the best results for a query the web has to offer"""
        
        r = await self.pxl.web_search(query=text)
        if r.success:
            results = r.data["results"]
            embed = discord.Embed.from_dict({
                "title": f"Results for query {text}",
                "color": 0x1400ff,
            })
            for i in range(4 if len(results) >= 4 else len(results)):
                res = results[i-1]
                embed.add_field(name="** **", value=f"**[__{res['title']}__]({res['url']})**\n{unquote(res['description'][:100])}..." if len(res["description"]) > 100 else unquote(res["description"]), inline=False)
            return await self.client.send_message(ctx, embed=embed, ephemeral=hasattr(ctx, "invoked_by_context_menu"))
        return await ctx.send(":x: "+r.error, epheremal=True)

Cog = WebScraping

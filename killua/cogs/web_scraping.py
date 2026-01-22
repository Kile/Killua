import re
import discord
from discord.ext import commands
from bs4 import BeautifulSoup
from html import escape
from json import loads
from typing import List, Union
from pypxl import PxlClient
from asyncio import wait_for, TimeoutError
from urllib.parse import unquote, quote

from killua.bot import BaseBot
from killua.utils.checks import check
from killua.utils.paginator import Paginator
from killua.static.enums import Category
from killua.static.constants import PXLAPI

class WebScraping(commands.GroupCog, group_name="web"):

    def __init__(self, client: BaseBot):
        self.client = client
        self.pxl = PxlClient(
            token=PXLAPI, stop_on_error=False, session=self.client.session
        )
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
        menus.append(
            discord.app_commands.ContextMenu(
                name="google",
                callback=self.client.callback_from_command(self.google, message=True),
                allowed_installs=discord.app_commands.AppInstallationType(
                    guild=True, user=True
                ),
                allowed_contexts=discord.app_commands.AppCommandContext(
                    guild=True, dm_channel=True, private_channel=True
                ),
            )
        )

        for menu in menus:
            self.client.tree.add_command(menu)

    def book_buying_links(self, book: dict) -> List[str]:
        """Returns a list of links where the book can be bought"""
        available_to_buy = []
        if "ia" in book:
            available_to_buy.append(
                f"[Internet Archive](https://archive.org/details/{book['ia'][0]})"
            )
        if "id_amazon" in book and [i for i in book["id_amazon"] if i]:
            available_to_buy.append(
                f"[Amazon](https://www.amazon.com/dp/{[i for i in book['id_amazon'] if i][0]})"
            )
        if "worldcat" in book:
            available_to_buy.append(
                f"[WorldCat](https://www.worldcat.org/title/{book['worldcat'][0]})"
            )
        if "id_goodreads" in book:
            available_to_buy.append(
                f"[Goodreads](https://www.goodreads.com/book/show/{book['id_goodreads'][0]})"
            )
        if "id_librarything" in book:
            available_to_buy.append(
                f"[LibraryThing](https://www.librarything.com/work/{book['id_librarything'][0]})"
            )
        if "id_overdrive" in book:
            available_to_buy.append(
                f"[Overdrive](https://www.overdrive.com/media/{book['id_overdrive'][0]})"
            )
        return available_to_buy

    def embed_for_book(self, book: dict) -> discord.Embed:
        """Creates an embed for a book"""
        embed = discord.Embed(
            title=(
                book["title"]
                if len(book["title"]) < 256
                else (book["title"][:253] + "...")
            ),
            url=f"https://openlibrary.org{book['key']}",
            color=0x3E4A78,
        )

        if "author_name" in book:
            embed.add_field(name="Author", value=book["author_name"][0])
        if "first_publish_year" in book:
            embed.add_field(name="Published", value=book["first_publish_year"])
        if "language" in book:
            embed.add_field(name="Language", value=book["language"][0])
        if "isbn" in book:
            embed.add_field(name="ISBN", value=book["isbn"][0])
        if "edition_count" in book:
            embed.add_field(name="Editions", value=book["edition_count"])

        available_to_buy = self.book_buying_links(book)
        if available_to_buy:
            embed.add_field(
                name="Available to buy",
                value="\n".join(available_to_buy),
                inline=False,
            )

        if "cover_i" in book:
            embed.set_image(
                url=f"https://covers.openlibrary.org/b/id/{book['cover_i']}-M.jpg"
            )

        return embed

    @check(12)
    @commands.hybrid_command(
        aliases=["n", "search-book", "sb"],
        extras={"category": Category.FUN, "id": 116},
        usage="book <title>",
    )
    @discord.app_commands.describe(book="The name of the book to look for")
    async def novel(self, ctx: commands.Context, *, book: str):
        """With this command you can search for books! Just say the book title and look through the results"""
        await ctx.channel.typing()
        if ctx.interaction:
            await ctx.send("Processing...", ephemeral=True)

        response = await self.client.session.get(
            f"https://openlibrary.org/search.json?q={quote(book)}"
        )
        if response.status != 200:
            return await ctx.send(
                "Something went wrong... If this keeps happening please contact the developer"
            )

        data = await response.json()
        if not data["numFound"]:
            return await ctx.send("No results found")

        embeds = []
        for book in data["docs"]:
            embed = self.embed_for_book(book)
            embeds.append({"embed": embed, "key": book["key"]})

        async def make_embed(page, embed: discord.Embed, pages):
            embed = pages[page - 1]["embed"]
            key = pages[page - 1]["key"]
            response = await self.client.session.get(
                f"https://openlibrary.org{key}.json"
            )
            if response.status != 200:
                embed.description = "No description found"
                return embed
            data = await response.json()
            if "description" in data:
                if isinstance(data["description"], dict):
                    embed.description = (
                        data["description"]["value"]
                        if len(data["description"]["value"]) < 2048
                        else (data["description"]["value"][:2045] + "...")
                    )
                else:
                    embed.description = (
                        data["description"]
                        if len(data["description"]) < 2048
                        else (data["description"][:2045] + "...")
                    )
            else:
                embed.description = "No description found"
            embed.set_footer(text=f"Page {page}/{len(pages)}")
            return embed

        return await Paginator(ctx, embeds, func=make_embed).start()

    async def _get_token(self, query: str) -> Union[str, None]:
        """Gets a new token to be used in the image search"""
        try:
            res = await self.client.session.get(
                f"https://duckduckgo.com/?q={escape(query)}"
            )
            if res.status != 200:
                return
            token = re.search(
                r'vqd="(.*?)",', str(BeautifulSoup(await res.text(), "html.parser"))
            ).group(1)
            return token
        except Exception:
            return

    async def get_duckduckgo_images(self, query: str) -> Union[List[str], None]:
        token = await self._get_token(query)

        if not token:
            return None

        base = "https://duckduckgo.com/i.js?l=wt-wt&o=json&q={}&vqd={}&f=,,,&p=1"
        url = base.format(escape(query), token)

        response = await self.client.session.get(url, headers=self.headers)

        if response.status != 200:
            if response.status == 403:
                return None

            return None

        results = loads(await response.text())["results"]

        if not results:
            return None

        # A hacky way to get the list of results because the response is not in the correct format
        # as duckduckgo is not returning a json decodable response but a string

        return [r["image"] for r in results if r["image"]]

    async def get_soup(self, url) -> Union[int, BeautifulSoup]:
        """Make request and return BeautifulSoup object"""
        header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.134 Safari/537.36"
        }

        response = await self.client.session.get(url, headers=header)

        if response.status != 200:
            return response.status

        return BeautifulSoup(await response.text(), "html.parser")

    async def get_bing_images(self, query: str) -> List[str]:
        """Make the request format it correctly and return the list of images"""
        BASE_URL = "http://www.bing.com/images/search?q={}&FORM=HDRSC2"

        response: BeautifulSoup = await self.get_soup(BASE_URL.format(query))

        if isinstance(response, int):
            return response

        images = []  # contains the link for large original images, type of  image
        for a in response.find_all("a", {"class": "iusc"}):
            try:
                m = loads(a["m"])
                image_url = m["murl"]

                images.append(image_url)
            except Exception:
                continue  # Possible it errors, skip if so

        # Filter out any malformed urls
        images = list(filter(lambda x: re.match(r"^https?://[^\s]+$", x), images))

        return images

    @check(4)
    @commands.hybrid_command(
        aliases=["image", "i"],
        extras={"category": Category.FUN, "id": 117, "clone_top_level": True},
        usage="img <query>",
    )
    @discord.app_commands.describe(query="What image to look for")
    async def img(self, ctx: commands.Context, *, query: str):
        """Search for any image you want"""
        if ctx.interaction and not ctx.interaction.response.is_done():
            await ctx.defer()  # I don't want this to fail, even if it takes < 3 secs most of the time

        links = await self.get_bing_images(query)

        if isinstance(links, int):
            return await ctx.send(
                f"Something went wrong while searching for images, got status code {links}"
            )

        if not links:
            return await ctx.send("No results found")

        def make_embed(page, embed: discord.Embed, pages):
            embed.title = "Results for query " + query
            embed.set_image(url=pages[page - 1])
            return embed

        return await Paginator(ctx, links, func=make_embed).start()

    @check(2)
    @commands.hybrid_command(
        aliases=["g", "search"],
        extras={"category": Category.FUN, "id": 118},
        usage="google <query>",
    )
    @discord.app_commands.describe(text="The query to search for")
    async def google(self, ctx: commands.Context, *, text: str):
        """Get the best results for a query the web has to offer"""

        try:
            r = await wait_for(
                self.pxl.web_search(query=text), 2
            )  # 2 second timeout so the interaction does not fail
        except TimeoutError:
            return await ctx.send(
                "The API is taking too long to respond, please try again later (it is likely down)"
            )

        if r.success:
            results = r.data["results"]
            embed = discord.Embed.from_dict(
                {
                    "title": f"Results for query: {text}",
                    "color": 0x3E4A78,
                }
            )
            for i in range(4 if len(results) >= 4 else len(results)):
                res = results[i - 1]
                embed.add_field(
                    name="** **",
                    value=(
                        f"**[__{res['title']}__]({res['url']})**\n{unquote(res['description'][:100])}..."
                        if len(res["description"]) > 100
                        else unquote(res["description"])
                    ),
                    inline=False,
                )
            return await self.client.send_message(
                ctx, embed=embed, ephemeral=hasattr(ctx, "invoked_by_context_menu")
            )
        if len(r.error) > 2000:
            return await ctx.send(
                discord.Embed(
                    title="An error occurred with the service this command is using",
                    description=":x: The service is likely down. Please try again later.",
                    color=discord.Color.red(),
                )
            )
        return await ctx.send(
            embed=discord.Embed(
                title="An error occurred running the command",
                description=":x: The service Killua is using responded with an error: "
                + r.error,
                color=discord.Color.red(),
            ),
            ephemeral=True,
        )


Cog = WebScraping

from __future__ import annotations

import discord
from aiohttp import ClientSession
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from datetime import datetime
from pathlib import Path
from typing import Tuple, Union

from killua.utils.classes.user import User
from killua.utils.classes.card import Card
from killua.bot import BaseBot as Bot


# pillow logic contributed by DerUSBstick (Thank you!)
class Book:

    background_cache = {}
    card_cache = {}

    def __init__(
        self, client: Bot
    ):
        self.session = client.session
        self.base_url = client.api_url(to_fetch=True)
        self.client = client
        self._book_token_cache: Tuple[str, str] = None
        self.scalar = 2

    @property
    def book_token_cache(self) -> Tuple[str, str]:
        # No token is permanent, so it may need to be refreshed if the token is older than 24 hours
        if self._book_token_cache is None or datetime.fromtimestamp(float(self._book_token_cache[1])) < datetime.now():
            self._book_token_cache = self.client.sha256_for_api("book", 60 * 60 * 24)
        return self._book_token_cache

    async def create_image(
        self, data: list, restricted_slots: bool, page: int
    ) -> Image.Image:
        """Creates the book image of the current page and returns it"""
        background = await self._get_background(0 if len(data) == 10 else 1)
        if restricted_slots:
            background = await self._numbers(background, data, page)
        background = await self._cards(background, data, 0 if len(data) == 10 else 1)
        background = self._set_page(background, page)
        return background

    def _get_from_cache(self, types: int) -> Union[Image.Image, None]:
        """Gets background from the cache if it exists, otherwise returns None"""
        if types == 0:
            if "first_page" in self.background_cache:
                return self.background_cache["first_page"]
        else:
            if "default_background" in self.background_cache:
                return self.background_cache["default_background"]

    def _set_cache(self, data: Image, first_page: bool) -> None:
        """Sets the background cache"""
        self.background_cache["first_page" if first_page else "default_background"] = (
            data
        )

    async def _get_background(self, types: int) -> Image.Image:
        """Gets the background image of the book"""

        endpoints = [
            "misc/book_first.png",
            "misc/book_default.png",
        ]
        url = [
            (self.base_url + "/image/" + x + "?token=" + self.book_token_cache[0] + "&expiry=" + self.book_token_cache[1])
            for x in endpoints
        ]

        if res := self._get_from_cache(types):
            return res.convert("RGBA")

        res = await self.session.get(url[types])
        image_bytes = await res.read()
        img = Image.open(BytesIO(image_bytes))
        img = img.resize((img.size[0] * self.scalar, img.size[1] * self.scalar))

        background = img.convert("RGBA")
        self._set_cache(img, types == 0)
        return background

    async def _get_card(self, url: str) -> Image.Image:
        """Gets a card image from the url"""
        res = await self.session.get(url)
        image_bytes = await res.read()
        image_card = Image.open(BytesIO(image_bytes)).convert("RGBA")
        image_card = image_card.resize((84 * self.scalar, 115 * self.scalar), Image.LANCZOS)
        # await asyncio.sleep(0.4) # This is to hopefully prevent aiohttp's "Response payload is not completed" bug
        return image_card

    def _set_page(self, image: Image.Image, page: int) -> Image.Image:
        """Gets the plain page background and sets the page number"""
        font = self._get_font(20 * self.scalar)
        draw = ImageDraw.Draw(image)
        draw.text((5 * self.scalar, 385 * self.scalar), f"{page*2-1}", (0, 0, 0), font=font)
        draw.text((595 * self.scalar, 385 * self.scalar), f"{page*2}", (0, 0, 0), font=font)
        return image

    def _get_font(self, size: int) -> ImageFont.ImageFont:
        font = ImageFont.truetype(
            str(Path(__file__).parent.parent.parent) + "/static/font.ttf",
            size,
            encoding="unic",
        )
        return font

    async def _cards(self, image: Image.Image, data: list, option: int) -> Image.Image:
        """Puts the cards on the background if there are any"""
        card_pos: list = [
            [
                (112, 143),
                (318, 15),
                (418, 15),
                (513, 15),
                (318, 142),
                (418, 142),
                (514, 142),
                (318, 269),
                (418, 269),
                (514, 269),
            ],
            [
                (12, 14),
                (112, 14),
                (207, 14),
                (12, 141),
                (112, 143),
                (208, 143),
                (13, 271),
                (112, 272),
                (209, 272),
                (318, 15),
                (417, 15),
                (513, 15),
                (318, 142),
                (418, 142),
                (514, 142),
                (318, 269),
                (418, 269),
                (514, 269),
            ],
        ]
        # Multiply all by scalar
        card_pos = [[(x * self.scalar, y * self.scalar) for x, y in i] for i in card_pos]
        for n, i in enumerate(data):
            if i:
                if i[1]:
                    if not str(i[0]) in self.card_cache:
                        self.card_cache[str(i[0])] = await self._get_card(i[1])

                    card = self.card_cache[str(i[0])]
                    image.paste(card, (card_pos[option][n]), card)
        return image

    async def _numbers(self, image: Image.Image, data: list, page: int) -> Image.Image:
        """Puts the numbers on the restricted slots in the book"""
        page -= 1
        numbers_pos: list = [
            [
                (130, 188),
                (338, 60),
                (436, 60),
                (536, 60),
                (338, 188),
                (436, 188),
                (536, 188),
                (338, 317),
                (436, 317),
                (536, 317),
            ],
            [
                (35, 60),
                (138, 60),
                (230, 60),
                (35, 188),
                (138, 188),
                (230, 188),
                (36, 317),
                (134, 317),
                (232, 317),
                (338, 60),
                (436, 60),
                (536, 60),
                (338, 188),
                (436, 188),
                (536, 188),
                (338, 317),
                (436, 317),
                (536, 317),
            ],
            [
                (30, 60),
                (132, 60),
                (224, 60),
                (34, 188),
                (131, 188),
                (227, 188),
                (32, 317),
                (130, 317),
                (228, 317),
                (338, 60),
                (436, 60),
                (533, 60),
                (338, 188),
                (436, 188),
                (533, 188),
                (338, 317),
                (436, 317),
                (533, 317),
            ],
            [
                (30, 60),
                (130, 60),
                (224, 60),
                (31, 188),
                (131, 188),
                (230, 188),
                (32, 317),
                (130, 317),
                (228, 317),
                (338, 60),
                (436, 60),
                (533, 60),
                (338, 188),
                (436, 188),
                (533, 188),
                (340, 317),
                (436, 317),
                (533, 317),
            ],
            [
                (30, 60),
                (130, 60),
                (224, 60),
                (31, 188),
                (131, 188),
                (230, 188),
                (32, 317),
                (133, 317),
                (228, 317),
                (338, 60),
                (436, 60),
                (533, 60),
                (338, 188),
                (436, 188),
                (533, 188),
                (338, 317),
                (436, 317),
                (535, 317),
            ],
            [
                (30, 60),
                (130, 60),
                (224, 60),
                (31, 188),
                (131, 188),
                (230, 188),
                (32, 317),
                (133, 317),
                (228, 317),
                (342, 60),
                (436, 60),
                (533, 60),
                (338, 188),
                (436, 188),
                (533, 188),
                (338, 317),
                (436, 317),
                (535, 317),
            ],
            [
                (30, 60),
                (130, 60),
                (224, 60),
                (31, 188),
                (131, 188),
                (230, 188),
                (32, 317),
                (133, 317),
                (228, 317),
                (342, 60),
                (436, 60),
                (533, 60),
                (338, 188),
                (436, 188),
                (533, 188),
                (338, 317),
                (436, 317),
                (535, 317),
            ],
        ]
        numbers_pos = [[(x * self.scalar, y * self.scalar) for x, y in i] for i in numbers_pos]

        font = self._get_font(35 * self.scalar)
        draw = ImageDraw.Draw(image)
        for n, i in enumerate(data):
            if i[1] is None:
                draw.text(numbers_pos[page][n], f"0{i[0]}" if i[0] > 9 else f"00{i[0]}", (165 * self.scalar, 165 * self.scalar, 165 * self.scalar), font=font)
        return image

    async def _get_book(
        self,
        user: discord.Member,
        page: int,
        client: Bot,
        just_fs_cards: bool = False,
    ) -> Tuple[discord.Embed, discord.File]:
        """Gets a formatted embed containing the book for the user"""
        rs_cards = []
        fs_cards = []
        person = await User.new(user.id)
        if just_fs_cards:
            page += 6

        # Bringing the list in the right format for the image generator
        if page < 7:
            if page == 1:
                i = 0
            else:
                i = 10 + ((page - 2) * 18)
                # By calculating where the list should start, I make the code faster because I don't need to
                # make a list of all cards and I also don't need to deal with a problem I had when trying to get
                # the right part out of the list. It also saves me lines!
            while not len(rs_cards) % 18 == 0 or len(rs_cards) == 0:
                # I killed my pc multiple times while testing, don't use while loops!
                if not i in [x[0] for x in person.rs_cards]:
                    rs_cards.append([i, None])
                else:
                    rs_cards.append(
                        [
                            i,
                            (Card(i)).formatted_image_url(client, to_fetch=True),
                        ]
                    )
                if page == 1 and len(rs_cards) == 10:
                    break
                i = i + 1
        else:
            i = (page - 7) * 18
            while (len(fs_cards) % 18 == 0) == False or (len(fs_cards) == 0) == True:
                try:
                    fs_cards.append(
                        [
                            person.fs_cards[i][0],
                            (Card(person.fs_cards[i][0])).formatted_image_url(
                                client, to_fetch=True
                            ),
                        ]
                    )
                except IndexError:
                    fs_cards.append(None)
                i = i + 1

        image = await self.create_image(
            rs_cards if (page <= 6 and not just_fs_cards) else fs_cards,
            (page <= 6 and not just_fs_cards),
            page,
        )

        buffer = BytesIO()
        image.save(buffer, "png")
        buffer.seek(0)

        f = discord.File(buffer, filename="image.png")
        embed = discord.Embed.from_dict(
            {
                "title": f"{user.display_name}'s book",
                "color": 0x2F3136,  # making the boarder "invisible" (assuming there are no light mode users)
                "image": {"url": "attachment://image.png"},
                "footer": {"text": ""},
            }
        )
        return embed, f

    async def create(
        self,
        user: discord.Member,
        page: int,
        just_fs_cards: bool = False,
    ) -> Tuple[discord.Embed, discord.File]:
        return await self._get_book(user, page, self.client, just_fs_cards)

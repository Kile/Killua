import discord
from discord.ext import commands

import re
import io
from typing import Union, Any, List, Coroutine, Optional, Literal
from PIL import Image, ImageDraw, ImageChops
from asyncio import wait_for, TimeoutError

from pypxl import PxlClient, pxl_object  # My own library ✨

from killua.bot import BaseBot
from killua.utils.gif import save_transparent_gif
from killua.utils.checks import check
from killua.static.enums import Category  # , SnapOptions, EyesOptions, FlagOptions
from killua.static.constants import NOKIA_CODE, PXLAPI, URL_REGEX


class ImageManipulation(commands.GroupCog, group_name="image"):

    def __init__(self, client: BaseBot):
        self.client = client
        self.wtf_meme = None
        self.wtf_meme_url = "https://i.redd.it/pvdxasy5z7k41.jpg"
        self.pxl = PxlClient(
            token=PXLAPI, stop_on_error=False, session=self.client.session
        )

    async def _get_image_bytes(self, url: str) -> io.BytesIO:
        """Gets the bytes from the image behind the url"""
        res = await self.client.session.get(url)
        _bytes = await res.read()
        return io.BytesIO(_bytes)

    def _crop_to_circle(self, im: Image.Image) -> Image.Image:
        """Crops the given image to a circle"""
        bigsize = (im.size[0] * 3, im.size[1] * 3)
        mask = Image.new("L", bigsize, 0)
        ImageDraw.Draw(mask).ellipse((0, 0) + bigsize, fill=255)
        mask = mask.resize(im.size, Image.LANCZOS)
        mask = ImageChops.darker(mask, im.split()[-1])
        im.putalpha(mask)

        return im.copy()

    def _create_frames(self, image: Image.Image) -> List[Image.Image]:
        """Creates the frames for the spin, sligtly rotating each frame"""
        res = []
        for i in range(17):
            res.append(image.rotate(i * 20 - 1))
        return res

    async def _create_spin_gif(self, url: str) -> io.BytesIO:
        """Takes in a url and returns io bytes of a spinning GIF"""
        image = Image.open(await self._get_image_bytes(url)).convert("RGB")
        # Crops the image to a square in the middle with the smallest side being the size of the largest side
        image = image.crop(
            (
                image.width / 2 - min(image.width, image.height) / 2,
                image.height / 2 - min(image.width, image.height) / 2,
                image.width / 2 + min(image.width, image.height) / 2,
                image.height / 2 + min(image.width, image.height) / 2,
            )
        )
        new_image = self._crop_to_circle(image)
        image.close()
        frames = self._create_frames(new_image)
        new_image.close()
        buffer = io.BytesIO()
        save_transparent_gif(
            frames, durations=1, save_file=buffer
        )  # making sure the gif is transparent. This is necessarry because of a pillow bug and slows this down quite significantly
        buffer.seek(0)
        return buffer

    def _put_horizontally(
        self, im1: Image.Image, im2: Image.Image, reduce_by: int = 5
    ) -> Image.Image:
        """Puts im2 below im2 with regards to each others sizes"""
        heigth_avatar = int(im2.width * (im1.height / im1.width))
        height_meme = int((heigth_avatar + im2.height) / reduce_by)

        dst = Image.new("RGBA", (im2.width, heigth_avatar + height_meme))

        im1 = im1.resize((im2.width, heigth_avatar))
        dst.paste(im1, (0, 0))
        im2 = im2.resize((im2.width, height_meme))
        dst.paste(im2, (0, heigth_avatar))
        return dst

    async def create_wtf_meme(self, url: str) -> io.BytesIO:
        """Puts a "excuse me what the frick" below the image provided"""
        if not self.wtf_meme:
            self.wtf_meme = await self._get_image_bytes(self.wtf_meme_url)

        image = Image.open(self.wtf_meme).copy().convert("RGBA")
        url_image = Image.open(await self._get_image_bytes(url)).convert("RGBA")

        buffer = io.BytesIO()
        self._put_horizontally(url_image, image).save(buffer, "PNG")
        buffer.seek(0)
        return buffer

    async def _validate_input(
        self, ctx: commands.Context, target: Optional[str]
    ) -> str:  # a useful check that looks for what url to pass pxlapi
        """Finds an image url to use from a command"""
        if target:
            try:
                m = await commands.MemberConverter().convert(ctx, target)
                return str(m.avatar.url)
            except commands.MemberNotFound:
                pass

            try:
                e = await commands.EmojiConverter().convert(ctx, target)
                return str(e.url)
            except commands.EmojiNotFound:
                pass

            if target.isdigit():
                try:
                    user = await self.client.fetch_user(int(target))
                    return str(user.avatar.url)
                except discord.NotFound:
                    pass
            else:
                url = re.search(URL_REGEX, target)
                # Makes sure the url is valid.
                # This check is not perfect but it works for most cases and if it's a false positive itdoesn't matter too much
                if not url:
                    pass
                else:
                    return url.group(0)

        if len(ctx.message.attachments) > 0:
            return ctx.message.attachments[0].url

        async for message in ctx.channel.history(limit=5):
            if len(message.attachments) > 0:
                return message.attachments[0].url
            elif len(message.embeds) > 0:
                embed = message.embeds[0]
                if embed.image:
                    return embed.image.url
                if embed.thumbnail:
                    return embed.thumbnail.url

        return str(
            ctx.author.avatar.url
        )  # if all else fails, return the author"s avatar

    async def handle_command(
        self,
        ctx: commands.Context,
        target: Union[discord.Member, discord.Emoji, str],
        function: Coroutine,
        t: Any = None,
        censor: bool = False,
        validate: bool = True,
    ) -> discord.Message:
        """Handles the command and returns the message"""
        if validate:
            data = await self._validate_input(ctx, target)
            if not data:
                return await ctx.send(
                    f"Invalid arguments passed. For help with the command, use `{self.client.command_prefix(self.client, ctx.message)[2]}help {ctx.command.name}`",
                    allowed_mentions=discord.AllowedMentions.none(),
                    ephemeral=True,
                )
        else:
            data = target

        await ctx.channel.typing()
        try:
            r: pxl_object.PxlObject = await wait_for(function(data, t), timeout=2)
        except TimeoutError:
            return await ctx.send(
                "The API took too long to respond. Please try again later (It is likely down)."
            )

        if r.success:
            f = discord.File(
                r.convert_to_ioBytes(),
                filename=f"{ctx.command.name}.{r.file_type}",
                spoiler=censor,
            )
            return await self.client.send_message(
                ctx,
                file=f,
                reference=ctx.message,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        if len(r.error) > 2000:
            return await ctx.send(
                f":x: An error occured with the API this command is using. The API is likely down. Please try again later."
            )
        return await ctx.send(
            f":x: " + r.error, allowed_mentions=discord.AllowedMentions.none()
        )

    async def flag_autocomplete(
        self, _: commands.Context, current: str
    ) -> List[discord.app_commands.Choice[str]]:
        """Returns a list of flags that match the current string since there are too many flags for it to use the options feature"""
        return [
            discord.app_commands.Choice(name=i, value=i)
            for i in self.pxl.flags
            if i.startswith(current)
        ][:25]

    @check(120)  # Big cooldown >_<
    @commands.hybrid_command(
        aliases=["ej", "emojimosaic"],
        extras={"category": Category.FUN, "id": 46},
        usage="emojaic <user/url>",
    )
    @discord.app_commands.describe(target="A user, url or emoji to take the image from")
    async def emojaic(self, ctx: commands.Context, target: str = None):
        """Emoji mosaic an image; let emojis recreate an image you gave Killua!"""

        async def func(data, *_):
            return await self.pxl.emojaic([data], groupSize=6)

        await self.handle_command(ctx, target, func)

    @check(5)
    @commands.hybrid_command(
        extras={"category": Category.FUN, "id": 47}, usage="flag <flag> <user/url>"
    )
    @discord.app_commands.describe(
        flag="The flag to overlay the image with",
        target="A user, url or emoji to take the image from",
    )
    @discord.app_commands.autocomplete(
        flag=flag_autocomplete
    )  # has to be done as autocomplete and not options because there are more than 25 flags
    async def flag(self, ctx: commands.Context, flag: str, target: str = None):
        """Overlay an image with a flag"""

        async def func(data, flag):
            return await self.pxl.flag(flag=flag, images=[data])

        await self.handle_command(ctx, target, func, flag)

    @check(5)
    @commands.hybrid_command(
        extras={"category": Category.FUN, "id": 48}, usage="glitch <user/url>"
    )
    @discord.app_commands.describe(target="A user, url or emoji to take the image from")
    async def glitch(self, ctx: commands.Context, target: str = None):
        """Tranform a users pfp into a glitchy GIF!"""

        async def func(data, *_):
            return await self.pxl.glitch(images=[data], gif=True)

        await self.handle_command(ctx, target, func)

    @check(10)
    @commands.hybrid_command(
        extras={"category": Category.FUN, "id": 49}, usage="lego <user/url>"
    )
    @discord.app_commands.describe(target="A user, url or emoji to take the image from")
    async def lego(self, ctx: commands.Context, target: str = None):
        """Legofies an image"""

        async def func(data, *_):
            return await self.pxl.lego(images=[data], scale=True, groupSize=10)

        await self.handle_command(ctx, target, func)

    @check(3)
    @commands.hybrid_command(
        aliases=["snap"],
        extras={"category": Category.FUN, "id": 50},
        usage="snapchat <filter> <user/url>",
    )
    @discord.app_commands.describe(
        filter="The snap filter to apply to the image",
        target="A user, url or emoji to take the image from",
    )
    async def snapchat(
        self,
        ctx: commands.Context,
        filter: Literal["dog", "dog2", "dog3", "pig", "flowers", "random"],
        target: str = None,
    ):
        """Put a snapchat filter on an image with a face"""

        async def func(data, filter):
            return await self.pxl.snapchat(filter=filter, images=[data])

        await self.handle_command(ctx, target, func, filter)

    @check(3)
    @commands.hybrid_command(
        aliases=["eye"],
        extras={"category": Category.FUN, "id": 51},
        usage="eyes <eye_type> <user/url>",
    )
    @discord.app_commands.describe(
        type="The type of eyes to put on the image",
        target="A user, url or emoji to take the image from",
    )
    async def eyes(
        self,
        ctx: commands.Context,
        type: Literal[
            "big",
            "black",
            "bloodshot",
            "blue",
            "default",
            "googly",
            "green",
            "horror",
            "illuminati",
            "money",
            "pink",
            "red",
            "small",
            "spinner",
            "spongebob",
            "white",
            "yellow",
            "random",
        ],
        target: str = None,
    ):
        """Put some crazy eyes on a person"""

        async def func(data, type):
            return await self.pxl.eyes(eyes=type, images=[data])

        await self.handle_command(ctx, target, func, type)

    @check(4)
    @commands.hybrid_command(
        aliases=["8bit", "blurr"],
        extras={"category": Category.FUN, "id": 52},
        usage="jpeg <user/url>",
    )
    @discord.app_commands.describe(target="A user, url or emoji to take the image from")
    async def jpeg(self, ctx: commands.Context, target: str = None):
        """Did you ever want to decrease image quality? Then this is the command for you!"""

        async def func(data, *_):
            return await self.pxl.jpeg(images=[data])

        await self.handle_command(ctx, target, func)

    @check(4)
    @commands.hybrid_command(
        extras={"category": Category.FUN, "id": 53}, usage="ajit <user/url>"
    )
    @discord.app_commands.describe(target="A user, url or emoji to take the image from")
    async def ajit(self, ctx: commands.Context, target: str = None):
        """Overlays an image of Ajit Pai snacking on some popcorn!"""

        async def func(data, *_):
            return await self.pxl.ajit(images=[data])

        await self.handle_command(ctx, target, func)

    @check()
    @commands.hybrid_command(
        extras={"category": Category.FUN, "id": 54}, usage="nokia <user/url>"
    )
    @discord.app_commands.describe(target="A user, url or emoji to take the image from")
    async def nokia(self, ctx: commands.Context, target: str = None):
        """Add the image onto a nokia display"""

        async def func(data, *_):
            d = 'const url = "' + data + ';"' + NOKIA_CODE
            return await self.pxl.imagescript(version="1.2.0", code=d)

        await self.handle_command(ctx, target, func)

    @check(4)
    @commands.hybrid_command(
        extras={"category": Category.FUN, "id": 55}, usage="flash <user/url>"
    )
    @discord.app_commands.describe(target="A user, url or emoji to take the image from")
    async def flash(self, ctx: commands.Context, target: str = None):
        """Greates a flashing GIF. WARNING FOR PEOPLE WITH EPILEPSY!"""

        async def func(data, *_):
            return await self.pxl.flash(images=[data])

        await self.handle_command(ctx, target, func, censor=True)

    @check(3)
    @commands.hybrid_command(
        extras={"category": Category.FUN, "id": 56}, usage="thonkify <text>"
    )
    @discord.app_commands.describe(text="The text to thonkify")
    async def thonkify(self, ctx: commands.Context, *, text: str):
        """Turn text into thonks!"""

        async def func(data, *_):
            return await self.pxl.thonkify(text=data)

        await self.handle_command(ctx, text, func, validate=False)

    @check(5)
    @commands.hybrid_command(
        aliases=["screen"],
        extras={"category": Category.FUN, "id": 57},
        usage="screenshot <url>",
    )
    @discord.app_commands.describe(website="The url of the website to screenshot")
    async def screenshot(self, ctx: commands.Context, website: str):
        """Screenshot the specified webste!"""

        async def func(data, *_):
            return await self.pxl.screenshot(url=data)

        await self.handle_command(ctx, website, func, validate=False)

    @check(2)
    @commands.hybrid_command(
        extras={"category": Category.FUN, "id": 58}, usage="sonic <text>"
    )
    @discord.app_commands.describe(text="The text to let sonic say")
    async def sonic(self, ctx: commands.Context, *, text: str):
        """Let sonic say anything you want"""

        async def func(data, *_):
            return await self.pxl.sonic(text=data)

        await self.handle_command(ctx, text, func, validate=False)

    @check(20)  # long check because this is exhausting for the poor computer
    @commands.hybrid_command(
        alises=["s"],
        extras={"category": Category.FUN, "id": 59},
        usage="spin <user/url>",
    )
    @discord.app_commands.describe(target="A user, url or emoji to take the image from")
    async def spin(self, ctx: commands.Context, target: str = None):
        """Spins an image 'round and 'round and 'round and 'round..."""
        data = await self._validate_input(ctx, target)
        if not data:
            return await ctx.send(
                f"Invalid arguments passed. For help with the command, use `{self.client.command_prefix(self.client, ctx.message)[2]}help {ctx.command.name}`",
                allowed_mentions=discord.AllowedMentions.none(),
            )

        await ctx.channel.typing()
        await ctx.send("Processing...", ephemeral=True)
        buffer = await self._create_spin_gif(data)
        await self.client.send_message(
            ctx,
            file=discord.File(fp=buffer, filename="spin.gif"),
            reference=ctx.message,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @check(10)
    @commands.hybrid_command(
        extras={"category": Category.FUN, "id": 60}, usage="wtf <user/url>"
    )
    @discord.app_commands.describe(target="A user, url or emoji to take the image from")
    async def wtf(self, ctx: commands.Context, target: str = None):
        """Puts the wtf meme below the image provided"""
        data = await self._validate_input(ctx, target)
        if not data:
            return await ctx.send(
                f"Invalid arguments passed. For help with the command, use `{self.client.command_prefix(self.client, ctx.message)[2]}help {ctx.command.name}`",
                allowed_mentions=discord.AllowedMentions.none(),
            )
        await ctx.channel.typing()
        await ctx.send("Processing...", ephemeral=True)
        buffer = await self.create_wtf_meme(data)
        await self.client.send_message(
            ctx,
            file=discord.File(fp=buffer, filename="wtf.png"),
            reference=ctx.message,
            allowed_mentions=discord.AllowedMentions.none(),
        )


Cog = ImageManipulation

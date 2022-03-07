import discord
from discord.ext import commands
from typing import Union, Any, List
import re
import io
from PIL import Image, ImageDraw, ImageChops

from pypxl import PxlClient # My own library ✨

from killua.utils.gif import save_transparent_gif
from killua.utils.checks import check
from killua.static.enums import Category
from killua.static.constants import NOKIA_CODE, PXLAPI

class ImageManipulation(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.wtf_meme = None
        self.wtf_meme_url = 'https://i.redd.it/pvdxasy5z7k41.jpg'
        self.pxl = PxlClient(token=PXLAPI, stop_on_error=False, session=self.client.session)

    async def _get_image_bytes(self, url: str) -> io.BytesIO:
        res = await self.client.session.get(url)
        _bytes = await res.read()
        return io.BytesIO(_bytes)

    def _crop_to_circle(self, im):
        bigsize = (im.size[0] * 3, im.size[1] * 3)
        mask = Image.new('L', bigsize, 0)
        ImageDraw.Draw(mask).ellipse((0, 0) + bigsize, fill=255)
        mask = mask.resize(im.size, Image.ANTIALIAS)
        mask = ImageChops.darker(mask, im.split()[-1])
        im.putalpha(mask)

        return im.copy()

    def _create_frames(self, image:Image.Image) -> List[Image.Image]:
        res = []
        for i in range(17):
            res.append(image.rotate(i*20-1))
        return res

    async def _create_spin_gif(self, url:str) -> io.BytesIO:
        """Takes in a url and returns the io bytes object"""
        image = Image.open(await self._get_image_bytes(url)).convert("RGB")

        new_image = self._crop_to_circle(image)
        image.close()
        frames = self._create_frames(new_image)
        new_image.close()
        buffer = io.BytesIO()
        save_transparent_gif(frames, durations=1, save_file=buffer) # making sure the gif is transparent. This is necessarry because of a pillow bug and slows this down quite significantly 
        buffer.seek(0)
        return buffer

    def _put_horizontally(self, im1: Image.Image, im2: Image.Image, reduce_by: int = 5) -> Image.Image:
        """Puts im2 below im2 with regards to each others sizes"""
        heigth_avatar = int(im2.width * (im1.height/im1.width))
        height_meme = int((heigth_avatar + im2.height)/reduce_by)

        dst = Image.new("RGBA", (im2.width, heigth_avatar + height_meme))

        im1 = im1.resize((im2.width, heigth_avatar))
        dst.paste(im1, (0, 0))
        im2 = im2.resize((im2.width, height_meme))
        dst.paste(im2, (0, heigth_avatar))
        return dst

    async def create_wtf_meme(self, avatar:str) -> io.BytesIO:
        if not self.wtf_meme:
            self.wtf_meme = await self._get_image_bytes(self.wtf_meme_url)

        image = Image.open(self.wtf_meme).copy().convert("RGBA")
        avatar_image = Image.open(await self._get_image_bytes(avatar)).convert("RGBA")

        buffer = io.BytesIO()
        self._put_horizontally(avatar_image, image).save(buffer, "PNG")
        buffer.seek(0)
        return buffer

    async def _validate_input(self, ctx, args): # a useful check that looks for what url to pass pxlapi
        image = None
        if isinstance(args, discord.Member):
            image = str(args.avatar.url)

        if isinstance(args, discord.PartialEmoji):
            image = str(args.url)
            
        if isinstance(args, str):
            if args.isdigit():
                try:
                    user = await self.client.fetch_user(int(args))
                    image = str(user.avatar.url)
                except discord.NotFound:
                    return None
            else:
                url = re.search(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))", args)
                if not url:
                    return None 
                else:
                    image = args

        if not image:
            if len(ctx.message.attachments) > 0:
                return ctx.message.attachments[0].url
                
            async for message in ctx.channel.history(limit=5):
                if len(message.attachments) > 0:
                    image = message.attachments[0].url
                    break
                elif len(message.embeds) > 0:
                    embed = message.embeds[0]
                    if embed.image:
                        image = embed.image.url
                        break
                    if embed.thumbnail:
                        image = embed.thumbnail.url
                        break
        if not image:
            image = str(ctx.author.avatar.url)  
        return image

    async def handle_command(self, ctx, args, function, t:Any=None, censor:bool=False, validate:bool=True):
        if validate:
            data = await self._validate_input(ctx, args)
            if not data:
                return await ctx.send(f'Invalid arguments passed. For help with the command, use `{self.client.command_prefix(self.client, ctx.message)[2]}help {ctx.command.name}`', allowed_mentions=discord.AllowedMentions.none())
        else:
            data = args
        r = await function(data, t)
        if r.success:
            f = discord.File(r.convert_to_ioBytes(), filename=f'{ctx.command.name}.{r.file_type}', spoiler=censor)
            return await self.client.send_message(ctx, file=f, reference=ctx.message, allowed_mentions=discord.AllowedMentions.none())
        return await ctx.send(f':x: '+r.error, allowed_mentions=discord.AllowedMentions.none())

    @check(120) # Big cooldown >_<
    @commands.command(aliases=['ej', 'emojimosaic'], extras={"category":Category.FUN}, usage="emojaic <user/url>")
    async def emojaic(self, ctx, args:Union[discord.Member, discord.PartialEmoji, str]=None):
        """Emoji mosaic an image; let emojis recreate an image you gave Killua! Takes in a mention, ID or image url"""
        async def func(data, *args):
            return await self.pxl.emojaic([data], groupSize=6)
        await self.handle_command(ctx, args, func)

    @check(5)
    @commands.command(extras={"category":Category.FUN}, usage="flag <flag> <user/url>")
    async def flag(self, ctx, flag:str, args:Union[discord.Member, discord.PartialEmoji, str]=None):
        """Valid flags: asexual, aromantic, bisexual, pansexual, gay, lesbian, trans, nonbinary, genderfluid, genderqueer, polysexual, austria, belgium, botswana, bulgaria, ivory, estonia, france, gabon, gambia, germany, guinea, hungary, indonesia, ireland, italy, luxembourg, monaco, nigeria, poland, russia, romania, sierraleone, thailand, ukraine, yemen"""
        async def func(data, flag):
            return await self.pxl.flag(flag=flag.lower(), images=[data])
        await self.handle_command(ctx, args, func, flag)

    @check(5)
    @commands.command(extras={"category":Category.FUN}, usage="glitch <user/url>")
    async def glitch(self, ctx, args:Union[discord.Member, discord.PartialEmoji, str]=None):
        """Tranform a users pfp into a glitchy GIF!"""
        async def func(data, *args):
            return await self.pxl.glitch(images=[data], gif=True)
        await self.handle_command(ctx, args, func)

    @check(10)
    @commands.command(extras={"category":Category.FUN}, usage="lego <user/url>")
    async def lego(self, ctx, args:Union[discord.Member, discord.PartialEmoji, str]=None):
        """Legofies an image"""
        async def func(data, *args):
            return await self.pxl.lego(images=[data], scale=True, groupSize=10)
        await self.handle_command(ctx, args, func)

    @check(3)
    @commands.command(aliases=['snap'], extras={"category":Category.FUN}, usage="snapchat <filter> <user/url>")
    async def snapchat(self, ctx, fil:str, args:Union[discord.Member, discord.PartialEmoji, str]=None):
        """Valid filters: dog, dog2, dog3, pig, flowers, random"""
        async def func(data, fil):
            return await self.pxl.snapchat(filter=fil.lower(), images=[data])
        await self.handle_command(ctx, args, func, fil)

    @check(3)
    @commands.command(aliases=['eye'], extras={"category":Category.FUN}, usage="eyes <eye_type> <user/url>")
    async def eyes(self, ctx, t:str, args:Union[discord.Member, discord.PartialEmoji, str]=None):
        """Valid eyes: big, black, bloodshot, blue, default, googly, green, horror, illuminati, money, pink, red, small, spinner, spongebob, white, yellow, random"""
        async def func(data, t):
            return await self.pxl.eyes(eyes=t.lower(), images=[data])
        await self.handle_command(ctx, args, func, t)

    @check(4)
    @commands.command(aliases=['8bit', 'blurr'], extras={"category":Category.FUN}, usage="jpeg <user/url>")
    async def jpeg(self, ctx, args:Union[discord.Member, discord.PartialEmoji, str]=None):
        """Did you ever want to decrease image quality? Then this is the command for you!"""
        async def func(data, *args):
            return await self.pxl.jpeg(images=[data])
        await self.handle_command(ctx, args, func)

    @check(4)
    @commands.command(extras={"category":Category.FUN}, usage="ajit <user/url>")
    async def ajit(self, ctx, args:Union[discord.Member, discord.PartialEmoji, str]=None):
        """  Overlays an image of Ajit Pai snacking on some popcorn!"""
        async def func(data, *args):
            return await self.pxl.ajit(images=[data])
        await self.handle_command(ctx, args, func)

    @check()
    @commands.command(extras={"category":Category.FUN}, usage="nokia <user/url>")
    async def nokia(self, ctx, args:Union[discord.Member, discord.PartialEmoji, str]=None):
        """Add the image onto a nokia display"""
        async def func(data, *args):
            d = "const url = '" + data + ";'" + NOKIA_CODE
            return await self.pxl.imagescript(version="1.2.0", code=d)
        await self.handle_command(ctx, args, func)

    @check(4)
    @commands.command(extras={"category":Category.FUN}, usage="flash <user/url>")
    async def flash(self, ctx, args:Union[discord.Member, discord.PartialEmoji, str]=None):
        """Greates a flashing GIF"""
        async def func(data, *args):
            return await self.pxl.flash(images=[data])
        await self.handle_command(ctx, args, func, censor=True)

    @check(3)
    @commands.command(extras={"category":Category.FUN}, usage="thonkify <text>")
    async def thonkify(self, ctx, *, text:str):
        """Turn text into thonks!"""
        async def func(data, *args):
            return await self.pxl.thonkify(text=data)
        await self.handle_command(ctx, text, func, validate=False)

    @check(5)
    @commands.command(aliases=['screen'], extras={"category":Category.FUN}, usage="screenshot <url>")
    async def screenshot(self, ctx, website:str):
        """Screenshot the specified webste!"""
        async def func(data, *args):
            return await self.pxl.screenshot(url=data)
        await self.handle_command(ctx, website, func, validate=False)

    @check(2)
    @commands.command(extras={"category":Category.FUN}, usage="sonic <text>")
    async def sonic(self, ctx, *, text:str):
        """Let sonic say anything you want"""
        async def func(data, *args):
            return await self.pxl.sonic(text=data)
        await self.handle_command(ctx, text, func, validate=False)

    @check(2)
    @commands.command(aliases=['g','search'], extras={"category":Category.FUN}, usage="google <query>")
    async def google(self, ctx, *, query:str):
        """Get the best results for a query the web has to offer"""
        
        r = await self.pxl.web_search(query=query)
        if r.success:
            results = r.data['results']
            embed = discord.Embed.from_dict({
                'title': f'Results for query {query}',
                'color': 0x1400ff,
            })
            for i in range(4 if len(results) >= 4 else len(results)):
                res = results[i-1]
                embed.add_field(name='** **', value=f'**[__{res["title"]}__]({res["url"]})**\n{res["description"][:100]}...' if len(res["description"]) > 100 else res["description"], inline=False)
            return await self.client.send_message(ctx, embed=embed)
        return await ctx.send(':x: '+r.error)

    @check(30) # long check because this is exhausting for the poor computer
    @commands.command(alises=["s"], extras={"category": Category.FUN}, usage="spin <user/url>")
    async def spin(self, ctx, args:Union[discord.Member, discord.PartialEmoji, str]=None):
        """Spins an image 'round and 'round and 'round and 'round..."""
        data = await self._validate_input(ctx, args)
        if not data:
            return await ctx.send(f'Invalid arguments passed. For help with the command, use `{self.client.command_prefix(self.client, ctx.message)[2]}help {ctx.command.name}`', allowed_mentions=discord.AllowedMentions.none())

        async with ctx.typing():
            msg = await ctx.send("Processing...")
            buffer = await self._create_spin_gif(data)
            await msg.delete()
            await self.client.send_message(ctx, file=discord.File(fp=buffer, filename="spin.gif"), reference=ctx.message, allowed_mentions=discord.AllowedMentions.none())

    @check(10)
    @commands.command(extras= {"category": Category.FUN}, usage= "wtf <user/url>")
    async def wtf(self, ctx, args:Union[discord.Member, discord.PartialEmoji, str]=None):
        """Puts the wtf meme below the image provided"""
        data = await self._validate_input(ctx, args)
        if not data:
            return await ctx.send(f'Invalid arguments passed. For help with the command, use `{self.client.command_prefix(self.client, ctx.message)[2]}help {ctx.command.name}`', allowed_mentions=discord.AllowedMentions.none())

        buffer = await self.create_wtf_meme(data)
        await self.client.send_message(ctx, file=discord.File(fp=buffer, filename="wtf.png"), reference=ctx.message, allowed_mentions=discord.AllowedMentions.none())

Cog = ImageManipulation

def setup(client):
    client.add_cog(ImageManipulation(client))
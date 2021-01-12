from PIL import Image
from io import BytesIO
import aiohttp
import discord
import logging
import os
import secrets
import subprocess

from redbot.core import commands, checks, Config
from redbot.core.data_manager import cog_data_path

log = logging.getLogger("red.aikaterna.antiphoneclapper")


class AntiPhoneClapper(commands.Cog):
    """This cog deletes bad GIFs and MP4s that will crash phone clients."""

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete."""
        return

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 2719371001, force_registration=True)

        default_guild = {"watching": []}

        self.config.register_guild(**default_guild)

    @commands.group()
    @checks.mod_or_permissions(administrator=True)
    @commands.guild_only()
    async def nogif(self, ctx):
        """Configuration options."""
        pass

    @nogif.command()
    async def watch(self, ctx, channel: discord.TextChannel):
        """
        Add a channel to watch. 
        Gif and MP4 attachments and links that break mobile clients will be removed in these channels.
        """
        channel_list = await self.config.guild(ctx.guild).watching()
        if channel.id not in channel_list:
            channel_list.append(channel.id)
        await self.config.guild(ctx.guild).watching.set(channel_list)
        await ctx.send(f"{self.bot.get_channel(channel.id).mention} will have bad gifs removed.")

    @nogif.command()
    async def watchlist(self, ctx):
        """List the channels being watched."""
        channel_list = await self.config.guild(ctx.guild).watching()
        msg = "Bad gifs will be removed in:\n"
        for channel in channel_list:
            channel_obj = self.bot.get_channel(channel)
            msg += f"{channel_obj.mention}\n"
        await ctx.send(msg)

    @nogif.command()
    async def unwatch(self, ctx, channel: discord.TextChannel):
        """Remove a channel from the watch list."""
        channel_list = await self.config.guild(ctx.guild).watching()
        if channel.id in channel_list:
            channel_list.remove(channel.id)
        else:
            return await ctx.send("Channel is not being watched.")
        await self.config.guild(ctx.guild).watching.set(channel_list)
        await ctx.send(f"{self.bot.get_channel(channel.id).mention} will not have bad gifs removed.")

    @commands.Cog.listener()
    async def on_message(self, m):
        if not m.channel.guild:
            return
        if m.author.bot:
            return
        watch_channel_list = await self.config.guild(m.guild).watching()
        if not watch_channel_list:
            return
        if m.channel.id not in watch_channel_list:
            return

        link = False
        phone_clapper = None

        if m.content:
            if m.content.startswith("https://cdn.discordapp.com/attachments/"):
                link = True

        if not link:
            for att in m.attachments:
                if att.size > 8000000:
                    continue
                if att.filename.endswith(".mp4"):
                    phone_clapper = await self._is_video_clapper(att.url)
                if att.filename.endswith(".gif"):
                    phone_clapper = await self._is_image_clapper(att.url)
        else:
            maybe_url = m.content.split()[0]
            if maybe_url.endswith(".mp4"):
                phone_clapper = await self._is_video_clapper(maybe_url)
            if maybe_url.endswith(".gif"):
                phone_clapper = await self._is_image_clapper(maybe_url)

        if phone_clapper:
            try:
                await m.delete()
                await m.channel.send(f"{m.author.mention} just tried to send a bad file and I removed it.")
                return
            except discord.errors.Forbidden:
                await m.channel.send(f"Don't send malicious files, {m.author.mention}")
                log.debug(f"Failed to delete message ({m.id}) that contained a Discord killing gif or mp4 video.")
                return
        else:
            return

    def is_phone_clapper(self, im):
        limit = im.size
        tile_sizes = []
        for frame in range(im.n_frames):
            im.seek(frame)
            tile_sizes.append(im.tile[0][1][2:])
        return any([x[0] > limit[0] or x[1] > limit[1] for x in tile_sizes])

    async def _is_image_clapper(self, url):
        async with aiohttp.ClientSession() as session:
            async with session.get(att.url) as resp:
                data = await resp.content.read()
                f = BytesIO(data)
                try:
                    img = Image.open(f)
                    phone_clapper = self.is_phone_clapper(img)
                    return False
                except Image.DecompressionBombError:
                    return True

    async def _is_video_clapper(self, input_file):
        r = secrets.token_hex(6)
        video_name = f"temp_vid_{r}.mp4"
        video_file = f"{cog_data_path(self)}/{video_name}"
        text_name = f"temp_output_{r}.txt"
        text_file = f"{cog_data_path(self)}/{text_name}"

        async with aiohttp.ClientSession() as session:
            async with session.get(input_file) as resp:
                data = await resp.content.read()
                with open(video_file, "wb+") as g:
                    g.write(data)

        f = open(text_file, "wb+")
        try:
            result = self.bot.loop.run_in_executor(None, subprocess.call(["ffplay.exe", video_file, "-autoexit", "-loglevel", "+debug"], stdout=f, stderr=subprocess.STDOUT, timeout=60))
        except subprocess.CalledProcessError as e:
            log.error(e.output)
            return
        except subprocess.TimeoutExpired:
            f.close()
            os.remove(video_file)
            os.remove(text_file)
            log.error("Timeout expired trying to read a video file")
            return
        result.cancel()
        f.close()

        f = open(text_file, "r")
        content = f.read()

        if "Video frame changed from size:" in content:
            phone_clapper = True
        else:
            phone_clapper = False

        f.close()
        os.remove(video_file)
        os.remove(text_file)

        return phone_clapper

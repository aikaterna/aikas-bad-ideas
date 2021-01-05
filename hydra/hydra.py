import asyncio
import discord
import lavalink
from redbot.core import checks, commands, Config
from redbot.core.utils.chat_formatting import bold, box, humanize_list


class Hydra(commands.Cog):
    def __init__(self, bot):
        self.bot: Red = bot
        self.config = Config.get_conf(self, identifier=2713931003)

        default_global = {"channels": []}
        self.config.register_global(**default_global)

        lavalink.register_event_listener(self._hydra_listener)
        self._lock = {}

    @checks.is_owner()
    @commands.command()
    async def hydraadd(self, ctx, channel: discord.TextChannel = None):
        """Add a channel to listen to."""
        if not channel:
            channel = ctx.channel
        perms = await self._channel_perm_checker(channel)
        audio_cog = self.bot.get_cog("Audio")
        cleanup_cog = self.bot.get_cog("Cleanup")
        if (not perms) or (not audio_cog) or (not cleanup_cog):
            msg = f"I need send messages, embed links, add reactions, and manage messages permissions in {channel.mention}. "
            msg += "The Audio and Cleanup cogs must also be loaded. "
            msg += "Re-add this channel with this command when those requirements are in place."
            return await ctx.send(msg)

        channel_list = await self.config.channels()
        if channel.id not in channel_list:
            channel_list.append(channel.id)
            await self.config.channels.set(channel_list)
            await ctx.send(f"{channel.mention} was added to the song request channels.", delete_after=5)
            await ctx.message.delete()
            await self._setup(channel)
        else:
            await ctx.send(f"{channel.mention} was already in the list of song request channels.", delete_after=5)

    @checks.is_owner()
    @commands.command()
    async def hydraremove(self, ctx, channel: discord.TextChannel = None):
        """Remove a channel for listening."""
        if not channel:
            channel = ctx.channel
        channel_list = await self.config.channels()
        if channel.id in channel_list:
            channel_list.remove(channel.id)
            await self.config.channels.set(channel_list)
            await ctx.send(f"{channel.mention} was removed from the song request channels.")
        else:
            await ctx.send(f"{channel.mention} was not in the list.")

    @checks.is_owner()
    @commands.command()
    async def hydrasettings(self, ctx):
        """Show the current settings."""
        msg = f"[Settings for {ctx.guild.name}]\n"
        channel_list = await self.config.channels()
        in_server = [
            x for x in channel_list if x in [x.id for x in ctx.guild.channels if isinstance(x, discord.TextChannel)]
        ]
        if len(in_server) == 0:
            chans = "None."
        else:
            chans = humanize_list(in_server)
        msg += f"Channels: {chans}\n"
        await ctx.send(box(msg, lang="ini"))

    @staticmethod
    async def _channel_perm_checker(channel):
        if not channel.permissions_for(channel.guild.me).send_messages:
            return False
        elif not channel.permissions_for(channel.guild.me).embed_links:
            return False
        elif not channel.permissions_for(channel.guild.me).add_reactions:
            return False
        elif not channel.permissions_for(channel.guild.me).manage_messages:
            return False
        else:
            return True

    async def _cleanup_routine(self, ctx):
        audio_cog = self.bot.get_cog("Audio")
        cleanup_cog = self.bot.get_cog("Cleanup")
        await cleanup_cog.messages(ctx=ctx, number=10)
        self._lock[str(ctx.guild.id)] = False
        await audio_cog.command_queue(ctx=ctx)
        async for msg in ctx.channel.history(limit=1):
            try:
                await msg.remove_reaction("\N{INFORMATION SOURCE}\N{VARIATION SELECTOR-16}", self.bot.user)
            except (AttributeError, IndexError):
                continue

    async def _hydra_listener(self, player, event, reason):
        if event == lavalink.LavalinkEvents.TRACK_START:
            audio_cog = self.bot.get_cog("Audio")
            cleanup_cog = self.bot.get_cog("Cleanup")
            channel_id = player.fetch("hydra-text-channel", None)
            if channel_id:
                channel_obj = self.bot.get_channel(channel_id)
                async for msg in channel_obj.history(limit=1):
                    ctx = await self.bot.get_context(msg)
                    if len(msg.embeds) > 0:
                        if msg.embeds[0].title.startswith("Queue for "):
                            await cleanup_cog.messages(ctx=ctx, number=1)
                            await audio_cog.command_queue(ctx=ctx)

    async def _setup(self, channel):
        img_header = "https://cdn.discordapp.com/attachments/376048873929572352/795904443035287602/cat_meows_at.png"
        msg = bold("Drop a song URL in chat or tell me what you want to listen to.\n")
        msg += f"Use words like `skip`, `stop`, `prev`, and `seek` to control the music once it's playing."
        e = discord.Embed()
        e.add_field(name=f"Hi, I'm {self.bot.user.name}!\n", value=msg)
        e.set_thumbnail(url=self.bot.user.avatar_url_as())
        e.set_image(url=img_header)
        header_msg = await channel.send(embed=e)
        try:
            await header_msg.pin()
        except discord.errors.HTTPException:
            pass

    @commands.Cog.listener()
    async def on_message_without_command(self, message):
        if not message.guild:
            return
        if message.author.bot:
            return
        perms = await self._channel_perm_checker(message.channel)
        if not perms:
            return
        channel_list = await self.config.channels()
        if not channel_list:
            return
        if message.channel.id not in channel_list:
            return
        audio_cog = self.bot.get_cog("Audio")
        if not audio_cog:
            return

        try:
            self._lock[str(message.guild.id)]
        except KeyError:
            self._lock[str(message.guild.id)] = False

        if self._lock[str(message.guild.id)] == True:
            return
        self._lock[str(message.guild.id)] = True

        try:
            player = lavalink.get_player(message.guild.id)
        except IndexError:
            return
        except KeyError:
            vc = message.author.voice
            if vc:
                if not vc.channel.permissions_for(message.guild.me).connect:
                    return
                await lavalink.connect(vc.channel)
                player = lavalink.get_player(message.guild.id)

        player.store("hydra-text-channel", message.channel.id)
        ctx = await self.bot.get_context(message)
        commands = ["skip", "stop", "prev", "seek"]
        word = message.content.split(" ")[0]
        if word in commands:
            if word == "skip":
                await audio_cog.command_skip(ctx=ctx)
                await asyncio.sleep(1)
                await self._cleanup_routine(ctx)
                return
            if word == "seek":
                await audio_cog.command_seek(ctx=ctx, seconds=message.content.split(" ")[1])
                await asyncio.sleep(1)
                await self._cleanup_routine(ctx)
                return
            if word == "prev":
                await audio_cog.command_prev(ctx=ctx)
                await asyncio.sleep(1)
                await self._cleanup_routine(ctx)
                return
            if word == "stop":
                await audio_cog.command_stop(ctx=ctx)
                await asyncio.sleep(1)
                await self._cleanup_routine(ctx)
                return

        await audio_cog.command_play(ctx=ctx, query=message.content)
        await self._cleanup_routine(ctx)

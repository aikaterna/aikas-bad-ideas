import aiohttp
import re

from redbot.core import commands


IPV4_RE = re.compile("\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}")
IPV6_RE = re.compile("([a-f0-9:]+:+)+[a-f0-9]+")


class IPNotify(commands.Cog):
    """What's the bot's IP address?"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    async def checkip(self, ctx: commands.Context):
        """What's the bot's IP address?"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://checkip.dyndns.com/") as resp:
                    result = await resp.text()
                    ip_match = IPV4_RE.search(result)
                    if ip_match:
                        return await ctx.send(f"My IP address is: {ip_match.group(0)}")
                    else:
                        ip_match = IPV6_RE.search(result)
                    if ip_match:
                        return await ctx.send(f"My IP address is: {ip_match.group(0)}")
                    else:
                        return await ctx.send("I can't find my ip address...")

        except aiohttp.ClientConnectionError:
            return await ctx.send("Looks like there was a connection error when I tried to do that.")

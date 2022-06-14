from .ipnotify import IPNotify


async def setup(bot):
    n = IPNotify(bot)
    bot.add_cog(n)

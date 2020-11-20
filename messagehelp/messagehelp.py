from redbot.core import commands, checks, Config
from redbot.core.utils.chat_formatting import box, pagify


class MessageHelp(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 2769001001, force_registration=True)

        default_global = {
            "message": "A bot owner needs to set my help message with the `sethelp message` command.",
            "old_help": False,
        }

        self.config.register_global(**default_global)

    @commands.command(name="help", hidden=True)
    async def message_help(self, ctx, *, command_or_category_name: str = None):
        """HELP!"""
        # send old help if toggle is enabled
        old_help = await self.config.old_help()
        if old_help:
            return await ctx.bot.send_help_for(ctx, command_or_category_name)

        # otherwise send special help
        help_message = await self.config.message()
        await ctx.send(help_message)

    @checks.is_owner()
    @commands.command(name="oldhelp", hidden=True)
    async def old_help_message(self, ctx, *, command_or_category_name: str = None):
        """Old help command functionality."""
        await ctx.bot.send_help_for(ctx, command_or_category_name)

    @checks.is_owner()
    @commands.group()
    async def sethelp(self, ctx):
        """Custom message help settings."""
        pass

    @sethelp.command()
    async def message(self, ctx, *, message: str):
        """Set the message shown when regular users use the help command."""
        await self.config.message.set(message)
        await ctx.send("Done.")

    @sethelp.command()
    async def oldhelp(self, ctx, true_or_false: bool = None):
        """Toggle sending new or old help."""
        if true_or_false is None:
            old_help = await self.config.old_help()
            await self.config.old_help.set(not old_help)
            await ctx.send(f"Old help message style: {not old_help}")
        else:
            await self.config.old_help.set(true_or_false)
            await ctx.send(f"Old help message style: {true_or_false}")

    @sethelp.command()
    async def settings(self, ctx):
        """Show the help settings."""
        global_config = await self.config.all()
        msg = "[ Custom Help Settings ]\n\n"
        msg += f"Message:     {global_config['message']}\n"
        msg += f"Custom Help: {'Disabled' if global_config['old_help'] else 'Enabled'}"
        for page in pagify(msg):
            await ctx.send(box(page, lang="ini"))

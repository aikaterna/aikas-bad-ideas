from .messagehelp import MessageHelp


def setup(bot):
    n = MessageHelp(bot)
    cmds = ["help"]
    for cmd_name in cmds:
        old_cmd = bot.get_command(cmd_name)
        if old_cmd:
            bot.remove_command(old_cmd.name)
    bot.add_cog(n)

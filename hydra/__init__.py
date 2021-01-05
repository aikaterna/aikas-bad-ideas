from .hydra import Hydra


def setup(bot):
    bot.add_cog(Hydra(bot))

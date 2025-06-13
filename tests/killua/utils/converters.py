from discord.ext import commands

from datetime import timedelta
from re import compile

time_regex = compile(r"(\d{1,5}(?:[.,]?\d{1,5})?)([smhd])")
time_dict = {"h": 3600, "s": 1, "m": 60, "d": 86400}

class TimeConverter(commands.Converter):
    async def convert(self, _: commands.Context, argument: str) -> timedelta:
        matches = time_regex.findall(argument.lower())
        time = 0
        for v, k in matches:
            try:
                time += time_dict[k]*float(v)
            except KeyError:
                raise commands.BadArgument("{} is an invalid time-key! h/m/s/d are valid!".format(k))
            except ValueError:
                raise commands.BadArgument("{} is not a number!".format(v))

        if time > 2419200:
            raise commands.BadArgument("The maximum time allowed is 28 days!")

        return timedelta(seconds=time)
from datetime import datetime, timedelta
from random import randrange

INCREMENT = 0


def random_date() -> int:
    start_date = datetime(2015, 1, 1)
    end_date = datetime.now()

    time_between_dates = end_date - start_date
    days_between_dates = time_between_dates.days
    random_number_of_days = randrange(days_between_dates)
    return start_date + timedelta(days=random_number_of_days)


# Adapted from https://github.com/discordjs/discord.js/blob/stable/src/util/SnowflakeUtil.js#L30
# and translated into python
def get_random_discord_id(time: datetime = None) -> int:
    global INCREMENT
    INCREMENT += 1
    if INCREMENT >= 4095:
        INCREMENT = 0
    if not time:
        time = random_date()
    return int((int(time.timestamp()) - 1420070400) * 100 << 22 | 1 << 17 | INCREMENT)


def random_name() -> str:
    """Creates a random username"""
    return "".join([chr(randrange(97, 123)) for _ in range(randrange(4, 16))])

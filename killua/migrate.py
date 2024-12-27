"""
This file contains one function, `migrate`, which is used to migrate the database from one version to another once when 
an update is released. It can be run through the command line with `python3 -m killua --migrate`
"""

import logging
from typing import Type
from motor.motor_asyncio import AsyncIOMotorCollection as Collection
from discord.ext.commands import AutoShardedBot, HybridGroup
from killua.static.constants import DB


async def migrate_requiring_bot(bot: Type[AutoShardedBot]):
    """
    Migrates the database from one version to another, requiring a bot instance. Automatically called when the bot starts if `--migrate` was run before.
    """
    logging.info("Migrating database...")
    const: Collection = DB._DB["const"]

    usage: dict = (await const.find_one({"_id": "usage"}))["command_usage"]

    logging.info("Attemping to migrate edge cases...")
    usage["games gstats"] = usage.get("games stats", 0)
    usage["games gstats"] += usage.get("gstats", 0)
    usage.pop("games stats", None)
    usage.pop("gstats", None)

    usage["games gleaderboard"] = usage.get("games leaderboard", 0)
    usage["games gleaderboard"] += usage.get("gleaderboard", 0)
    usage.pop("games stats", None)
    usage.pop("gstats", None)

    # Handle edge case
    usage["web novel"] = usage.get("web book", 0)
    usage["web novel"] += usage.get("novel", 0)
    usage.pop("web book", None)
    usage.pop("novel", None)

    logging.info("Edge cases done, migrating different command group names...")

    def update(to_update: dict, _update: int, key: str) -> dict:
        if key in to_update:
            to_update[key] += _update
        else:
            to_update[key] = _update
        return to_update

    for item in usage.keys():
        if "moderation" in item:
            before = item
            item.replace("moderation", "mod")
            usage = update(usage, usage[before], item)
            usage[before] = -1
        elif "miscillaneous" in item:
            before = item
            item.replace("miscillaneous", "misc")
            usage = update(usage, usage[before], item)
            usage[before] = -1
        elif "economy" in item:
            before = item
            item.replace("economy", "econ")
            usage = update(usage, usage[before], item)
            usage[before] = -1

    usage = {k: v for k, v in usage.items() if v > -1}

    logging.info(
        "Fininished migrating different command group names, migrating command usage..."
    )

    for command in bot.walk_commands():
        if "jishaku" in command.qualified_name:
            continue
        if isinstance(command, HybridGroup):
            continue

        if command.name in usage:
            if command.qualified_name in usage:
                usage[command.qualified_name] += usage[command.name]
            else:
                usage[command.qualified_name] = usage[command.name]
            del usage[command.name]

    new = {}
    for command in bot.tree.get_commands():
        if hasattr(command, "commands"):
            for sub in command.commands:
                if sub.qualified_name in usage:
                    cmd = bot.get_command(sub.qualified_name)
                    if not cmd:
                        cmd = bot.get_command(sub.name)
                    extras = cmd.extras
                    new[str(extras["id"])] = usage[sub.qualified_name]

    logging.info("Finished migrating command usage, updating database...")

    const.update_one({"_id": "usage"}, {"$set": {"command_usage": new}})
    logging.info("successfully migrated command usage")


def migrate():
    """
    Migrates the database from one version to another
    """
    const = DB._DB["const"]
    const.update_one({"_id": "migrate"}, {"$set": {"value": True}})
    logging.info("Set migrate to True")

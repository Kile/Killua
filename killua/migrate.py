"""
This file contains one function, `migrate`, which is used to migrate the database from one version to another once when 
an update is released. It can be run through the command line with `python3 -m killua --migrate`
"""
from typing import Type
from pymongo.collection import Collection
from discord.ext.commands import AutoShardedBot, HybridGroup
from killua.static.constants import DB, CLUSTER

def migrate_requiring_bot(bot: Type[AutoShardedBot]):
    """
    Migrates the database from one version to another, requiring a bot instance. Automatically called when the bot starts if `--migrate` was run before.
    """
    const: Collection = DB._DB["const"]

    if bot.is_dev:
        const.insert_one({"_id": "usage", "command_usage": {}})
        const.update_one({"_id": "migrate"}, {"$set": {"value": False}}) # Only migrate once
        return

    # Migrate the current command usage statistics the const collecting, adjusting its values
    coll: Collection = DB._DB["stats"]
    usage = coll.find_one({"_id": "commands"})["command_usage"]

    new = {}

    # First handle case of already corrupt data
    usage["8ball"] += usage["ball"]
    del usage["ball"]

    # Handle edge case
    usage["misicillaneous info"] = usage["info"]
    del usage["info"]

    usage["economy leaderboard"] = usage["leaderboard"]
    del usage["leaderboard"]

    usage["economy guild"] = usage["guild"]
    del usage["guild"]

    usage["shush"] = usage["mute"]
    usage["unshush"] = usage["unmute"]

    for command in bot.walk_commands():

        if "jishaku" in command.qualified_name:
            continue
        for key, val in usage.items():
            if key == command.qualified_name and not isinstance(command, HybridGroup):
                new[command.qualified_name] = val
            elif key == command.name and not isinstance(command, HybridGroup):
                new[command.qualified_name] = val

    const.insert_one({"_id": "usage", "command_usage": new})
    const.update_one({"_id": "migrate"}, {"$set": {"value": False}}) # Only migrate once

def migrate():
    """
    Migrates the database from one version to another
    """
    
    # Migrate single item collection into a new "const" collection
    const: Collection = DB._DB["const"]
    GDB: Collection = CLUSTER["general"]

    # shop
    const.insert_one({"_id": "shop", "offers": [], "log": []})
    # custom presence
    const.insert_one({"_id": "presence", "text": None, "activity": None, "presence": None})
    # updates
    const.insert_one({"_id": "updates", "updates": []})
    # stats (growth)
    const.insert_one({"_id": "growth", "growth": []}) 
    # blacklist
    const.insert_one({"_id": "blacklist", "blacklist": []})

    # Transfer all todo lists to another namespace
    todo: Collection = DB._DB["todo"]
    old_todo: Collection = CLUSTER["general"]["todo"]
    for todo_list in old_todo.find():
        todo.insert_one(todo_list)

    # Ensure `migrate_requiring_bot` is called when the bot starts
    const.insert_one({"_id": "migrate", "value": True})
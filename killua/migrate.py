"""
This file contains one function, `migrate`, which is used to migrate the database from one version to another once when 
an update is released. It can be run through the command line with `python3 -m killua --migrate`
"""
import discord
import logging
from asyncio import sleep
from typing import Type, cast
from pymongo.asynchronous.collection import AsyncCollection as Collection
from discord.ext.commands import AutoShardedBot, HybridGroup
from killua.static.constants import DB


async def migrate_requiring_bot(bot: Type[AutoShardedBot]):
    """
    Migrates the database from one version to another, requiring a bot instance. Automatically called when the bot starts if `--migrate` was run before.
    """
    logging.info("Migrating database...")

    for i, guild in enumerate(bot.guilds):
        logging.debug(f"Updating guild {i + 1}/{len(bot.guilds)}: {guild.name} ({guild.id})")
        # Update the guild data with the new structure
        await DB.guilds.update_one(
            {"id": cast(discord.Guild, guild).id},
            {
                "$set": {
                    "added_on": cast(discord.Guild, guild).me.joined_at,
                }
            },
        )
        if i % 100 == 0 and i != 0:
            logging.info(f"Updated {i} guilds")
            await sleep(1)

    logging.info("Migrated all guild data to include added_on field")


async def migrate():
    """
    Migrates db versions without needing the bot instance. Also sets "migrate" to True in 
    the database so the migrate requiring bots can be run afterwards. 
    """
    await DB.teams.update_many(
        {"achivements": {"$exists": True}},
        [
            {"$set": {"achievements": "$achivements"}},
        ]
    )

    await DB.teams.update_many(
        {"achievements": {"$exists": True}},
        [
            {"$unset": "achivements"},
        ]
    )
    
    logging.info("Migrated user achievements key to achievements successfully")

    # Add message_stats field to all guilds
    result = await DB.guilds.update_many(
        {"message_stats": {"$exists": False}},
        {"$set": {"message_stats": {}}}
    )
    logging.info(f"Added message_stats field to {result.modified_count} guilds")

    await DB.const.update_one(
        {"_id": "migrate"},
        {"$set": {"value": True}},
    )
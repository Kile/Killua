"""
This file sets up the mongodb collections and sets default values where needed

All you have to do is go to https://www.mongodb.com and create an account, create a cluster, click on "connect", 
click on "connect your application" and then copy the connection string. Replacing <password> with your own, you 
put it with the "mongodb" key in `config.json` and run this file with `python3 setup.py`, then you're all set!

Note: As the console says when running this program, you will need to add data for the "items" collection yourself
"""
from pymongo import errors, collection

import logging
from killua.static.enums import PrintColors
from killua.static.constants import (
    shop,
    stats,
    presence,
    updates
)

def _try(coll: collection, args:dict):
    try:
        coll.insert_one(args)
    except errors.DuplicateKeyError:
        logging.info(f"{PrintColors.FAIL} \"{args['_id']}\" key already exists, skipped...{PrintColors.ENDC}")

def main():
    
    _try(shop, {"_id": "daily_offers", "offers": [], "log": [], "reduced": None})
    _try(stats, {"_id": "commands", "command_usage": {}})
    _try(presence, {"_id": "status", "text": None, "activity": None, "presence": None})
    _try(updates, {"_id": "current"})
    _try(updates, {"_id": "log", "past_updates": []})
    _try(stats, {"_id": "growth", "growth": []})
    
    logging.info(f"""
    {PrintColors.OKGREEN} Successfully added all collections {PrintColors.WARNING}

     The "item" items have to be added manually. Structure:
     {'{'}
        "_id": <int>,
        "name": <str>,
        "limit": <int>,
        "range": <str>, {PrintColors.OKBLUE} Only for spell cards {PrintColors.WARNING}
        "class": <list>,{PrintColors.OKBLUE} Only for spell cards {PrintColors.WARNING}
        "rank": <str>,
        "description": <str>,
        "Image": <url>,
        "emoji": <str>,
        "owners": <list>,
        "type": <str>
     {'}'}{PrintColors.ENDC}
    """)

if __name__ == "__main__":
    main()
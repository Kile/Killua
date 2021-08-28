# MONGODB CONNECTIONS
import json
from pymongo import MongoClient
with open('config.json', 'r') as config_file:
    config = json.loads(config_file.read())

CLUSTER = MongoClient(config['mongodb'])

DB = CLUSTER['Killua']
teams = DB['teams']
items = DB['items']
guilds = DB['guilds']

GDB = CLUSTER['general']
shop = GDB['shop']
blacklist = GDB['blacklist']
stats = GDB['stats']
presence = GDB['presence']
todo = GDB['todo']
updates = GDB['updates']

IPC_TOKEN = config["ipc"]
TOKEN = config["token"]
PATREON = config["patreon"]
DBL = config["dbl"]
PXLAPI = config["pxlapi"]

PATREON_TIERS = {
    "6002629": {
        "name": "tier_one",
        "id": 1,
        "premium_guilds": 1
    },
    "6002630": {        
        "name": "tier_two",
        "id": 2,
        "premium_guilds": 2
    },
    "6002631": {
        "name": "tier_three",
        "id": 3,
        "premium_guilds": 3
    },
    "6563669": {
        "name": "tier_four", 
        "id": 4,
        "premium_guilds": 10
    }
}

# Tips that can be added to any send message send with bot.send_message
TIPS = ["Did you know you gain doubled jenny **every time** you collect jenny somehow with premium tier 3?", "With premium you can choose an *entire server* whose cooldowns will be halved", "Want to get started collecting cards and need a guilde? Use `use booklet`!"]

# TOPICS
TOPICS = ['What\'s your favorite animal?', 'What is your favorite TV show?', 'If you could go anywhere in the world, where would you go?', 'What did you used to do, stopped and wish you hadn\'t?', 'What was the best day in your life?', 'For what person are you the most thankful for?', 'What is and has always been your least favorite subject?', 'What always makes you laugh and/or smile when you think about it?', 'Do you think there are aliens?', 'What is your earliest memory?', 'What\'s your favorite drink?', 'Where do you like going most for vacation?', 'What motivates you?', 'What is the best thing about school/work?', 'What\'s better, having high expectations or having low expectations?', 'What was the last movie you saw?', 'Have you read anything good recently?', 'What is your favorite day of the year?', 'What kind of music do you like to listen to?', 'What things are you passionate about?', 'What is your favorite childhood memory?', 'If you could acquire any skill, what would you choose?', 'What is the first thing that you think of in the morning?', 'What was the biggest life change you have gone through?', 'What is your favorite song of all time?', 'If you won $1 million playing the lottery, what would you do?', 'How would you know if you were in love?', 'If you could choose to have any useless super power, what would you pick?',
'Who is your role model?', 'What\'s the best food you have ever eaten?', 'What accomplishment are you most proud of?', 'Would you rather be the most popular kid in school or the smartest kid in school?', 'Do you prefer to cook or order take out?', 'What is your dream job?', 'What\'s your ideal way to celebrate your birthday?', 'What is a short/long term goal of yours?', 'What are your three must have smart phone apps?', 'Would you rather be the smartest moron or dumbest genius?', 'What was the last gift that you received?', 'If you could give one piece of advice to the whole world, what would it be?', 'Describe your perfect day.', 'How would you define success?', 'What is the first thing that you notice when meeting someone new?', 'Do you prefer to take baths or showers?', 'Do you like to sing out loud when no one else is around?']
ANSWERS = ['Yep', 'You are kidding, right?', 'I think you know that better than me', 'I am sorry to break it to you but... no', 'I don\'t think so', 'Yes, no more info needed', 'No! Why would you ask that?', 'Let\'s do it!', 'Did you ask your mom?', 'I seriously don\'t think that is a good idea', 'Could you repeat that?', 'Well... maybe', 'Anything is possible']

# ACTION IMAGES
HUG_IMGS = [f'https://i.pinimg.com/originals/66/9b/67/669b67ae57452f7afbbe5252b6230f85.gif', f'https://i.pinimg.com/originals/70/83/0d/70830dfba718d62e7af95e74955867ac.jpg', 'https://cdn.discordapp.com/attachments/756945125568938045/756945463432839168/image0.gif', 'https://cdn.discordapp.com/attachments/756945125568938045/756945308381872168/image0.gif', 'https://cdn.discordapp.com/attachments/756945125568938045/756945151191941251/image0.gif', 'https://pbs.twimg.com/media/Dl4PPE4UUAAsb7c.jpg', 'https://encrypted-tbn0.gstatic.com/images?q=tbn%3AANd9GcSJgTjRyQW3NzmDzlvskIS7GMjlFpyS7yt_SQ&usqp=CAU', 'https://static.zerochan.net/Hunter.x.Hunter.full.1426317.jpg', 'https://encrypted-tbn0.gstatic.com/images?q=tbn%3AANd9GcQJjVWplBdqrasz8Fh-7nDkxRjnnNBqk0bZlQ&usqp=CAU', 'https://i.pinimg.com/originals/75/2e/0a/752e0a5f813400dfebe322fc8b0ad0ae.jpg', 'https://thumbs.gfycat.com/IllfatedComfortableAplomadofalcon-small.gif', 'https://steamuserimages-a.akamaihd.net/ugc/492403625757327002/9B089509DDCB6D9F8E11446C7F1BC29B9BA57384/', f'https://cdn.discordapp.com/attachments/756945125568938045/758235270524698634/image0.gif', f'https://cdn.discordapp.com/attachments/756945125568938045/758236571974762547/image0.jpg', 'https://cdn.discordapp.com/attachments/756945125568938045/758236721216749638/image0.jpg', 'https://cdn.discordapp.com/attachments/756945125568938045/758237082484473856/image0.jpg', 
'https://cdn.discordapp.com/attachments/756945125568938045/758237352756903936/image0.png', 'https://cdn.discordapp.com/attachments/756945125568938045/758237832954249216/image0.jpg', 'https://i.pinimg.com/originals/22/66/3e/22663e7f60734f141c72ca659a3a90cc.jpg', 'https://i.pinimg.com/originals/c5/38/d5/c538d54e493b118683c48ccbd0020311.jpg', 'https://wallpapercave.com/wp/wp6522234.jpg', 'https://i.pinimg.com/originals/48/db/98/48db98dac9d67143c4244991cb84b4f1.jpg', 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQjXQW8tVJfFmPz8qokH3u7maX6haz_6Uyx2w&usqp=CAU', 'https://i.pinimg.com/originals/f3/17/1b/f3171b2bb05b6c6ad90e6c094737d7e9.png', 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQrukypBFocf_oqpSSJmEpzx5sLjnpUJqMD4Q&usqp=CAU', 'https://images-wixmp-ed30a86b8c4ca887773594c2.wixmp.com/f/edb16fd5-2978-4a97-8568-7472c3205405/dbfi6uq-32adf5b9-e2d0-4892-8026-97012b9ae0d1.png/v1/fit/w_300,h_900,q_70,strp/happy_bday_killua_by_queijac_dbfi6uq-300w.jpg?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1cm46YXBwOiIsImlzcyI6InVybjphcHA6Iiwib2JqIjpbW3siaGVpZ2h0IjoiPD05MjkiLCJwYXRoIjoiXC9mXC9lZGIxNmZkNS0yOTc4LTRhOTctODU2OC03NDcyYzMyMDU0MDVcL2RiZmk2dXEtMzJhZGY1YjktZTJkMC00ODkyLTgwMjYtOTcwMTJiOWFlMGQxLnBuZyIsIndpZHRoIjoiPD05MDAifV1dLCJhdWQiOlsidXJuOnNlcnZpY2U6aW1hZ2Uub3BlcmF0aW9ucyJdfQ.ETgcZiDvdTQpDPQTQiMwW8ELS3xVXH_4nFYzEFpXJ8Y', 'https://i.pinimg.com/originals/b5/c1/f3/b5c1f308052e51b79c9a38e5164fe89e.jpg',
'https://dzt1km7tv28ex.cloudfront.net/u/466410804707590144_35s_d.jpg', 'https://i.pinimg.com/originals/d5/bf/f3/d5bff3a697448536651892e90ecea059.png', 'https://d.furaffinity.net/art/akitamonster/1416385290/1416385290.akitamonster_killuagonhugbehind.png', 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTSrjPgwlZ86TckXAV8LudKe6Depz3l37rMcg&usqp=CAU', 'https://i.pinimg.com/originals/a0/83/63/a083635d9813b7d3e2ce45cb12ccdc13.png', 'https://i.quotev.com/img/q/u/20/9/2/rcu7je27oy.jpg', 'https://pm1.narvii.com/6467/02892de9a2e459094adc2eab7b1f4ec1495a7a21_hq.jpg', 'https://i.pinimg.com/originals/c8/ee/c8/c8eec84afc58789fe1656f339fb10d8e.jpg', ]
PAT_IMGS = [f'https://i.pinimg.com/originals/be/75/ff/be75ff9f2ba20efb4dbda09c62802b39.gif', f'https://pbs.twimg.com/media/DmWlGrqX0AAKlT3.jpg']


# ACTION TEXT
HUG_TEXTS = [f'**(a)** hugs **(u)** as strong as they can', f'**(a)** hugs **(u)** and makes sure to not let go', f'**(a)** gives **(u)** the longest hug they have ever seen', f'**(a)** cuddles **(u)**', f'**(a)** uses **(u)** as a teddybear', f'**(a)** hugs **(u)** until all their worries are gone and 5 minutes longer',f'**(a)** clones themself and together they hug **(u)**', f'**(a)** jumps in **(u)**\'s arms', f'**(a)** gives **(u)** a bearhug', f'**(a)** finds a lamp with a Jinn and gets a wish. So they wish to hug **(u)**', f'**(a)** asks **(u)** for motivation and gets a hug','**(a)** looks at the floor, then up, then at the floor again and finnally hugs **(u)** with passion', '**(a)** looks deep into **(u)**\'s eyes and them gives them a hug', '**(a)** could do their homework but instead they decide to hug **(u)**', '**(u)** wanted to go get food but **(a)** wouldn\'t let go']
PAT_TEXTS = ['**(a)** was too tired to hug **(u)** so they gave a pat instead', '**(u)** took 5 lp damage down so **(a)** gives them a healing head pat', '**(a)** tries to catch a spider, slips and instead pats **(u)**. **(a)** is also fine with that', '**(a)** pats **(u)**', '**(a)** thinks **(u)** is a cat and starts to pat them', '**(a)** looks at **(u)**\'s fluffy hair and starts to pat them']
SLAP_TEXTS = ['**(a)** slaps **(u)**', '**(a)** stares at **(u)** for a long time and then slaps them', '**(a)** has no mercy; they slap **(u)**', '**(a)** is unsure how to react so they slap **(u)**']
POKE_TEXTS = ['**(a)** pokes **(u)**', '*Poke* *Poke*, **(a)** pokes **(u)**', '**(a)** starts poking **(u)**', '**(a)** pokes **(u)** with a big smile on their face']
TICKLE_TEXTS = ['**(u)** didn\'t let **(a)** eat cookies, so they get tickled!', '**(a)** couldn\'t resist their chance to tickle **(a)**','**(a)** tickles **(u)**', '**(a)** has no mercy; they tickle **(u)**', '**(a)** knows there is just one way, so they tickle **(u)**']

# the todo editing cache, needs to be defined here so I can use it across files
editing = {}

# ACTION DATA
ACTIONS = {
    "hug": {
        "text": HUG_TEXTS,
        "images": HUG_IMGS
    },
    "pat": {
        "text": PAT_TEXTS,
        "images": PAT_IMGS
    },
    "slap": {
        "text": SLAP_TEXTS,
        "images": "who cares"
    },
    "poke": {
        "text": POKE_TEXTS,
        "images": "who cares"
    },
    "tickle": {
        "text": TICKLE_TEXTS,
        "images": "who cares"
    }
}

# EMOTES
USER_FLAGS = {
    "staff": "<:DiscordStaff:788508648245952522>",
    "partner": "<a:PartnerBadgeShining:788508883144015892>",
    "hypesquad": "<a:HypesquadShiny:788508580101488640>",
    "bug_hunter": "<:BugHunter:788508715241963570>",
    "bug_hunter_level_2": "<:BugHunterGold:788508764339830805>",
    "hypesquad_bravery": "<:BraveryLogo:788509874085691415>",
    "hypesquad_brilliance": "<:BrillianceLogo:788509874517442590>",
    "hypesquad_balance": "<:BalanceLogo:788509874245074989>",
    "early_supporter": "<:EarlySupporter:788509000005451776>",
    "team_user": "Contact Kile#0606", # I do not know what that flag means
    "system": "system", # don't have an emoji for that but also don't want a KeyError
    "verified_bot": "<:verifiedBot:788508495846047765>",
    "verified_bot_developer": "<:EarlyBotDev:788508428779388940>",
    "discord_certified_moderator": "<:CertifiedModerator:866841508812292096>",
    "nitro": "<:Nitro:866841996114657280>"
}

KILLUA_BADGES = {
    "6002629": "<:tier_one_badge:879390548857880597>",
    "6002630": "<:tier_two_badge:879390669368614982>",
    "6002631": "<:tier_three_badge:879390807315087451>",
    "partner": "<:partner_badge:879391663460610078>",
    "artist": "<:artist_badge:879391368076734464>",
    "greed_island_badge": "<:greed_island_badge:879391821938180116>",
    "early_supporter": "",
    "developer": "",
    "owner": "<:badge_killua_owner:788940157599612948>"
}

SERVER_BADGES = {
    "premium": "",
    "early supporter": "",
    "partner": "<:partner_badge:879391663460610078>",
    "official": ""
}


LOOTBOXES = {
    1: {
        "name": "Standart Box",
        "price": 250,
        "emoji": "<:standard_box:877917415470690375>",
        "description": "A mass produced box sold everywhere",
        "rewards": {
            "jenny": (10, 30),
            "cards": {
                "rarities": [],
                "types": []
            }
        },
        "rewards_total": 20,
        "cards_total": (0, 0),
        "probability": 20,
        "available": True
    },
    2: {
        "name": "Box of Legends",
        "price": 10000,
        "emoji": "<:box_of_legends:877928029647691856>",
        "description": "A box so rare that nobody has seen one yet, its existence is only a legend",
        "rewards": {
            "jenny": (200, 1000),
            "cards": {
                "rarities": ["S", "A"],
                "types": ["normal", "spell"]
            }
        },
        "rewards_total": 10,
        "cards_total": (2, 3),
        "probability": 1,
        "available": True
    }
}

# GREED ISLAND STUFF

ALLOWED_AMOUNT_MULTIPLE = 3
FREE_SLOTS = 40
DEF_SPELLS= [1003, 1004, 1019]
VIEW_DEF_SPELLS = [1025]
INDESTRUCTABLE = [1026, 0]

PRICES:dict = {
    'S': 10000,
    'A': 5000,
    'B': 3000,
    'C': 1500,
    'D': 800,
    'E': 500,
    'F': 200,
    'G': 100,
    'H': 50
}

BOOK_PAGES = [
"""
📖::📖::📖


A beginners guide of the greed island card system


📖::📖::📖
""",
f"""If you are not familiar with how this works in the anime: 

The main goal of the game is to obtain all 100 cards in the book. How hard it is to obtain a card is determined by it's **rank**. You can find it on the top right of the card. Next to it to the right is a number. This number times {ALLOWED_AMOUNT_MULTIPLE} is the maximum amount of those cards to exist globally. If that limit is exceeded you can't obtain any more cards unless someone looses one of their copies which means one 
other person can obtain the card again""",

f"""On the top left, you can see the card number. 
Typically, spell cards have a number one thousand and ... and item cards have a number less than 100. Cards with a number below 100 count towards your goal of collecting all 100 **restricted slot** cards.
When you obtain a card which has an id below 100 but you already have one in your restricted slots, or the card id is above 100, the card comes into your **free slots**. You can have a maximum of {FREE_SLOTS} cards in your free slots""",

"""I have mentioned before that there are **spell cards**. You can use them to steal cards from other users, gamble and a lot more. To use a spell card, use `use <card> <arguments>`. Some spell cards only work in a **short range**. In discord terms that means that the target must have send a message recently in the channel the command is used in. You can also use permament spell cards to protect yourself from others or tranform cards into fakes.""",

"""A word about **fakes**. The main usecase I see them as is bait. You can't sell fakes, you can't use them and they don't count towards the 100 card goal. 
If you want to swap out a fake in your album with a real card in your free slots or the other way around, use `swap <card_id>`. If you want to get rid of a fake, make sure it's in your free slots and discard it with `discard <card_id>`""",

"""You have reached the end of the introduction!

Now it's time for you to explore the world of cards, steal, collect, form alliances and so on. 

Do you want to add a card to the game you have a good idea for? That is possible, if you can make the
card design with image we will be happy to have a look at your idea!

Have fun hunters
- The Gamemaster"""
]   


# FOR THE UWU COMMAND

ALIASES = {
    'hello': ['hyaaaa', 'Haiii'],
    'bye': ['baiiii'],
    'this': ['dis'],
    'what': ['wat'],
    'because': ['cuz'],
    'and': ['&']
}

UWUS = ['uwu', 'owo', 'ʕ•́ᴥ•̀ʔっ', '≧◠ᴥ◠≦', '>\_<']

# THE KILLUA SUPPORT SERVER AND ITS DATA
GUILD = 715358111472418908
BOOSTER_ROLE = 769622564648648744
REPORT_CHANNEL = 796306329756893184
UPDATE_CHANNEL = 874626830949302282

# FOR THE NOKIA COMMAND OF /IMAGESCRIPT OF PXLAPI

NOKIA_CODE = """
let e = url.split('.').pop(); let ext = e.substring(0,e.length-(e.length-3)).replace('jpe', 'jpeg');
const mybuffer = await fetch(url).then(r => r.arrayBuffer());
const mybuffer2 = await fetch('https://cdn.discordapp.com/attachments/762926280793784350/817847142668304444/1615060247537.png').then(r => r.arrayBuffer());

let canvas;
if(ext == "gif") {
let overlay = await Image.decode(mybuffer2);
let image = await GIF.decode(mybuffer);
let frames = [];
let n = 0;
 for (num = 0; num < ((image.length < 40) ? image.length : 40); num = num+1) {
 const canva = new Frame(overlay.width, overlay.height, image[n].duration, 0, 0, Frame.DISPOSAL_BACKGROUND);
image[n].resize(235, 168);
for(const [x, y] of image[n]) {
    const [,,l,a] = Image.rgbaToHSLA(...Image.colorToRGBA(image[n].getPixelAt(x, y)));
    image[n].setPixelAt(x, y, Image.rgbaToColor(...[0x69,0x90,0x5b].map(v => v * l), 0xff * a));}
    canva.composite(new Image(235, 168).fill(0x69905bff), 54, 214);
    canva.composite(image[n], 54, 214);
    canva.composite(overlay);
 frames.push(canva); n = n+1}
canvas = new GIF(frames);
} else {
    let overlay = await Image.decode(mybuffer2);
    let image = await Image.decode(mybuffer);
     canvas = new Image(overlay.width, overlay.height);
    for(const [x, y] of image) {
    const [,,l,a] = Image.rgbaToHSLA(...Image.colorToRGBA(image.getPixelAt(x, y)));
    image.setPixelAt(x, y, Image.rgbaToColor(...[0x69,0x90,0x5b].map(v => v * l), 0xff * a));}
    image.resize(235, 168);
    canvas.composite(new Image(235, 168).fill(0x69905bff), 54, 214);
    canvas.composite(image, 54, 214);
    canvas.composite(overlay);
} 
return canvas.encode();
"""
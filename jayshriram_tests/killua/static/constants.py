import json
import io
import discord
from pymongo import MongoClient, collection
from typing import Union

from os.path import exists
from killua.utils.test_db import TestingDatabase as Database
import killua.args as args

args.init()

with open("config.json", "r") as config_file:
    config = json.loads(config_file.read())

CLUSTER = MongoClient(config["mongodb"])

CONST_DEFAULT = [ # The default values for the const collection
    {"_id": "migrate", "value": True},
    {"_id": "usage", "command_usage": {}},
    {"_id": "shop", "offers": [], "log": []},
    {"_id": "presence", "text": None, "activity": None, "presence": None},
    {"_id": "updates", "updates": []},
    {"_id": "blacklist", "blacklist": []},
]

MAX_VOTES_DISPLAYED = 5

CARDS_URL = "https://json.extendsclass.com/bin/7d2c78bde0cd"

class DB:
    _DB = None
    const = None
    _cards = None

    def __init__(self):
        if not args.Args.test:
            self._DB = CLUSTER["Killua"]

    @property
    def teams(self) -> Union[collection.Collection, Database]:
        return self._DB["teams"] if args.Args.test is None else Database("teams")

    @property
    def items(self) -> Union[collection.Collection, Database]:
        if args.Args.test is not None:
            if self._cards:
                return self._cards
            elif exists("cards.json"):
                with open("cards.json", "r") as file:
                    res = json.loads(file.read())
                    db = Database("items")
                    db.db["items"] = res["data"]
                    self._cards = db
                    file.close()
                    return db
            else:
                raise FileNotFoundError("cards.json does not exist. Run `python3 -m killua -dl` to download the cards first.")
        else:
            return self._DB["items"]

    @property
    def guilds(self) -> Union[collection.Collection, Database]:
        return self._DB["guilds"] if args.Args.test is None else Database("guilds")

    @property
    def todo(self) -> Union[collection.Collection, Database]:
        return self._DB["todo"] if args.Args.test is None else Database("todo")

    @property
    def const(self) -> Union[collection.Collection, Database]:
        if args.Args.test is not None:
            db = Database("const")
            db.insert_many(CONST_DEFAULT)

            return db
        else:
            return self._DB["const"]

DB = DB()

IPC_TOKEN: str = config["ipc"]
TOKEN = config["token"]
PATREON = config["patreon"]
PXLAPI = config["pxlapi"]
PASSWORD = config["password"]
PORT = config["port"]
TOPGG_TOKEN = config["topgg_token"]
DBL_TOKEN = config["dbl_token"]

# Big boi from https://gist.github.com/gruber/8891611
URL_REGEX = r"(?i)\b((?:https?:(?:/{1,3}|[a-z0-9%])|[a-z0-9.\-]+[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)/)(?:[^\s()<>{}\[\]]+|\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\))+(?:\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’])|(?:(?<!@)[a-z0-9]+(?:[.\-][a-z0-9]+)*[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)\b/?(?!@)))"

# these are badges that grant premium benefits without being managed by the patreon class.
# granted when someone pays for premium another way or gets benefits in some way
PREMIUM_ALIASES = {
    "tier_one": "6002630",
    "tier_two": "6002629",
    "tier_three": "6002631",
    "tier_four": "6563669"
}

PATREON_TIERS = {
    "6002630": {
        "name": "tier_one",
        "id": 1,
        "premium_guilds": 1
    },
    "6002629": {        
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

PREMIUM_BENEFITS = """
Premium benefits
*every tier includes the benefits from the previous tiers*

Tier 1 <:tier_one_badge:879390548857880597> 
<a:arrow:876801266381127710> halved cooldowns
<a:arrow:876801266381127710> up to 1 premium guild
<a:arrow:876801266381127710> custom id for todo lists
<a:arrow:876801266381127710> exclusive role in support server
<a:arrow:876801266381127710> doubled daily jenny
<a:arrow:876801266381127710> weekly lootbox
<a:arrow:876801266381127710> exclusive badge

Tier 2 <:tier_two_badge:879390669368614982> 
<a:arrow:876801266381127710> invite dev bot and use not yet public features
<a:arrow:876801266381127710> up to two premium guilds

Tier 3 <:tier_three_badge:879390807315087451> 
<a:arrow:876801266381127710> up to 3 premium guilds
<a:arrow:876801266381127710> doubled jenny whenever gaining jenny

Tier 4 <:tier_four_badge:879391090665467905> 
<a:arrow:876801266381127710> up to 10 premium guilds


Premium guild <:premium_guild_badge:883473807292121149>
<a:arrow:876801266381127710> exclusive server badge 
<a:arrow:876801266381127710> halved cooldown for entire server (stacks with premium sub)
<a:arrow:876801266381127710> access to premium server restricted commands
<a:arrow:876801266381127710> doubled daily jenny for entire server (stacks with premium sub)
<a:arrow:876801266381127710> unlimted poll votes
"""

INFO = "This bot is themed after the character Killua from the anime [hunter x hunter](https://en.wikipedia.org/wiki/Hunter_×_Hunter)." + \
"""
I chose this character because it was sort of a role model I had during a tough time and I wanted to give back by creating a bot that would best represent the character.
At that point I had never programmed in python before, but I had a goal and I taught myself (through some pingspams in the support servers) how to code step by step to achieve that goal.

Killua has become a way I continue to teach myself programming and by now it has taught me a lot. The bot was never build to profit. 
And so even though I myself invested quite a lot of money into the bot, Killua will barely have any paywalls at all. If you do like the project, there is a patreon, however if you don't want to spend money, Killua will still have many things to offer for you.

If you're reading this that means you're using Killua, so I want to thank you for that. Being the only developer on this pretty massive codebase is not easy, but knowing people enjoy bot makes it worth it :)
"""

# Tips that can be added to any send message send with bot.send_message
TIPS = ["Do you own a big server? Chances are **you** qualify to become a partner, meaning your server will become a permanent premium server. For more infos & applying, join the support server.", "Got feedback? **We want to hear it!** Join the support server to let us know what you think about the bot.", "Killua is designed to have as little as possible paywalled, but if you enjoy the bot please enjoy becoming a Patreon.", "Join the support server to be the first to see new features!", "If you manage to beat Killua 25 times at rock paper scissors he will give you a present :)", "Need something to organise your tasks? Try **todo lists**. For more info, use `/help`", "If you have no one to play rps against, you can just play against me!", "Did you know you gain doubled jenny **every time** you collect jenny somehow with premium tier 3?", "With premium you can choose an *entire server* whose cooldowns will be halved", "Want to get started collecting cards and need a guide? Use `/cards use booklet`!", "Want to get lootboxes for free? You get a free lootbox every 5th time you vote for Killua!", "Get info on lootbox chances and lore by using `boxinfo`", "To invite Killua to your own server, use `invite`", "Did you know that you can search for books using `novel <book_name>`", "You can translate 20+ languages using the `translate` command!", "Not sure how to use a command? Use `/help <command>` to get more infos!", "Take a screenshot of any website using the `screenshot` command.", "Did you forget if a card you own is a fake? No problem, check it with `/cards check`"]

# TOPICS
TOPICS = ["What's your least favorite genre of music?", "What's the most beautiful place youve ever been to?", "What's the best name for a pet dragon?", "What's the best name for a pet turtle?", "What's the best name for a pet snake?", "What do you enjoy doing most in your free time?", "Do you think technology will advance or ruin humanity?", "What's your favorite animal?", "What is your favorite TV show?", "If you could go anywhere in the world, where would you go?", "What did you used to do, stopped and wish you hadn't?", "What was the best day in your life?", "For what person are you the most thankful for?", "What is and has always been your least favorite subject?", "What always makes you laugh and/or smile when you think about it?", "Do you think there are aliens?", "What is your earliest memory?", "What's your favorite drink?", "Where do you like going most for vacation?", "What motivates you?", "What is the best thing about school/work?", "What's better, having high expectations or having low expectations?", "What was the last movie you saw?", "Have you read anything good recently?", "What is your favorite day of the year?", "What kind of music do you like to listen to?", "What things are you passionate about?", "What is your favorite childhood memory?", "If you could acquire any skill, what would you choose?", "What is the first thing that you think of in the morning?", "What was the biggest life change you have gone through?", "What is your favorite song of all time?", "If you won $1 million playing the lottery, what would you do?", "How would you know if you were in love?", "If you could choose to have any useless super power, what would you pick?",
"What sport do you wish you were really good at?", "What's the strangest dream you've had recently?", "What's the best thing you've ever bought off Amazon?", "What is something people are always surprised to learn about you?", "What song do you wish you could put on right now?", "What do you think has been the best movie of the year so far?", "What do you think is the best show on Netflix right now?", "Do you think at some points there will be robot revolution? (I do ò_ó)", "Who was your first crush on?", "What was something that changed your life?", "What did someone you know do that was so embarrassing that you acted like you didn't know them?", "What was a moment that completely changed your option about something or someone?", "What thing happened to you that you wouldn't believe it if someone told you it had happened to them?", "What's your favorite ice cream flavor?", "If you had to choose another username what would it be?", "Who is your role model?", "What's the best food you have ever eaten?", "What accomplishment are you most proud of?", "Would you rather be the most popular kid in school or the smartest kid in school?", "Do you prefer to cook or order take out?", "What is your dream job?", "What's your ideal way to celebrate your birthday?", "What is a short/long term goal of yours?", "What are your three must have smart phone apps?", "Would you rather be the smartest moron or dumbest genius?", "What was the last gift that you received?", "If you could give one piece of advice to the whole world, what would it be?", "Describe your perfect day.", "How would you define success?", "What is the first thing that you notice when meeting someone new?", 
"Who is the most important person in your life right now?", "What's the nicest thing anyone has ever done for you?", "What's the biggest risk you've ever taken?", "What are the top three things on your bucket list?", "What did you want to be when you were a kid?", "What did you want to be when you were a kid?", "How did you spend your last birthday?", "What's the best holiday?", "Do you prefer to take baths or showers?", "Do you like to sing out loud when no one else is around?", "What is the worst piece of advice you've ever gotten?", "When was the last time you laughed so hard you cried?", "Is a hot dog a sandwich?", "What's your go-to joke?", "Which celebrity would play you in a movie about your life?", "Tell me about the worst pickup line you've ever gotten.", "How would you describe your best friend?", "What qualities do you admire about your parents?", "What's the one thing that people always misunderstand about you?", "When have you felt your biggest adrenaline rush?", "What's something you hope will never change?", "What's your best memory so far this year?", "If your life had a theme song, what would it be?", "Do you believe we would be better off if we didn't have social media?", "What is one quality about yourself that you are most proud of?", "What's something that always makes you smile?", "Where would you go if you had to pack your stuff and relocate to another country tomorrow?", "Which website do you visit the most?", "What's the weirdest fact you've ever heard?", "What's the last lie you told?", "What bridges are you glad that you burned?", "What's the meanest thing you've ever said to someone else?", "Who are you most jealous of?",
"What's one movie you're embarrassed to admit you enjoy?", "What's the cheapest gift you've ever gotten for someone else?", "What's your most embarrassing late night purchase?", "What is your greatest fear in a relationship?", "Have you ever regifted a present?", "Name one thing you'd change about every person in this chat.", "What's one useless skill you'd love to learn anyway?", "How many people have you kissed?", "What's something you would die if your mom found out about?", " Who was your first love?", "Who in this chat would you want to swap lives with for a week?", "Who's the most surprising person to ever slide into your DMs?", "What is something you've failed at recently?", "What word do you hate the most?", "If you could hire someone to do one thing for you, what would it be?", "What's the best lie you've ever told anyone?", "What do you think happens when you die?", "Who's the last person who called you?", "What's one thing about your partner that you find least attractive?", "When was the last time you were really angry? Why?", "Would you ever get plastic surgery?", "Who was the last person you said, “I love you” to?", "What's the most bogus rumor you've ever heard about yourself?", "Do you think cheating can ever be justified? How?", "What's your best pickup line?", "What's the dumbest thing you've ever lied about?", "What's the biggest secret you've kept from your parents?", "What's something that takes up way too much of your time?", "What's your favorite thing to do when bored?", "If you had to pick three words to describe yourself, what would they be?", "What do you seek for in a romantic partner?", "What's the most useless invention you've ever heard of?",
"What was the best thing about how your parents raised you?", "If you could have a fictional superhero for a best friend, who would it be?", "What does your name mean?", "Tell me about your childhood best friend.", "What is the thing you wish you would have known 10 years ago?", "What Netflix show or movie are you marathon-watching?", " What projects are you working on right now that bring you joy?", "What is one thing you should never say at a wedding?", "What do you think are the best traits for a person to have?", "What is something you wish you could do everyday?", "If someone gave you an envelope with your death date inside of it, would you open it?", "What scares you most about your future?", "What three things do you want to be remembered for?", "How would your best friend describe you?", "What is a significant event that has changed you?", "What are three fun facts about yourself?", "Who do you count on the most for help?", "What did you think was the most challenging part of being a kid?", "Have you ever really kept a New Year's resolution?", "How long can you go without checking your phone?", "Which of your family members or friends are you most like?", "How long do you think you'd survive in a zombie apocalypse?", "What's a special habit of yours?", "What's your least favorite color?"]
ANSWERS = ["What would jesus do?", "My sources say no but my heart says yes", "\U000026a0 8ball.exe has stopped responding", "If you try hard enough, maybe", "Stop asking me >-<", "Only if you're wearing socks", "That's what the milk carton said", "Probably, if it's raining.", "Yep", "You are kidding, right?", "I think you know that better than me", "I am sorry to break it to you but... no", "I don't think so", "Yes, no more info needed", "No! Why would you ask that?", "Lets do it!", "Did you ask your mom?", "I seriously don't think that is a good idea", "Could you repeat that?", "Well... maybe", "Anything is possible", "If you really need an answer, google it", "Better to think about it yourself", "Yes....wait, no", "No...actually, yes"]

# A list of whould you rather options
WYR = [("Be able to see 10 minutes into the future", "Be able to see 150 years into the future"), ("Never be able to use your phone again", "Never be able to use the internet again"), ("Team up with wonder woman", "Team up with Captain Marvel"), ("Lose your sight", "Lose your memories"), ("Have a personal maid", "Have a personal chef"), ("Be royalty 1000 years ago", "Be an average person today"), ("Cuddle a coala", "Pal around with a Panda"), ("Sip gin with Ryan Renolds", "Take tequila shots with The Rock"), ("Have a child every year for 5 years", "Never have any children at all"), ("Hunt and butcher your own meat", "Never have meat again"), ("Walk in on your parents", "Have your parents walk in on you"), ("Have unlimited Battery life on all your devices", "Have unlimited wifi wherever you go"), ("Be in history books for something terrible", "Be completely forgotten after you die"), ("Be in a zombie apocalypse", "Be in a robot apocalypse"), ("Have a photographic memory", "Have an IQ of 200"), ("Forget your partners birthday every year", "Forget your anniversary every year"), ("Get to decide the outcome of the next election", "Change the outcome of the last election"), ("Have super sensitive taste buds", "Have super sensitive hearing"), ("Detect every lie you hear", "Get away with any lie you tell"), ("Be able to fly", "Be able to breathe underwater"), ("Be able to read minds", "Be able to control minds"), ("Be able to teleport", "Be able to time travel"), ("Be able to speak every language", "Be able to speak to animals"), ("Be able to see in the dark", "Be able to see through walls"), ("Be the funniest person in the room", "Be the smartest person in the room"),
("Work for Michael Scott", "Work for Mr Burns"), ("Give up cursing forever", "Give up ice cream for 12 years"), ("Have a stranger see all the photos on your phone", "Have a stranger read all texts on your phone"), ("Have fortune", "Have fame"), ("Vistit the ISS for a week", "Spend a week in a hotel at the bottom of the ocean"), ("Be stranded in the jungle", "Be stranded in the desert"), ("Go back to kindergarden with everything you know", "Know everything your future self will learn now"), ("Be an unknown superhero", "Be an infamous villan"), ("Wear real fur", "Wear fake jewels"), ("Be able to erase your memeories", "Be able to erase someone elses memories"), ("Get drunk with one sip of alcohol", "Never get drunk"), ("Sell all of your possesions", "Sell one of your organs"), ("Unable to close any open door", "Unable to open any closed door"), ("Star in a Star Wars film", "Star in a Marvel film"), ("Always wear wet socks", "Always have a rock in your shoes"), ("Never age physically", "Never age mentally"), ("Know when you're going to die", "Know how you're going to die"), ("Be beloved by the public but hated by friends and family", "Be hated by the public but loved by friends and family"), ("Give up the internet for a month", "Give up showering for a month"), ("Be unable to move your body when it rains", "Be unable to stop moving when the sun is out"), ("Be the head of a company", "Be the head of a cult"), ("Be a famous actor", "Be a famous director"), ("Be unable to use search engines", "Unable to use social media"), ("Be a brilliant mathematician", "Be an amazing painter"), ("Never be able to wear pants", "Never be able to wear shorts"),
("Sleep with 10 blankets", "Sleep with no blanket"), ("Eat the same thing for your entire life", "Drink the same thing for your entire life"), ("Work indoors", "Work outdoors"), ("Never hear again", "Never speak again"), ("Never use a phone again", "Never use a computer again"), ("Have unlimited bacon but no games", "Have games. Unlimited games. But no games"), ("Spend one year in jail", "Lose one year off your life"), ("All traffic lights you approach turn green for you", "Never have to stand in line again"), ("Be the first person to explore a planet", "Be the inventor of a drug that cures a deadly desease"), ("Always travel first class free", "Never have to pay for food again"), ("Be able to dodge bullets no matter how fast they're moving", "Ask 3 questions about anything and get an accurate answer"), ("Be an unimportant character in the last movie you sad", "Be an unimportant character in the last book you read"), ("Be completely insane and know it", "Be completely insane and think you're sane"), ("Have everything you think about in a bubble above you", "Life stream what you do 24/7 for anyone to see"), ("Be born again in the same country", "Be born again in a random country"), ("Have a successful Twitch channel", "Have a successfull YouTube channel"), ("Never be able to drink water again", "Only be able to drink water"), ("Control fire", "Control water"), ("Never be able to use a touchscreen again", "Never be able to use keyboard and mouse again"), ("Be able to type insanely fast", "Be able to read insanely fast"), ("Take amazing selfies, but all of your other pictures are horrible", "Take breathtaking photographs of anything but yourself"),
("Lose all of your friends except your best friend", "Lose your best friend"), ("Never have to clean a bathroom again", "Never have to clean the dishes again"), ("Live in a nice house and boring town", "Live in a rough house but exciting town"), ("Have a top tier gaming pc", "Have the newest and best apple computer"), ("Read a hardback book", "Read a paperback book"), ("Owe someone a lot of money", "Owe someone a big favour"), ("Have your house completely carpeted", "Have your house completely tiled"), ("Clean rest stop toilets for living", "Work in a slaughterhouse for living"), ("Live without hot water for showers/baths", "Live without a washing machine"), ("Accindentally be responsible for the death of a child", "Accindentally be responsible for the death of three adults"), ("Have evrything you eat be too salty", "Have everything you eat be too sweet"), ("Be an amazing artist but never see the art you create", "Be an amazing musician but never hear the music you create"), ("Wake up in the middle of an unknown desert", "Wake up on a rowboat in the middle of an unknown body of water"), ("Constantly tired no matter how much you sleep", "Constantly hungry no matter how much you eat"), ("Lose the 3 possessions you hold most dear", "Lose everything but those 3 posessions"), ("Get a suitecase with $10k", "Get a suitcase which has the 50/50 chance of $50k or $1k"), ("Be completely offline for the next year", "Lose a finger or toe of your choice"), ("Have a non-venomous spider infestation in your house", "Have a mouse investation in your house"), ("Swallow 5 live worms", "Swallow one live cockroach"), ("Be held in high regard by your parents", "Be held in high regard by your friends"),
("Know the uncomfortable truth", "Believe a comfortable lie"), ("Donate your body to science", "Donate your organs to people who need them"), ("Have real political power but be relatively poor", "Be ridiculously rich but have no political power (not even bought)"), ("Have a criminal justice system that works and is fair", "Have an administrative branch that is free of corruption"), ("Live iin utopia as a normal person", "Live in distopia but you're the surpreme ruler"), ("Know all the mysteries of the universe", "Know the outcome of every choice you could make"), ("Fight for a cause you believe in, but doubt will succeed", "Fight for a cause that you only partially believe in but have a high chance of your cause succeeding"), ("Eat at the same resturant you usually do", "Eat at a new resturant that just opened"), ("Live in a house that is incredibly unique and beautiful but plain on the inside", "Live in a house that is incredibly unique and beautiful on the inside but plain on the outside")
]

# ACTION IMAGES
HUG_IMGS = ["https://pbs.twimg.com/media/E-R3q0HWYAQGC-8?format=jpg&name=900x900", "https://pbs.twimg.com/media/D2CMyE5WoAAYyNZ?format=jpg&name=small", "https://pbs.twimg.com/media/EZJPkcsXQAEIyPY?format=jpg&name=large", "https://pbs.twimg.com/media/BV23LRDCEAACjqL?format=jpg&name=small", f"https://i.pinimg.com/originals/66/9b/67/669b67ae57452f7afbbe5252b6230f85.gif", f"https://i.pinimg.com/originals/70/83/0d/70830dfba718d62e7af95e74955867ac.jpg", "https://cdn.discordapp.com/attachments/756945125568938045/756945463432839168/image0.gif", "https://cdn.discordapp.com/attachments/756945125568938045/756945308381872168/image0.gif", "https://cdn.discordapp.com/attachments/756945125568938045/756945151191941251/image0.gif", "https://pbs.twimg.com/media/Dl4PPE4UUAAsb7c.jpg", "https://encrypted-tbn0.gstatic.com/images?q=tbn%3AANd9GcSJgTjRyQW3NzmDzlvskIS7GMjlFpyS7yt_SQ&usqp=CAU", "https://static.zerochan.net/Hunter.x.Hunter.full.1426317.jpg", "https://encrypted-tbn0.gstatic.com/images?q=tbn%3AANd9GcQJjVWplBdqrasz8Fh-7nDkxRjnnNBqk0bZlQ&usqp=CAU", "https://i.pinimg.com/originals/75/2e/0a/752e0a5f813400dfebe322fc8b0ad0ae.jpg", "https://thumbs.gfycat.com/IllfatedComfortableAplomadofalcon-small.gif", "https://steamuserimages-a.akamaihd.net/ugc/492403625757327002/9B089509DDCB6D9F8E11446C7F1BC29B9BA57384/", f"https://cdn.discordapp.com/attachments/756945125568938045/758235270524698634/image0.gif", f"https://cdn.discordapp.com/attachments/756945125568938045/758236571974762547/image0.jpg", "https://cdn.discordapp.com/attachments/756945125568938045/758236721216749638/image0.jpg", "https://cdn.discordapp.com/attachments/756945125568938045/758237082484473856/image0.jpg", 
"https://cdn.discordapp.com/attachments/756945125568938045/758237352756903936/image0.png", "https://cdn.discordapp.com/attachments/756945125568938045/758237832954249216/image0.jpg", "https://i.pinimg.com/originals/22/66/3e/22663e7f60734f141c72ca659a3a90cc.jpg", "https://i.pinimg.com/originals/c5/38/d5/c538d54e493b118683c48ccbd0020311.jpg", "https://wallpapercave.com/wp/wp6522234.jpg", "https://i.pinimg.com/originals/48/db/98/48db98dac9d67143c4244991cb84b4f1.jpg", "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQjXQW8tVJfFmPz8qokH3u7maX6haz_6Uyx2w&usqp=CAU", "https://i.pinimg.com/originals/f3/17/1b/f3171b2bb05b6c6ad90e6c094737d7e9.png", "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQrukypBFocf_oqpSSJmEpzx5sLjnpUJqMD4Q&usqp=CAU", "https://images-wixmp-ed30a86b8c4ca887773594c2.wixmp.com/f/edb16fd5-2978-4a97-8568-7472c3205405/dbfi6uq-32adf5b9-e2d0-4892-8026-97012b9ae0d1.png/v1/fit/w_300,h_900,q_70,strp/happy_bday_killua_by_queijac_dbfi6uq-300w.jpg?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1cm46YXBwOiIsImlzcyI6InVybjphcHA6Iiwib2JqIjpbW3siaGVpZ2h0IjoiPD05MjkiLCJwYXRoIjoiXC9mXC9lZGIxNmZkNS0yOTc4LTRhOTctODU2OC03NDcyYzMyMDU0MDVcL2RiZmk2dXEtMzJhZGY1YjktZTJkMC00ODkyLTgwMjYtOTcwMTJiOWFlMGQxLnBuZyIsIndpZHRoIjoiPD05MDAifV1dLCJhdWQiOlsidXJuOnNlcnZpY2U6aW1hZ2Uub3BlcmF0aW9ucyJdfQ.ETgcZiDvdTQpDPQTQiMwW8ELS3xVXH_4nFYzEFpXJ8Y", "https://i.pinimg.com/originals/b5/c1/f3/b5c1f308052e51b79c9a38e5164fe89e.jpg",
"https://dzt1km7tv28ex.cloudfront.net/u/466410804707590144_35s_d.jpg", "https://i.pinimg.com/originals/d5/bf/f3/d5bff3a697448536651892e90ecea059.png", "https://d.furaffinity.net/art/akitamonster/1416385290/1416385290.akitamonster_killuagonhugbehind.png", "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTSrjPgwlZ86TckXAV8LudKe6Depz3l37rMcg&usqp=CAU", "https://i.pinimg.com/originals/a0/83/63/a083635d9813b7d3e2ce45cb12ccdc13.png", "https://i.quotev.com/img/q/u/20/9/2/rcu7je27oy.jpg", "https://pm1.narvii.com/6467/02892de9a2e459094adc2eab7b1f4ec1495a7a21_hq.jpg", "https://i.pinimg.com/originals/c8/ee/c8/c8eec84afc58789fe1656f339fb10d8e.jpg", ]
PAT_IMGS = [f"https://i.pinimg.com/originals/be/75/ff/be75ff9f2ba20efb4dbda09c62802b39.gif", f"https://pbs.twimg.com/media/DmWlGrqX0AAKlT3.jpg"] # this is not used


# ACTION TEXT
HUG_TEXTS = ["<author> makes <user> blush by hugging them", "<author> gives <user> a hug. Their face lights up brighter than a star", "<author> makes <user>'s day by giving them a hug", "<author> hugs <user> so strong they can barely breathe", "<author> hugs <user> from behind like a hug-assassine :ninja:", "<user> looked like they needed one of these", f"<author> hugs <user> as strong as they can", f"<author> hugs <user> and makes sure to not let go", f"<author> gives <user> the longest hug they have ever seen", f"<author> cuddles <user>", f"<author> uses <user> as a teddybear", f"<author> hugs <user> until all their worries are gone and 5 minutes longer",f"<author> clones themself and together they hug <user>", f"<author> jumps in <user>'s arms", f"<author> gives <user> a bearhug", f"<author> finds a lamp with a Jinn and gets a wish. So they wish to hug <user>", f"<author> asks <user> for motivation and gets a hug","<author> looks at the floor, then up, then at the floor again and finally hugs <user> with passion", "<author> looks deep into <user>'s eyes and then gives them a hug", "<author> could do their homework but instead they decide to hug <user>", "<user> wanted to go get food but <author> wouldn't let go"]
PAT_TEXTS = ["<author> reaches over to pat <user> lovingly", "<user> is too far about to hug, so <author> pats them", "<author> wants to show appreciation, so they pat <user>", "<author> pats <user> like a cat", "<user>'s head seems very pattable", "<author> was too tired to hug <user> so they gave a pat instead", "<user> took 5 lp damage down so <author> gives them a healing head pat", "<author> tries to catch a spider, slips and instead pats <user>. <author> is also fine with that", "<author> pats <user>", "<author> thinks <user> is a cat and starts to pat them", "<author> looks at <user>'s fluffy hair and starts to pat them", "<author> didn't get pet so they pat <user> instead"]
SLAP_TEXTS = ["<author> hits <user> hard enough to send them flying", "Uh oh! <user> gets slapped by <author> because they said something <author> did not like", "<author> noticed <user> staring off into the distance. So they obviously slap them", "<user> did some unspeakable things... so <author> slapped them!", "<author> slaps <user>", "<author> stares at <user> for a long time and then slaps them", "<author> has no mercy; they slap <user>", "<author> is unsure how to react so they slap <user>"]
POKE_TEXTS = ["<user> is needed here", "<author> needs something from <user>", "<author> launches a poke attack at <user>", "<author> pokes <user> with so much force that their clothes nearly rip apart", "<author> uses the spell 'poke' to remove the tiredness 5 effect on <user>", "Look at me!", "<author> requires <user>'s attention please!", "<author> pokes <user>", "*Poke* *Poke*, <author> pokes <user>", "<author> starts poking <user>", "<author> pokes <user> with a big smile on their face", "<author> needs to tell <user> something"]
TICKLE_TEXTS = ["<author> is just wiggling their fingers, nothing going on here~", "<user> looks like they need a good laugh so they are tickled by <author>", "<author> has heard <user> likes to be tickled... so they tickle them", "<author> casts 'tickle' on <user> which adds the effect laughing 3 to them", "<user> looks sad so <author> tickles them", "<author> is too nice to slap but <user> still needs revenge, so they tickle them!", "<user> didn't let <author> eat cookies, so they get tickled!", "<author> couldn't resist their chance to tickle <author>","<author> tickles <user>", "<author> has no mercy; they tickle <user>", "<author> knows there is just one way, so they tickle <user>", "<author> attacks <user>!"]
CUDDLE_TEXTS = ["<author> snuggles up to <user> and cuddles them", "<author> cuddles <user> aggressively", "<author> cannot resist <user>'s face, so they cuddle them", "<author> uses cuddle-attack on <user>. It is very effective", "<author> can't stop thinking about it... so they cuddle <user>"]

# the todo editing cache, needs to be defined here so I can use it across files
editing = {}

# The users who have ran a command in the last 24h
daily_users = []

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
        "images": "not used"
    },
    "poke": {
        "text": POKE_TEXTS,
        "images": "not used"
    },
    "tickle": {
        "text": TICKLE_TEXTS,
        "images": "not used"
    },
    "cuddle": {
        "text": CUDDLE_TEXTS,
        "images": "not used"
    }
}

# the patreon banner being a discord.File in the cache because it's unnecessary to fetch every time I need it. The current value is the url to be fetched
class PatreonBanner: # using a normal var instead of a class did not work
    URL = "https://cdn.discordapp.com/attachments/795448739258040341/882017244484345916/killua-logo-banners-patreon2.png"
    VALUE = None

    @classmethod
    def file(cls) -> discord.File:# needs to be called each time else the bytesio object would be closed
        return discord.File(filename="patreon.png", fp=io.BytesIO(cls.VALUE))

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
    "6563669": "<:tier_four_badge:879391090665467905>",
    "partner": "<:partner_badge:879391663460610078>",
    "artist": "<:artist_badge:879391368076734464>",
    "greed_island_badge": "<:greed_island_badge:879391821938180116>",
    "early_supporter": "<:early_supporter_badge:882616073394987048>",
    "developer": "<:dev_badge:882959565690384404>"
}

GUILD_BADGES = {
    "premium": "<:premium_guild_badge:883473807292121149>",
    "early supporter": "<:early_supporter_badge:882616073394987048>",
    "partner": "<:partner_badge:879391663460610078>"
}


LOOTBOXES = {
    1: {
        "name": "Standard Box",
        "price": 250,
        "emoji": "<:Standard_box:882056516335702067>",
        "description": "A mass produced box sold everywhere.",
        "rewards": {
            "guaranteed" : {},
            "jenny": (10, 30),
            "cards": {
                "rarities": [],
                "types": []
            },
        },
        "rewards_total": 20,
        "cards_total": (0, 0),
        "probability": 1000,
        "available": True,
        "image": "https://cdn.discordapp.com/attachments/882051752386523188/882052419628986398/image1.png"
    },
    2: {
        "name": "Big box",
        "price": 1000,
        "emoji": "<:big_box:882373299986898964>",
        "description": "A big box sold to rather wealthier citizens. Some lost all their wealth on this box.",
        "rewards": {
            "guaranteed" : {},
            "jenny": (50, 500),
            "cards": {
                "rarities": [],
                "types": []
            }
        },
        "rewards_total": 15,
        "cards_total": (0, 0),
        "probability": 100,
        "available": True,
        "image": "https://cdn.discordapp.com/attachments/882051752386523188/882052419884826644/image2.png"
    },
    3: {
        "name": "Fancy box",
        "price": 1500,
        "emoji": "<:fancy_box:882373372321890304>",
        "description": "A quite rare box found somewhere in the back of somone's basement. It has a strange aura to it.",
        "rewards": {
            "guaranteed" : {},
            "jenny": (66, 66),
            "cards": {
                "rarities": ["B", "C"],
                "types": ["spell"]
            }
        },
        "rewards_total": 10,
        "cards_total": (2, 6),
        "probability": 50,
        "available": True,
        "image": "https://cdn.discordapp.com/attachments/882051752386523188/882052419251474493/image0.png"
    },
    4: {
        "name": "Golden box",
        "price": 5000,
        "emoji": "<:golden_box:882181724941979729>",
        "description": "A box for the rich and priviledged. It made some even richer and ruined others.",
        "rewards": {
            "guaranteed" : {},
            "jenny": (1500, 2500),
            "cards": {
                "rarities": [],
                "types": []
            }
        },
        "rewards_total": 15,
        "cards_total": (0, 0),
        "probability": 20,
        "available": True,
        "image": "https://cdn.discordapp.com/attachments/882051752386523188/882052420291682374/image3.png"
    },
    5: {
        "name": "Mysterious box",
        "price": 5000,
        "emoji": "<:mysterious_box:882181975367118859>",
        "description": "This box is given to young magicians after they complete their training. It a good starter pack on spells.",
        "rewards": {
            "guaranteed" : {},
            "jenny": (0, 0),
            "cards": {
                "rarities": ["D", "C", "B", "A"],
                "types": ["spell"]
            }
        },
        "rewards_total": 15,
        "cards_total": (15, 15),
        "probability": 20,
        "available": True,
        "image": "https://cdn.discordapp.com/attachments/882051752386523188/882052420576874536/image4.png"
    },
    6: {
        "name": "Advanced spell box",
        "price": 7500,
        "emoji": "<:advanced_spell_box:882181860090839110>",
        "description": "A box only given and sold to experienced magicians. Its spells are mighty and dangerous.",
        "rewards": {
            "guaranteed" : {},
            "jenny": (250, 500),
            "cards": {
                "rarities": ["B", "A"],
                "types": ["spell"]
            }
        },
        "rewards_total": 10,
        "cards_total": (5, 8),
        "probability": 8,
        "available": True,
        "image": "https://cdn.discordapp.com/attachments/882051752386523188/882052420975358032/image5.png"
    },
    7: {
        "name": "Box of titans",
        "price": 7500,
        "emoji": "<:box_of_titans:882367214186008657>",
        "description": "This ancient box used to be protected by titans and can contain one or more extremely rare SS cards. Yet even with the titans being long gone the risk is high opening this box since a lot of bombs await.",
        "rewards": {
            "guaranteed" : {},
            "jenny": (2000, 5000),
            "cards": {
                "rarities": ["SS"],
                "types": ["spell", "normal"]
            }
        },
        "rewards_total": 5,
        "cards_total": (0, 2),
        "probability": 3,
        "available": True,
        "image": "https://cdn.discordapp.com/attachments/882051752386523188/882367836331311134/image1.png"
    },
    8: {
        "name": "Haunted box",
        "price": 2000,
        "emoji": "<:haunted_box:882613954227077141>",
        "description": "This box has trapped monsters inside of it. If you listen closely you can hear them scratching and screming.",
        "rewards": {
            "guaranteed" : {},
            "jenny": (200, 300),
            "cards": {
                "rarities": ["D", "C", "B", "A"],
                "types": ["monster"]
            }
        },
        "rewards_total": 15,
        "cards_total": (5, 8),
        "probability": 40,
        "available": True,
        "image": "https://cdn.discordapp.com/attachments/882051752386523188/882754729640345670/image0.png"
    },
    9: {
        "name": "Diamond box",
        "price": 10000,
        "emoji": "<:diamond_box:882613900254777354>",
        "description": "A common possesion of royalty but hard to find elsewhere, this box contains many exclusive rewards and is partly made out of real diamonds.",
        "rewards": {
            "guaranteed" :{},
            "jenny": (2000, 3000),
            "cards": {
                "rarities": ["B", "A", "S"],
                "types": ["spell", "normal"]
            }
        },
        "rewards_total": 15,
        "cards_total": (5, 8),
        "probability": 10,
        "available": True,
        "image": "https://cdn.discordapp.com/attachments/882051752386523188/882367836738166794/image2.png"
    },
    10: {
        "name": "Box of legends",
        "price": 15000,
        "emoji": "<:box_of_legends:882367420256387142>",
        "description": "A box so rare that it's existance is nothing but a myth. The most rare items are said to be in it.",
        "rewards": {
            "guaranteed" : {},
            "jenny": (3000, 4500),
            "cards": {
                "rarities": ["S", "SS"],
                "types": ["spell", "normal"]
            }
        },
        "rewards_total": 10,
        "cards_total": (2, 4),
        "probability": 1,
        "available": True,
        "image": "https://cdn.discordapp.com/attachments/882051752386523188/882367836012556358/image0.png"
    }
}

# GREED ISLAND STUFF

ALLOWED_AMOUNT_MULTIPLE = 3
FREE_SLOTS = 40
DEF_SPELLS= [1003, 1004, 1019]
VIEW_DEF_SPELLS = [1025]
INDESTRUCTABLE = [1026, 0]

PRICES:dict = {
    "SS": 20000,
    "S": 10000,
    "A": 5000,
    "B": 3000,
    "C": 1500,
    "D": 800,
    "E": 500,
    "F": 200,
    "G": 100,
    "H": 50
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

"""A word about **fakes**. Fakes can be created with the spell card 1020 and look like real cards in the book but are not. The main usecase I seem them as is bait. You can't sell fakes, you can't use them and they don't count towards the 100 card goal. 
If you want to swap out a fake in your album with a real card in your free slots or the other way around, use `swap <card_id>`. If you want to get rid of a fake, make sure it's in your free slots and discard it with `discard <card_id>`""",

"""You have reached the end of the introduction!

Now it's time for you to explore the world of cards, steal, collect, form alliances and so on. 

Do you want to add a card to the game you have a good idea for? That is possible, if you can make the card design with image we will be happy to have a look at your idea!

Have fun hunters
- The Gamemaster"""
]   


# FOR THE UWU COMMAND

ALIASES = {
    "hello": ["hyaaaa", "haiii"],
    "bye": ["baiiii", "bui", "bai"],
    "this": ["dis"],
    "that": ["dat"],
    "what": ["wat", "waa"],
    "because": ["cuz"],
    "and": ["&", "annnd", "n"],
    "cry": ["cri"],
    "no": ["nu", "noooo"],
    "why": ["wai"]
}

UWUS = ["uwu", "owo", "ʕ•́ᴥ•̀ʔっ", "≧◠ᴥ◠≦", ">\_<", "(◕ ˬ ◕✿)", "(・ω ・✿)", "(◕ㅅ◕✿)", " (◠‿◠✿)", " (◠‿◠)", " ̑̑ෆ(⸝⸝⸝◉⸝ ｡ ⸝◉⸝✿⸝⸝)", "(இ\_\_இ✿)", "✧w✧", "ಇ( ꈍᴗꈍ)ಇ", "( ᴜ ω ᴜ )", "ଘ(੭ ˘ ᵕ˘)━☆ﾟ.*･｡ﾟᵕ꒳ᵕ~", "ʕ ꈍᴥꈍʔ", "（´•(ｪ)•｀）", "(=^･ω･^=)", "/ᐠ . ֑ . ᐟ\ﾉ", "චᆽච", "♡(˶╹̆ ▿╹̆˵)و✧♡", "( o͡ ꒳ o͡ )",
"(´・ω・｀)", "Ꮚ･ω･Ꮚ", "꒰(͏ʻัꈊʻั)꒱", "꒰(͏ˊ•ꈊ•ˋ)꒱", "ʕᴥ·　ʔ", "ʕ º ᴥ ºʔ", "ʕ≧ᴥ≦ʔ", "▼・ᴥ・▼", "૮ ˘ﻌ˘ ა", "(ᵔᴥᵔ)", "꒰꒡ꆚ꒡꒱"]

# THE KILLUA SUPPORT SERVER AND ITS DATA
GUILD = 715358111472418908
BOOSTER_ROLE = 769622564648648744
REPORT_CHANNEL = 796306329756893184
UPDATE_CHANNEL = 757170264294424646

GUILD_OBJECT = discord.Object(id=GUILD)

# For the translate command
LANGS = {
    "auto": "autodetect",
    "afrikaans": "af", 
    "albanian": "sq", 
    "amharic": "am", 
    "arabic": "ar", 
    "armenian": "hy", 
    "azerbaijani": "az", 
    "basque": "eu", 
    "belarusian": "be", 
    "bengali": "bn", 
    "bosnian": "bs", 
    "bulgarian": "bg", 
    "catalan": "ca", 
    "cebuano": "ceb", 
    "chichewa": "ny", 
    "chinese-simplified": "zh-CN", 
    "chinese-traditional": "zh-TW", 
    "corsican": "co", 
    "croatian": "hr", 
    "czech": "cs", 
    "danish": "da", 
    "dutch": "nl", 
    "english": "en", 
    "esperanto": "eo", 
    "estonian": "et", 
    "filipino": "tl", 
    "finnish": "fi", 
    "french": "fr", 
    "frisian": "fy", 
    "galician": "gl", 
    "georgian": "ka", 
    "german": "de", 
    "greek": "el", 
    "gujarati": "gu", 
    "haitian creole": "ht", 
    "hausa": "ha", 
    "hawaiian": "haw", 
    "hebrew": "iw", 
    "hindi": "hi", 
    "hmong": "hmn", 
    "hungarian": "hu", 
    "icelandic": "is", 
    "igbo": "ig", 
    "indonesian": "id", 
    "irish": "ga", 
    "italian": "it", 
    "japanese": "ja", 
    "javanese": "jw", 
    "kannada": "kn", 
    "kazakh": "kk", 
    "khmer": "km", 
    "kinyarwanda": "rw", 
    "korean": "ko", 
    "kurdish": "ku", 
    "kyrgyz": "ky", 
    "lao": "lo", 
    "latin": "la", 
    "latvian": "lv", 
    "lithuanian": "lt", 
    "luxembourgish": "lb", 
    "macedonian": "mk", 
    "malagasy": "mg", 
    "malay": "ms", 
    "malayalam": "ml", 
    "maltese": "mt", 
    "maori": "mi", 
    "marathi": "mr", 
    "mongolian": "mn", 
    "myanmar": "my", 
    "nepali": "ne", 
    "norwegian": "no", 
    "odia": "or", 
    "pashto": "ps", 
    "persian": "fa", 
    "polish": "pl", 
    "portuguese": "pt", 
    "punjabi": "pa", 
    "romanian": "ro", 
    "russian": "ru", 
    "samoan": "sm", 
    "scots gaelic": "gd", 
    "serbian": "sr", 
    "sesotho": "st", 
    "shona": "sn", 
    "sindhi": "sd", 
    "sinhala": "si", 
    "slovak": "sk", 
    "slovenian": "sl", 
    "somali": "so", 
    "spanish": "es", 
    "sundanese": "su", 
    "swahili": "sw", 
    "swedish": "sv", 
    "tajik": "tg", 
    "tamil": "ta", 
    "tatar": "tt", 
    "telugu": "te", 
    "thai": "th", 
    "turkish": "tr", 
    "turkmen": "tk", 
    "ukrainian": "uk", 
    "urdu": "ur", 
    "uyghur": "ug",
    "uzbek": "uz", 
    "vietnamese": "vi", 
    "welsh": "cy", 
    "xhosa": "xh", 
    "yiddish": "yi", 
    "yoruba": "yo", 
    "zulu": "zu"
}

# FOR THE NOKIA COMMAND FOR /IMAGESCRIPT OF PXLAPI

NOKIA_CODE = """
let e = url.split(".").pop(); let ext = e.substring(0,e.length-(e.length-3)).replace("jpe", "jpeg");
const mybuffer = await fetch(url).then(r => r.arrayBuffer());
const mybuffer2 = await fetch("https://cdn.discordapp.com/attachments/762926280793784350/817847142668304444/1615060247537.png").then(r => r.arrayBuffer());

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
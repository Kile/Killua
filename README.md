## Killua Discord Bot
<p align="center">
  <a href"https://discord.com/oauth2/authorize?client_id=756206646396452975&scope=bot&permissions=268723414">
     <img src="https://cdn.discordapp.com/avatars/756206646396452975/30c2da6b0a777658021cbac239fa5e66.png?size=256">
  </a>
</p>
<p align="center">
  <a href="https://top.gg/bot/756206646396452975">
    <img src="https://top.gg/api/widget/756206646396452975.svg" alt="Killua" />
  </a>
 </p>
<h4 align="center">Games, Moderation, todo lists and much more.</h4>

<p align="center">
  <a href="https://discord.gg/zXqDHkm/">
    <img alt="Discord Server" src="https://img.shields.io/discord/691713541262147687.svg?label=Discord&logo=discord&logoColor=ffffff&color=7389D8&labelColor=6A7EC2&style=flat">
  </a>
  <a>
    <img alt="Lines" src="https://img.shields.io/tokei/lines/github/Kile/Killua">
  </a>
  <a>
    <img scr="https://img.shields.io/github/commit-activity/w/Kile/Killua">
  </a>
  <a href="https://github.com/Rapptz/discord.py/">
     <img src="https://img.shields.io/badge/discord-py-blue.svg" alt="discord.py">
  </a>
  <a href="https://killua.dev/">
    <img src="https://img.shields.io/website?down_color=lightgrey&down_message=offline&up_color=green&up_message=online&url=https%3A%2F%2Fkillua.dev">
  </a>
  <a>
    <img scr="https://img.shields.io/github/license/Kile/Killua">
  </a>
  <a>
    <img src="https://img.shields.io/github/contributors/Kile/Killua">
  </a>
  <a href="https://www.patreon.com/KileAlkuri">
    <img src="https://img.shields.io/badge/Support-Killua!-blue.svg" alt="Support Killua on Patreon!">
  </a>
  <a href="https://lgtm.com/projects/g/Kile/Killua/context:python"><img alt="Language grade: Python" src="https://img.shields.io/lgtm/grade/python/g/Kile/Killua.svg?logo=lgtm&logoWidth=18"/>
  </a>
</p>

## Details

Hello and thanks for checking out Killua's source code! I have been working on Killua for months and I learned Python by programming him. He is frequently updated with a team of developers, each doing their part. 

Website: https://killua.dev

Invite Killua to your guild [here](https://discord.com/oauth2/authorize?client_id=756206646396452975&scope=bot&permissions=268723414&applications.commands)

Feel free to add issues or PRs, I would really appreciate it

## What you need to run Killua locally

First, set up a virtual environment. Do so with `python3 -m venv env; source env/bin/activate`. To leave the virtual environment after you are done, simply run `deactivate`

`requirements.txt` contains the libraries you'll need and probably a few more. To install the libraries use `pip3 install -r requirements.txt`

Note: `discord-ext-ipc` will throw an internal error. To get rid of this, you need to go into its source code and delete/comment out every time `bot.dispatch` is called

You will need a mongodb account. Why do I use mongodb and not sql? In my opinion mongo is easier to use and you can manually add and remove data

You will have to create a mongodb account [here](https://www.mongodb.com), then follow the instructions in [`setup.py`](https://github/Kile/Killua/blob/main/setup.py) and then run `python3 setup.py` or choose the "setup database" option in the menu to get the database set up
  
  
You will also need a file named `config.json` having the layout like this:

```json
{
    "token": "token",
    
    "mongodb": "your-mongodb-token",
    "pxlapi": "pxlapi-token",
    "patreon": "patreon-api-token",
    "dbl_token": "dbl-token",
    "topgg_token": "topgg-token",
    "password": "vote-pages-password",
    "port": 8000,
    "ipc": "ipc-token"
}
```

You can finally run the bot in development or production enviornment in a menu by running `./run.sh`

If you don't like me using one of your images for the hug or pat command, please contact me on discord `Kile#0606` or on `killua.bot.help@gmail.com`

If you have any further questions, join my discord server or dm me!
<p align="center">
  <a href"https://discord.com/oauth2/authorize?client_id=756206646396452975&scope=bot&permissions=268723414">
     <img src="https://cdn.discordapp.com/attachments/759863805567565925/834794115148546058/image0.jpg">
  </a>
</p>

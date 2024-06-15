## Killua Discord Bot
<p align="center">
  <a href"https://discord.com/oauth2/authorize?client_id=756206646396452975&scope=bot&permissions=268723414">
     <img src="https://i.imgur.com/diOmUcl.png">
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

## What is Killua?

I started Killua as a way to learn python and different programming concepts. It definitely was not the easiest way to do it, but it got me to a good level of python knowledge plus having a cool bot! As a result, I greatly appreciate issues, PRs and contributions enhancing my code.

## Links

*   [Website](https://killua.dev)
*   [Support server](https://discord.gg/Jkd29QvhBP)
*   [Invite link](https://discord.com/oauth2/authorize?client_id=756206646396452975&scope=bot&permissions=268723414&applications.commands)
*   [Patreon](https://patreon.com/kilealkuri)

## Algorithms
Killua contains a number of interesting algorithms which I have explained more and gone into detail in the [algorithms](./algorithms/README.md) folder.

## Programming concepts list

As explained previously, I use Killua as a tool to learn more about python and programming. Here is a list of programming concepts Killua uses and which ones it is planned to use at some point in the future.

*   [x] OOP (Object Oriented Programming)
*   [x] Web scraping
*   [x] IPC (Inter Process Communication)
*   [x] Providing and requesting REST-APIs
*   [x] Image manipulation
*   [x] Asyncronous Programming
*   [x] logging
*   [x] NonSQL databases
*   [x] Python `typing` library
*   [x] GitHub PRs, branches, issues, todo-lists, CLI
*   [x] caching
*   [x] Website with backend
*   [x] CSS
*   [x] Threading
*   [x] Github workflows
*   [x] Docker
*   [x] Rust
*   [x] Prometheus
*   [x] Grafana

## Contributors

I would like to give a big thank you to everyone who has helped me on this journey, each in their different way.

*   [y21](https://github.com/y21)
> Helped me a lot with the Rust API rewrite, spotting an issue that took me8 months to track down as well as helping my code to be much cleaner.

*   [WhoAmI](https://github.com/WhoAmI1000)

> Who has been with the project since the start, creating the website and supporting it through Patreon.

*   [MNW](https://linktr.ee/Michaelnw_mnw)

> An incredibly talented artist who made many artworks which make Killua look and feel so much better for little to no price.

*   [ClashCrafter](https://github.com/FlorianStrobl)

> Contributed initial parts of the web scraping code.

*   [danii](https://github.com/danii)

> Helped to change the incredibly bad mess of everything in one file into an organised, dynamic system and helped out with git commands.

*   [DerUSBstick](https://github.com/DerUSBstick)

> He contributed a lot to one of the best looking commands, `book` which uses image generation to make your collection book filled with cards. More recently he also helped a lot with making voting confirmations look much better!

*   [Scarf](https://odaibako.net/u/ano_furi)

> Helped write some of the action texts, topics, 8ball responses and would you rather questions.

*   [Apollo-Roboto](https://github.com/Apollo-Roboto) 
> Wrote a great library to use Prometheus/Grafana with discord.py which became the template for the current implementation. He also assisted me with questions during this process.

*   [Vivany](https://vivany.carrd.co/)

> Found a lot of hug images and also tracked down most artists of previously used ones to give them credit making Killua a much more considerate bot.

*   [Scientia](https://github.com/ScientiaEtVeritas)

> Gave me the original idea for this bot and helped me in the early stages, enduring lots of pings and stupid questions.

## Running Killua locally

Regardless of how you decide to run Killua, you need to edit two files. `config.json` includes most of the configurations for Killua such as the bot token and the mongodb connection string. `api/Rocket.toml` includes configurations for the API such as the port it runs on. The main thing to edit here is secret_key which is the API's Auth key for things like the `/vote` endpoint. It is not recommended to edit the other values in this file.

Both of these files have a template in the same directory with the same name but with `.template` at the end. You can copy these files and edit them to your liking.

<details>
<summary><b>Running from source</b></summary>

While running Killua using Docker is more convenient, running from source is more flexible and allows you to make changes to the code and see them in action. To run Killua from source, follow these steps:

> [!IMPORTANT]
> Not running Killua in Docker will make you unable to use Grafana or Prometheus. The code handles this on its own but if you want to use either of these you must run Killua using docker-compose. You also do not need to run the rust proxy as the IPC connection will be direct.

### Bot process
First, set up a virtual environment. Do so with `python3 -m venv env; source env/bin/activate` (for linux). To leave the virtual environment after you are done, simply run `deactivate`

`requirements.txt` contains the libraries you'll need. To install them use `pip3 install -r requirements.txt`

Depending on if you self host mongodb or not, you may also need a mongodb. You can to create a mongodb account [here](https://www.mongodb.com), then follow the instructions in [`setup.py`](https://github/Kile/Killua/blob/main/setup.py) and then run `python3 setup.py` or choose the "setup database" option in the menu to get the database set up. As a warning, this script is rarely run so it may not be up to date.

The bot can be run using 
```sh
python3 -m killua
``` 
There are a number of command line options, you can see them by running 
```sh
python3 -m killua --help
```
most notabily the `--development` flag which will prevent the bot from caching all it needs on startup and requests local API versions instead of the server. This is useful for development.

### API
To start the API, ideally you should use a different Terminal or screen/tmux session and run `cd api; cargo run`
</details>

<details>
<summary><b>Running using Docker</b></summary>
Running from Docker, while taking longer to start up, is much more convenient and allows you to use Grafana and Prometheus. To run Killua using Docker, follow these steps:


1) Either clone the repo or pull the latest image from Docker Hub using `docker pull`
2) Edit the `config.json` and `api/Rocket.toml` files as explained above
3) Run `MODE=[dev|prod] docker compose up` in the root directory of the project. The mode specifies if you want to run the bot in development or production mode. Development mode will not cache anything and will use the local API instead of the server. If not provided, it will default to development mode.

</details>

## Contributing
> [!INFO]
> If you add any commands, please make sure to also add tests for it. A document explaining how tests for Killua work can be found [**here**](https://github.com/Kile/Killua/blob/main/killua/tests/README.md).
> This also applies to the API, if you add any endpoints, please make sure to add tests for them.

Contributions are always welcome! If you just want to contribute but don't know where to start, just contact me! I can help you find something to work on. If you have any questions, feel free to ask me on discord (`k1le`).

If you don't like me using one of your images for the hug command, please contact me on discord `k1le` or on `kile@killua.dev`

If you have any further questions, join my discord server or dm me!

<p align="center">
  <a href"https://discord.com/oauth2/authorize?client_id=756206646396452975&scope=bot&permissions=268723414">
     <img src="https://i.imgur.com/pNGbm5a.png">
  </a>
</p>

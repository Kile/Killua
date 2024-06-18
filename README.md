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

## Flowchart 
![setup](https://github.com/Kile/Killua/assets/69253692/186f027c-2941-45d9-ae40-2c71a339618d)

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
*   [] Dynamically deploying docker containers
*   [] Multithreading the bot (related to the above but can be static)

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

Regardless of how you decide to run Killua, you need to edit the `.env` file. This file contains all secrets needed for the bot to run. A few can be left the same as the template for debugging purpose, such as `MODE` which defined if the bot should run in development or production mode. The GF_ variables are the admin login for Grafana which can remain default unless you deploy the bot in production somewhere (which is stealing so please like - don't)

This file has a template in the same directory with the same name but with `.template` at the end. You can copy it and edit it to your liking.

Depending on if you self host mongodb or not, you may also need a mongodb account. You can to create a mongodb account [here](https://www.mongodb.com), then follow the instructions in [`setup.py`](https://github/Kile/Killua/blob/main/setup.py) and then run `python3 setup.py` or choose the "setup database" option in the menu to get the database set up. As a warning, this script is rarely run so it may not be up to date.

<details>
<summary><b>Running from source</b></summary>

While running Killua using Docker is more convenient, running from source is more flexible and allows you to make changes to the code and see them in action. To run Killua from source, follow these steps:

> WARNING:
> Not running Killua in Docker will make you unable to use Grafana or Prometheus. The code handles this on its own but if you want to use either of these you must run Killua using docker-compose. You also do not need to run the rust proxy as the IPC connection will be direct.

### Bot process
First, set up a virtual environment. Do so with `python3 -m venv env; source env/bin/activate` (for linux). To leave the virtual environment after you are done, simply run `deactivate`

`requirements.txt` contains the libraries you'll need. To install them use `pip3 install -r requirements.txt`

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


1) Clone the repository (you need the `docker-compose.yml` file)
2) Edit the `.env` file to your liking

If you want to contribute and test your changes:

3) Run `docker compose up --build -d` to build the images and start the containers

If you want to run the built images:

3) Run `docker compose up -d` to start the containers (it will pull the images from Docker Hub)

You can access Grafana on port 3000. The configured dashboard should already be added. You can access it after logging in with username `admin` and password `admin` (unless you changed it in the env file). Prometheus can be accessed on port 8000. The API can be accessed on port 6060.

Note: if you want to expose Grafana on nginx, you need to add `proxy_set_header Host $http_host;` to the `server` config.
</details>

## Contributing
Before I start talking about contributing, I want to mention an area of Killua of which traces can be found of but it is not yet complete. This is due to me working on it for a few while and not enjoying it to a point where I decided to postpone development. This is my own testing framework for dpy. This can be found in [`killua/tests`](./killua/tests/). A part of this is also downloading all card data from somewhere so these tests can be run by someone who does not have them in their mongodb database like me. Both of these are incomplete. 


### What to work on
Contributions are MASSIVELY appreciated. A codebase this big can look a bit intimidating so if you would like to contribute but don't know where to start, here are some suggestions:
*  **Documentation**: I try to document what I can but ultimately most of this lives in my head so I have never needed to provide detailed documentation. If you see something that is not documented or could be documented better, feel free to make a PR.
*  **Multiple languages**: I would love to have Killua be available in multiple languages. You do not need to speak a language other than English to build a framework for it. I can organize translators. I have attempted this previously but got insanely burned out quickly. Discord offers a way to get the language of the user so all needed is to build a smart system to use this data.
*  **Testing**: I have a testing framework in place but it is not complete. I would love to have a system where I can run tests on the bot and get a report of what failed and why. This is a big project and probably overengineered but it could be INSANELY useful. It was originally planned to **need** to get done for a non alpha/beta 1.0 version to get published but ultimately I don't have enough time to finish it currently so it has been removed from the roadmap of that release.
* **Image generation**: I have a few commands that generate images. I rely on pxlapi for quite a few of them which is fine but if you have any other ideas (can be simple copy paste into another image) then feel free to PR them! They are always a lot of fun to use.
* **An RPG system**: I am in the early stages of thinking about an RPG system using hxh's "Nen" system and building out the hunt command for a more interactive fun experience. I will likely work on this myself but I would love some help.
* **Web development**: I have a website but it not very advanced. Frontend is my weak spot. If you would like to help me to build out the website, I am happy to write backend code for it. Please contact me if you are interested in this.


> [!NOTE]
> (If the testing system works for the bot) If you add any commands, please make sure to also add tests for it. A document explaining how tests for Killua work can be found [**here**](./killua/tests/README.md).
> This also applies to the API, if you add any endpoints, please make sure to add tests for them.


## Grafana
Grafana is pretty cool. The Grafana dashboard was added in version 1.1.0. You can find it in grafana/dashboards/main.json. Here are some screenshots:

If you use Docker to run Killua, this would work without any additional setup. I also welcome contributions to the Grafana dashboard (maybe even add more analytics to the code!). You are also free to use my dashboard for your own bot if you want to, most of the saved data logic can be found in [`killua/cogs/prometheus.py`](./killua/cogs/prometheus.py) and [`killua/metrics/`](./killua/metrics/).

If you don't like me using one of your images for the hug command, please contact me on discord `k1le` or on `kile@killua.dev`

If you have any further questions, join my discord server or dm me!

<p align="center">
  <a href"https://discord.com/oauth2/authorize?client_id=756206646396452975&scope=bot&permissions=268723414">
     <img src="https://i.imgur.com/pNGbm5a.png">
  </a>
</p>

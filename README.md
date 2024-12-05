## Killua Discord Bot
<p align="center">
  <a href="https://discord.com/oauth2/authorize?client_id=756206646396452975&scope=bot&permissions=268723414">
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
*   [x] Asynchronous Programming
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
*   [ ] Dynamically deploying docker containers/Kubernetes
*   [ ] Custom sharding the bot (related to the above)

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

### Assets
Killua uses a lot of images. These are stored in the `assets` folder. Some assets are gitignored and will not be in this folder. These are mainly all `cards` images except the `PLACEHOLDER`s and all hugs except `0.gif`. This is to avoid revealing secrets about the game and to avoid yoinking people's art for the hug images. The bot should still run out of the box without these. For local development, you should not need these images. However if you do want to use them, you need to edit `cards.json` or `hugs.json` respectively to point to the correct image you upload. The bot is not designed to handle a card url that does not have an asset associated with it, so if you want to use the `private` cards, you need to supply all images. More about this in the next section. Similarly if you change the only hug image that is not gitignored but not its data in `hugs.json`, it will not work.

### If you want to use/edit the "Greed Island" game locally
The default behavior for where the bot gets all the card data from is a censored list from the remote API `api.killua.dev/cards.json?public=true`. (The public list if it is run in dev mode, the non-censored list requires authorization). This is intended to work out of the box when you first run Killua locally. If you would like to edit the list of cards though, you can instead force Killua to instead request that endpoint from your local instance of the API. To do this, run Killua with the `--force-local` or `-fl` flag. This will instead request localhost or the Docker container the API runs in.

To use the local cards endpoint, you need to download the `cards.json` file. You can do this by running `python3 -m killua --download <public/private>` where `<public/private>` is the type of cards you want to download (private will require the API_KEY env variable set as it is the uncensored version). This will download the cards from the remote API and save them in the right directory (`cards.json`). You can edit these freely, however spell cards and their effects are in the code and not that file, so using a spell card ID will still behave as a spell card.

If you are running the bot using Docker (and build it locally with the `--build` flag), the default behavior is to use the remote API if in dev mode, and the local API in production mode. This is so development is plug and play and production runs faster by directly requesting another container rather than the internet. To change this, go into the `Dockerfile` in the `killua` directory and edit the arguments passed to the bot in the last line (`CMD`). You can add the `--force-local` flag to force the bot to use the local which will then request the API container instead.

> [!INFO] 
> Even when using `--force-local`, your local cards will still be censored if in dev mode. To prevent this, omit the `--development` or `-d` flag when running the bot. The censored version is still designed in a way that will let you test most of the functionality (eg name autocomplete, images in the book command etc) so most of the time this will not really be necessary. You may need to replace the emoji though as some code needs it to be a custom emoji.

### MongoDB Atlas
Depending on if you self host mongodb or not, you may also need a mongodb account. You can to create a mongodb account [here](https://www.mongodb.com), then create a collection called "Killua". You can then create a user with read and write permissions to this collection. You can then add the connection string to the `.env` file. Killua should automatically create the needed collections and indexes on startup. However this is rarely tested so please contact me if you encounter any issues.

<details>
<summary><b>Why do I use mongoDB instead of SQL?</b></summary>
The short answer is, it's because what I was introduced to first. 

But I have come to like it and chosen not to migrate for two reasons:
  
  * I am bad at joining tables in SQL. I prefer every piece of data I need returned by just on request
  * Because I am using mongoDB atlas, I don't have to worry about backups or how to migrate my db - it always stays in the same place in the cloud, making server migration insanely easy.
</details>

<details>
<summary><b>Running from source</b></summary>

While running Killua using Docker is more convenient, running from source is more flexible and allows you to make changes to the code and see them in action. To run Killua from source, follow these steps:

> WARNING:
> Not running Killua in Docker will make you unable to use Grafana or Prometheus. The code handles this on its own but if you want to use either of these you must run Killua using docker-compose. You also do not need to run the rust proxy as the IPC connection will be direct.

### Bot process
First, set up a virtual environment. Do so with `python3 -m venv env; source env/bin/activate` (for linux and macOS). To leave the virtual environment after you are done, simply run `deactivate`

`requirements.txt` contains the libraries you'll need. To install them use `pip3 install -r requirements.txt`

Before you run anything, unlike Docker where the env variables are automatically exported, you need to do it manually. For this you can run 
```sh
export $(cat .env | xargs)
# or to ignore comments started with #
export $(grep -v '^#' .env | xargs)
```

You can remove these exports again with 
```sh
unset $(cat .env | xargs)
# or to ignore comments started with #
unset $(grep -v '^#' .env | xargs)
```

### Bot
The bot can be run using 
```sh
python3 -m killua
``` 
There are a number of command line options, you can see them by running 
```sh
python3 -m killua --help
```
most notably the `--development` flag which will prevent the bot from caching all it needs on startup and requests local API versions instead of the server. This is useful for development.

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

If you want to run the pre-built images from the registry:

3) Run `docker compose up -d` to start the containers (it will pull the images from the GitHub registry)

You can access Grafana on port 3000. The configured dashboard should already be added. You can access it after logging in with username `admin` and password `admin` (unless you changed it in the env file). Prometheus can be accessed on port 8000. The API can be accessed on port 6060.

Note: if you want to expose Grafana on nginx, you need to add `proxy_set_header Host $http_host;` to the `server` config.
</details>

## Contributing
Before I start talking about contributing, I want to mention an area of Killua of which traces can be found of but it is not yet complete. This is due to me working on it for a few while and not enjoying it to a point where I decided to postpone development. This is my own testing framework for dpy. This can be found in [`killua/tests`](./killua/tests/). This system is incomplete though occasionally some structural changes are made to offer better support to it. 


### What to work on
Contributions are MASSIVELY appreciated. A codebase this big can look a bit intimidating so if you would like to contribute but don't know where to start, here are some suggestions:
*  **Documentation**: I try to document what I can but ultimately most of this lives in my head so I have never needed to provide detailed documentation. If you see something that is not documented or could be documented better, feel free to make a PR.
*  **Multiple languages**: I would love to have Killua be available in multiple languages. You do not need to speak a language other than English to build a framework for it. I can organize translators. I have attempted this previously but got insanely burned out quickly. Discord offers a way to get the language of the user so all needed is to build a smart system to use this data.
*  **Testing**: I have a testing framework in place but it is not complete. I would love to have a system where I can run tests on the bot and get a report of what failed and why. This is a big project and probably overengineered but it could be INSANELY useful. It was originally planned to **need** to get done for a non alpha/beta 1.0 version to get published but ultimately I don't have enough time to finish it currently so it has been removed from the roadmap of that release. Especially after the sync -> async change for any DB class, this needs a rewrite/update.
* **Image generation**: I have a few commands that generate images. I rely on pxlapi for quite a few of them which is fine but if you have any other ideas (can be simple copy paste into another image) then feel free to PR them! They are always a lot of fun to use.
* **An RPG system**: I am in the early stages of thinking about an RPG system using hxh's "Nen" system and building out the hunt command for a more interactive fun experience. I will likely work on this myself but I would love some help.
* **Web development**: I have a website but it not very advanced. Frontend is my weak spot. If you would like to help me to build out the website, I am happy to write backend code for it. Please contact me if you are interested in this.
* **Change text commands to generate images**: Commands such as `profile`, `gstats` and `server` all display their stats in text. This is ok for some (`profile` still looks ok) but generally would look much better as a generated image with fancy background etc. This is not a big project so this would be a good starting point for someone who wants to contribute but doesn't know where to start. The rust API could also be used for this in favour of making this more efficient and CPU friendly but it does not have to be.


> [!NOTE]
> (If the testing system works for the bot) If you add any commands, please make sure to also add tests for it. A document explaining how tests for Killua work can be found [**here**](./killua/tests/README.md).
> This also applies to the API, if you add any endpoints, please make sure to add tests for them.


## Grafana
Grafana is pretty cool. The Grafana dashboard was added in version 1.1.0. You can find it in grafana/dashboards/main.json. Here are some screenshots:
<img width="1280" alt="image" src="https://github.com/user-attachments/assets/9b103b43-9428-491c-903f-7cadeb0ac7aa">
<img width="1277" alt="image" src="https://github.com/user-attachments/assets/23c1b7b2-6818-479d-86d9-186c4498f8b6">
<img width="1249" alt="image" src="https://github.com/user-attachments/assets/9dee6e3a-febf-4bc6-b69c-a69145fb8204">
<img width="1376" alt="image" src="https://github.com/Kile/Killua/assets/69253692/0a0560d3-c5ba-4acf-abe9-a6cf4ef29de8">
<img width="1379" alt="image" src="https://github.com/Kile/Killua/assets/69253692/222063c9-60ae-4f8b-8b67-cdb6a90b586c">
<img width="1376" alt="image" src="https://github.com/Kile/Killua/assets/69253692/49926a8d-a85f-4ba0-80fc-a97c84557095">



If you use Docker to run Killua, this would work without any additional setup. I also welcome contributions to the Grafana dashboard (maybe even add more analytics to the code!). You are also free to use my dashboard for your own bot if you want to, most of the saving data logic can be found in [`killua/cogs/prometheus.py`](./killua/cogs/prometheus.py) and [`killua/metrics/`](./killua/metrics/).


## Thanks for checking this repo out!
If you don't like me using one of your images for the hug command, please contact me on Discord `k1le` or at `kile@killua.dev`

If you have any further questions, join my discord server or dm me!

If you think I did a good job at this now pretty massive codebase I spent years working on, a star would be much appreciated!!

<p align="center">
  <a href"https://discord.com/oauth2/authorize?client_id=756206646396452975&scope=bot&permissions=268723414">
     <img src="https://i.imgur.com/pNGbm5a.png">
  </a>
</p>

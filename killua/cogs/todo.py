import discord
from discord.ext import commands
from killua.functions import custom_cooldown, blcheck
import pymongo
from pymongo import MongoClient
import asyncio
import typing
from random import randint
from datetime import datetime
import re
import math
import json
from json import loads

with open('config.json', 'r') as config_file:
	config = json.loads(config_file.read())

cluster = MongoClient(config['mongodb'])
killuadb = cluster['Killua']
generaldb = cluster['general']
teams = killuadb['teams']
todo = generaldb['todo']

editing = {}

class TodoSystem(commands.Cog):

    def __init__(self,client):
        self.client = client


    @commands.group()
    async def todo(self, ctx):
        #h You most likely want info about another todo command. Use `k!help command todo <todo_command>` for that
        if blcheck(ctx.author.id) is True:
            return

    @custom_cooldown(20)
    @todo.command()
    async def create(self, ctx):
        #u todo create
        #h Let's you create your todo list in an interactive menu
        x = 0
        
        user_todo_lists = todo.find({'owner': ctx.author.id})
        try:
            for l in user_todo_lists:
                x +1
        except Exception:
            pass
        if x == 5:
            return ctx.send('You can currently not own more than 5 todo lists')

        title  = await todo_name(self, ctx)
        if title is None:
            return

        status = await todo_status(self, ctx)
        if status is None:
            return 

        done_delete = await todo_done_delete(self, ctx)
        if done_delete is None:
            return


        todo_id = int(generate_id())
        user = teams.find_one({'id': ctx.author.id})
        if not user is None:
            if 'premium' in user['badges'] or 'staff' in user['badges']:
                custom = await todo_custom_id(self, ctx, todo_id, title, status, done_delete)
                if custom is True:
                    return
                elif custom is False:
                    pass
                
        await ctx.send(f'Created the todo list with the name {title}. You can look at it and edit it through the id `{todo_id}`')
        todo.insert_one({'_id': todo_id, 'name': title, 'owner': ctx.author.id, 'custom_id': None, 'status': status, 'delete_done': done_delete, 'viewer': [], 'editor': [], 'todos': [{'todo': 'add todos', 'marked': None, 'added_by': 756206646396452975, 'added_on': (datetime.now()).strftime("%b %d %Y %H:%M:%S"), 'views':0, 'assigned_to': [], 'mark_log': []}], 'marks': [], 'created_at': (datetime.now()).strftime("%b %d %Y %H:%M:%S"), 'spots': 10, 'views': 0 })

    @custom_cooldown(5)
    @todo.command()
    async def view(self, ctx, todo_id=None):
        #u todo view <list_id(optional)>
        #h Allows you to view what is on any todo list- provided you have the permissions
        if todo_id is None:
            try:
                list_id = editing[ctx.author.id]
            except KeyError:
                return await ctx.send('You have to be in the editor mode to use this command without providing an id! Use `k!todo edit <todo_list_id>`')

            todo_id = str(list_id)

        if todo_id.isdigit():
            todo_id = int(todo_id)
            todo_list = todo.find_one({'_id': todo_id})
        else:
            todo_list = todo.find_one({'custom_id': todo_id.lower()})
        

        if todo_list is None:
            return await ctx.send('No todo list with specified ID found')

        if todo_list['status'] == 'private':
            if not (ctx.author.id in todo_list['viewer'] or ctx.author.id in todo_list['editor'] or ctx.author.id == todo_list['owner']):
                return await ctx.send('This is a private list you don\'t have the permission to view')
            if len(todo_list['todos']) > 10:
                return await todo_menu_embed_generator(self, ctx, todo_id, 1)
            else:
                embed = await todo_embed_generator(self, ctx, todo_id)
                return await ctx.send(embed=embed)
        else:
            if not ctx.author.id == todo_list['owner'] and not ctx.author.id in todo_list['viewer'] and ctx.author.id in todo_list['editor']:
                todo.update_one({'_id': todo_id}, {'$set':{'views': todo_list['views']+1 }})
            
            if len(todo_list['todos']) > 10:
                return await todo_menu_embed_generator(self, ctx, todo_id, 1)
            else:
                embed = await todo_embed_generator(self, ctx, todo_id)
                return await ctx.send(embed=embed)

    @custom_cooldown(5)
    @todo.command()
    async def info(self, ctx, todo_or_task_id=None, td:int=None):
        #u todo info <list_id/task_id> <task_id(if list id provided)>
        #h This gives you info about either a todo task or list
            if td is None:
                if todo_or_task_id is None:
                    try:
                        list_id = editing[ctx.author.id]
                    except KeyError:
                        return await ctx.send('You need to be in editor mode for a list or provide an id to use this command')
                    return await todo_info_embed_generator(self, ctx, list_id)
                try:
                    list_id = editing[ctx.author.id]
                except KeyError:
                    return await todo_info_embed_generator(self, ctx, todo_or_task_id)
                return await single_todo_info_embed_generator(self, ctx, int(todo_or_task_id), list_id)
            elif td:
                return await single_todo_info_embed_generator(self, ctx, td, todo_or_task_id)

    @custom_cooldown(5)
    @todo.command()
    async def edit(self, ctx, todo_id):
        #u todo edit <todo_id>
        #h The command with which you can change stuff on your todo list
        if todo_id.isdigit():
            todo_id = int(todo_id)
            todo_list = todo.find_one({'_id': todo_id})
        else:
            todo_list = todo.find_one({'custom_id': todo_id.lower()})

        if todo_list is None:
            return await ctx.send('No todo list with this id')

        if not (ctx.author.id in todo_list['editor'] or ctx.author.id == todo_list['owner']):
            return await ctx.send('You do not have the permission to edit this todo list')
        await ctx.send(f'You are now in editor mode for todo list "{todo_list["name"]}"')
        editing[ctx.author.id] = todo_list['_id']

    @custom_cooldown(20)
    @todo.command()
    async def name(self, ctx, new_name:str):
        #u todo name <new_name>
        #h Rename your todo list with thsi command (Only in editor mode)
        try:
            list_id = editing[ctx.author.id]
        except KeyError:
            return await ctx.send('You have to be in the editor mode to use this command! Use `k!todo edit <todo_list_id>`')
        todo_list = todo.find.one({'_id': list_id})
        if len(name) > 30:
            return await ctx.send('You can\'t have more than 30 characters in a name!')
        todo.update_one({'_id': list_id}, {'$set':{'name': new_name}})
        await ctx.send(f'Done! Update your todo list\'s name to "{new_name}"')

    @custom_cooldown(20)
    @todo.command()
    async def status(self, ctx, status):
        #u todo status <new_status>
        #h Change the status of your todo list (public/private) with this command (Only in editor mode)
        try:
            list_id = editing[ctx.author.id]
        except KeyError:
            return await ctx.send('You have to be in the editor mode to use this command! Use `k!todo edit <todo_list_id>`')
        if not status.lower() in ['private', 'public']:
            return await ctx.send('You need to chose a valid status (private/public)')
        todo.update_one({'_id'}, {'$set': {'status': status-lower()}})
        await ctx.send(f'Done! Updated your todo list\'s status to `{status.lower()}`')

    @custom_cooldown(20)
    @todo.command()
    async def color(self, ctx, color):
        #u todo color <new_color_in_hex>
        #h Change your todo list's color with this command (Only in editor mode)
        try:
            list_id = editing[ctx.author.id]
        except KeyError:
            return await ctx.send('You have to be in the editor mode to use this command! Use `k!todo edit <todo_list_id>`')
        todo_list = todo.find_one({'_id': list_id})
        try:
            current_color = todo_list['color']
        except KeyError:
            return await ctx.send('You need to have bought this feature for your current todo list with `k!todo buy color`')
            
        c = f'0x{color}'
        try:
            if not int(c, 16) <= 16777215:
                await ctx.send('You need to provide a valid color! (Default color is 1400ff f.e.)')
        except:
            await ctx.send('You need to provide a valid color! (Default color is 1400ff f.e.)')

        todo.update_one({'_id': list_id}, {'$set':{'color': int(c, 16)}})
        await ctx.send(f'Done! Updated your todo list\'s color to `{c}`')

    @custom_cooldown(20)
    @todo.command()
    async def thumbnail(self, ctx, url):
        #u todo thumbnail <new_thumbnail>
        #h Change your todo lists thumbnail with this command (Only in editor mode)
        try:
            list_id = editing[ctx.author.id]
        except KeyError:
            return await ctx.send('You have to be in the editor mode to use this command! Use `k!todo edit <todo_list_id>`')
        todo_list = todo.find_one({'_id': list_id})

        try:
            current_url = todo_list['thumbnail']
        except KeyError:
            return await ctx.send('You need to have bought this feature for your current todo list with `k!todo buy color`')

        search_url = re.search(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))', url)

        if search_url:
            image = re.search(r'png|jpg|gif|svg', url)
        else:
            await ctx.send('You didn\'t provide a valid url with an image! Please make sure you do that')
            
        if image:
            todo.update_one({'_id': list_id},{'$set':{'thumbnail': url}})
            return await ctx.send(f'Done! Updated your todo list\'s thumbnail to `{url}`')
        else:
            await ctx.send('You didn\'t provide a valid url with an image! Please make sure you do that')

    @custom_cooldown(20)
    @todo.command()
    async def custom_id(self, ctx, custom_id):
        #u todo custom_id <new_id>
        #h Lets you change your todo lists custom id- provided you are premium supporter (Only in editor mode)
        try:
            list_id = editing[ctx.author.id]
        except KeyError:
            return await ctx.send('You have to be in the editor mode to use this command! Use `k!todo edit <todo_list_id>`')
        user = teams.find_one({'id': ctx.author.id})
        if not ('staff' in user['badges'] or 'premium' in user['badges']):
            return await ctx.send('Nice try, but you need to be a premium supporter of Killua to create a custom id')

        if len(custom_id) > 20:
            return await ctx.send('Your custom id can not have more than 20 characters')

        if custom_id.lower() == '-rm' or custom_id.lower() == '-r':
            todo.update_one({'_id': list_id}, {'$set':{'custom_id': None}})
            return await ctx.send(f'Done! Removed the custom id from your list')
        todo.update_one({'_id': list_id}, {'$set':{'custom_id': custom_id}})
        return await ctx.send(f'Done! Updated your todo list\'s custom id to `{custom_id}`')

    @custom_cooldown(20)
    @todo.command()
    async def autodelete(self, ctx, on_or_off):
        #u todo autodelete <on/off>
        #h Let's you change if you mark a todo task as done if it should automatically delete it or not (Only in editor mode)
        try:
            list_id = editing[ctx.author.id]
        except KeyError:
            return await ctx.send('You have to be in the editor mode to use this command! Use `k!todo edit <todo_list_id>`')
        if not on_or_off.lower() in ['on', 'off']:
            return await ctx.send('You either need to activate this feature (**on**) or deactivate it (**off**)')
        
        todo_list = todo.find_one({'_id': list_id})

        if on_or_off.lower() == 'on':
            if todo_list['delete_done'] is True:
                return await ctx.send('You already have this feature enabled')
            todo.update_one({'_id': list_id},{'$set':{'delete_done': True}})
            return await ctx.send(f'Done! Activated your lists auto delete feature when something is marked as `done`')
        elif on_or_off.lower() == 'off':
            if todo_list['delete_done'] is False:
                return await ctx.send('You already have this feature enabled')
            todo.update_one({'_id': list_id},{'$set':{'delete_done': False}})
            return await ctx.send(f'Done! Deactivated your lists auto delete feature when something is marked as `done`')

    @custom_cooldown(10)
    @todo.command()
    async def remove(self, ctx, todo_numbers: commands.Greedy[int]):
        #u todo remove <task_id>
        #h Remove a todo with this command. YAY, GETTING THINGS DONE!! (Only in editor mode)
        try:
            list_id = editing[ctx.author.id]
        except KeyError:
            return await ctx.send('You have to be in the editor mode to use this command! Use `k!todo edit <todo_list_id>`')
        
        todo_list = todo.find_one({'_id': list_id})
        for n in todo_numbers:
            if n < 0:
                return await ctx.send('You can\'t remove a number less than 1')
        try:
            todos = todo_list['todos']
            for n in todo_numbers:
                todos.pop(n-1)
            todo.update_one({'_id': list_id}, {'$set':{'todos': todos}})
            return await ctx.send(f'You removed todo number{"s" if len(todo_numbers) > 1 else ""} {", ".join(todo_numbers)} successfully')
        except:
            return await ctx.send('You need to provide only valid numbers!')

    @custom_cooldown(5)
    @todo.command()
    async def mark(self, ctx, todo_number:int, *,marked_as:str):
        #u todo mark <task_id> <text>
        #h Mark a todo with a comment like `done` or `too lazy` (Only in editor mode)
        try:
            list_id = editing[ctx.author.id]
        except KeyError:
            return await ctx.send('You have to be in the editor mode to use this command! Use `k!todo edit <todo_list_id>`')
        
        todo_list = todo.find_one({'_id': list_id})
        todos = todo_list['todos']
        try:
            if todo_number == 0:
                raise 'Error!'
            t = todos[todo_number-1]
        except:
            return await ctx.send(f'You don\'t have a number {todo_number} on your current todo list')

        if  marked_as.lower() == 'done' and todo_list['delete_done'] is True:
            todos.pop(todo_number-1)
            todo.update_many({'_id': list_id},{'$set':{'todos': todos}}, upsert=True)
            return await ctx.send(f'Marked to-do number {todo_number} as done and deleted it per default')
        elif marked_as.lower() == '-r' or marked_as.lower() == '-rm':
            todos[todo_number-1]['marked'] = None
            mark_log = {
                'author': ctx.author.id,
                'change': 'REMOVED MARK',
                'date': (datetime.now()).strftime("%b %d %Y %H:%M:%S")
            }
            todos[todo_number-1]['mark_log'].append(mark_log)
            todo.update_many({'_id': list_id},{'$set':{'todos': todos}}, upsert=True)
            return await ctx.send(f'Removed to-do number {todo_number} successfully!')
        else:
            todos[todo_number-1]['marked'] = marked_as
            mark_log = {
                'author': ctx.author.id,
                'change': marked_as,
                'date': (datetime.now()).strftime("%b %d %Y %H:%M:%S")
            }
            todos[todo_number-1]['mark_log'].append(mark_log)
            todo.update_many({'_id': list_id},{'$set':{'todos': todos}}, upsert=True)
            return await ctx.send(f'Marked to-do number {todo_number} as `{marked_as}`!')

    @custom_cooldown(10)
    @todo.command()
    async def buy(self, ctx, what):
        #u todo buy <item>
        #h Buy cool stuff for your todo list with this command! (Only in editor mode)
        try:
            list_id = editing[ctx.author.id]
        except KeyError:
            return await ctx.send('You have to be in the editor mode to use this command! Use `k!todo edit <todo_list_id>`')
        user = teams.find_one({'id': ctx.author.id})
        if user is None:
            return await ctx.send('This is a feature you have to buy, to gain Jenny claim `k!daily`')
        
        if not what.lower() in ['color', 'thumbnail', 'space', 'description']:
            return await ctx.send('You need to provide a valid thing you want to buy (color, thumbnail, space)')

        if what.lower() == 'color':
            return await buy_color(self, ctx)
        elif what.lower() == 'thumbnail':
            return await buy_thumbnail(self, ctx)
        elif what.lower() == 'space':
            return await buy_space(self, ctx)
        elif what.lower() == 'description':
            return await buy_description(self, ctx)

    @custom_cooldown(2)
    @todo.command()
    async def shop(self, ctx):
        #u todo shop
        #h Get some info about what cool stuff you can buy for your todo list with this command
        embed = discord.Embed.from_dict({
            'title': '**The todo shop**',
            'description': '''You can buy the following items with `k!todo buy <item>` while you are in the edit menu for the todo list you want to buy the item for
            
**Cost**: 1000 Jenny
`color` change the color of the embed which displays your todo list!

**Cost**: 1000 Jenny
`thumbnail` add a neat thumbnail to your todo list (small image on the top right)

**Cost**: 1000 Jenny
`description` add a description to your todo list (recommended for public lists with custom id)

**Cost**: number of current spots * 100
Buy 10 more spots for todos for your list''',
            'color': 0x1400ff
        })
        await ctx.send(embed=embed)

    @custom_cooldown(4)
    @todo.command()
    async def add(self, ctx, *, td):
        #u todo add <text>
        #h Add a todo to your list, *yay, more work* (Only in editor mode)
        try:
            list_id = editing[ctx.author.id]
        except KeyError:
            return await ctx.send('You have to be in the editor mode to use this command! Use `k!todo edit <todo_list_id>`')

        todo_list = todo.find_one({'_id': list_id})

        if len(td) > 100:
            return await ctx.send('Your todo can\'t have more than 100 characters')
        
        if len(todo_list['todos']) >= todo_list['spots']:
            return await ctx.send(f'You don\'t have enough spots for that! Buy spots with `k!todo buy space`. You can currently only have up to {todo_list["spots"]} spots in this list')

        todos = todo_list['todos']
        todos.append({'todo': td, 'marked': None, 'added_by': ctx.author.id, 'added_on': (datetime.now()).strftime("%b %d %Y %H:%M:%S"),'views': 0, 'assigned_to': [], 'mark_log': []})

        todo.update_one({'_id': list_id},{'$set':{'todos': todos}})
        return await ctx.send(f'Great! Added {td} to your todo list!')

    @custom_cooldown(5)
    @todo.command()
    async def kick(self, ctx, user: typing.Union[discord.User, int]):
        #u todo kick <user>
        #h Kick someone with permissions from your todo list (this takes **every** permission) (Only in editor mode)
        try:
            list_id = editing[ctx.author.id]
        except KeyError:
            return await ctx.send('You are not editing a list at the moment')
        todo_list = todo.find_one({'_id': list_id})

        if isinstance(user, int):
            try:
                user = client.fetch_user(user)
            except:
                return await ctx.send('Invalid ID')

        if not ctx.author.id == todo_list['owner']:
            return await ctx.send('You have to own the todo list to remove permissions from users')
            
        if not (user.id in todo_list['viewer'] or user.id in todo_list['editor']):
            return await ctx.send('The user you specified doesn\'t have permission to view or edit the todo list, you can\'t take permissions you never granted')

        if user.id in todo_list['editor']:
            editor = todo_list['editor']
            editor.remove(user.id)
            todo.update_many({'_id': list_id},{'$set':{'editor': editor}}, upsert=True)
            await ctx.send(f'You have successfully taken the editor permission from {user}')

        if user.id in todo_list['viewer']:
            viewer = todo_list['viewer']
            viewer.remove(user.id)
            todo.update_many({'_id': list_id},{'$set':{'viewer': viewer}}, upsert=True)
            await ctx.send(f'You have successfully taken the viewer permission from {user}')

    @custom_cooldown(4)
    @todo.command()
    async def exit(self, ctx):
        #u todo exit
        #h Exit editing mode with this. I've never used it because it is pointless because my code is so good you realistically never need to be out of editing mode but it is here so use it 
        try:
            list_id = editing[ctx.author.id]
        except KeyError:
            return await ctx.send('You are not editing a list at the moment')
        
        editing.pop(ctx.author.id, None)
        return await ctx.send('Exiting editing mode!')

    @custom_cooldown(20)
    @todo.command()
    async def invite(self, ctx, user: typing.Union[discord.User, int], role):
        #u todo invite <user> <editor/viewer>
        #h Wanna let your friend add more todos for you? Invite them! You can also make people view your todo list when it is set on private (Only in editor mode)
        try:
            list_id = editing[ctx.author.id]
        except KeyError:
            return await ctx.send('You have to be in the editor mode to use this command! Use `k!todo edit <todo_list_id>`')

        if isinstance(user, int):
            try:
                user = self.client.fetch_user(user)
            except:
                return await ctx.send('Invalid user id')

        if user.id == ctx.author.id:
            return await ctx.send('You are already owner, you don\'t need to invite yourself')

        if blcheck(user.id) is True:
            return await ctx.send('You can\'t invite a blacklisted user')
        
        todo_list = todo.find_one({'_id': list_id})

        if not role.lower() in ['editor', 'viewer']:
            return await ctx.send(f'Please choose a valid role to grant {user.name} (either `viewer` or `editor`)')

        embed = discord.Embed.from_dict({
            'title': f'You were invited to to-do list {todo_list["name"]} (ID: {todo_list["_id"]})',
            'description': f'{ctx.author} invited you to be {role} in their to-do list. To accept, reply with **[y/n]**. To report abuse/harrassment, reply with **r**',
            'color': 0x1400ff,
            'footer': {'icon_url': str(ctx.author.avatar_url), 'text': f'Requested by {ctx.author}'}
        })

        try:
            await user.send(embed=embed)
            await ctx.send('Successfully send the invitation to the specified user! They have 24 hours to accept or deny')
        except:
            return await ctx.send('Failed to send the user a dm. Make sure they are on a guild Killua is on and has their dms open')

        def check(m):
            return m.author.id == user.id and m.guild is None and m.content.lower() in ['y', 'n', 'r']

        try:
            confirmmsg = await self.client.wait_for('message', check=check, timeout=86400)
        except asyncio.TimeoutError:
            try:
                await user.send('Time to respond is up')
            except:
                pass
            return await ctx.author.send(f'{user} has not responded to your invitation in 24 hours so the invitation went invalid')
        else:
            if confirmmsg.content.lower() == 'y':
                if role.lower() == 'viewer':
                    others = todo_list['viewer']
                    others.append(user.id)
                    todo.update_many({'_id': list_id},{'$set':{'viewer': others}}, upsert=True)

                if role.lower() == 'editor':
                    others = todo_list['editor']
                    others.append(user.id)
                    todo.update_many({'_id': list_id},{'$set':{'editor': others}}, upsert=True)

                await user.send(f'Sucess! You have now {role} permissions in the todo list `{todo_list["name"]}`')
                return await ctx.author.send(f'{user} accepted your invitation to your todo list `{todo_list["name"]}`!')

            elif confirmmsg.content.lower() == 'n':
                await user.send('Successfully denied invitation')
                return await ctx.author.send(f'{user} has denied your invitation the todo list `{todo_list["name"]}`')

            elif confirmmsg.content.lower() == 'r':
                channel = self.client.get_channel(796306329756893184)

                await channel.send(f'Report: \nReported by {user} (id: {user.id})\nInvite author {ctx.author} (id: {ctx.author.id})\ntodo list name: {todo_list["name"]} (id: {todo_list["_id"]})')
                await user.send('User has been reported for harrasment/abuse of the invite command. Abuse of reporting may lead to blacklisting')
                await ctx.author.send(f'You have been reported for inviting {user}, a staff member will look into the issue soon')

    @custom_cooldown(5)
    @todo.command()
    async def assign(self, ctx, todo_number:int, user: typing.Union[discord.User, int], rm=None):
        #u todo assign <task_id> <user>
        #h Assign someone a todo task with this to coordinate who does what (Only in editor mode)
        try:
            list_id = editing[ctx.author.id]
        except KeyError:
            return await ctx.send('You have to be in the editor mode to use this command! Use `k!todo edit <todo_list_id>`')

        todo_list = todo.find_one({'_id': list_id})

        if isinstance(user, int):
            try:
                user = self.client.fetch_user(user)
            except:
                return await ctx.send('Invalid user id')

        if not user.id == todo_list['owner'] and not user.id in todo_list['editor']:
            return await ctx.send('You can only assign people todos who have permission to edit this todo list')

        todos = todo_list['todos']

        try:
            if todo_number == 0:
                raise 'Error!'
                #Error!!!!
            t = todos[todo_number-1]
        except Exception as e:
            return await ctx.send(f'You don\'t have a number {todo_number} on your current todo list')
        if rm:
            if rm.lower() == '-rm' or rm.lower() == '-r':
                if not user.id in todos[todo_number-1]['assigned_to']:
                    return await ctx.send('The user is not assigned to this todo task so you can\'t remove them')
                if not ctx.author == user:
                    embed = discord.Embed.from_dict({
                    'title': f'Removed assignment to todo on list {todo_list["name"]} (ID: {todo_list["_id"]})',
                    'description': f'{ctx.author} removed assignment you to the todo {todos[todo_number-1]["todo"]}',
                    'color': 0x1400ff,
                    'footer': {'icon_url': str(ctx.author.avatar_url), 'text': f'Requested by {ctx.author}'}
                    })
                    try:
                        await user.send(embed=embed)
                    except:
                        pass
                todos[todo_number-1]['assigned_to'].remove(user.id)
                todo.update_one({'_id': list_id}, {'$set':{'todos': todos}})
                return await ctx.send(f'Succesfully removed assignment of todo task {todo_number} to {user}')
            else:
                await ctx.send('Invalid argument for `rm`. Command usage: `k!todo assign <todo_number> <user> <optional_rm>` where -rm would remove them from that task')

        if user in todos[todo_number-1]['assigned_to']:
            return await ctx.send('The user specified is already assigned to that todo task')

        todos[todo_number-1]['assigned_to'].append(user.id)

        todo.update_one({'_id': list_id}, {'$set':{'todos': todos}})

        if not ctx.author == user:
            embed = discord.Embed.from_dict({
                'title': f'Assigned to todo on list {todo_list["name"]} (ID: {todo_list["_id"]})',
                'description': f'{ctx.author} iassigned you to the todo {todos[todo_number-1]["todo"]}',
                'color': 0x1400ff,
                'footer': {'icon_url': str(ctx.author.avatar_url), 'text': f'Requested by {ctx.author}'}
            })
            try:
                await user.send(embed=embed)
            except:
                pass
        return await ctx.send(f'Succesfully assigned the task with number {todo_number} to `{user}`')
        
    @custom_cooldown(20)
    @todo.command()
    async def delete(self, ctx, todo_id):
        #u todo delete <todo_id>
        #h Use this command to delete your todo list. Make sure to say goodbye a last time
        if todo_id.isdigit():
            todo_id = int(todo_id)
            todo_list = todo.find_one({'_id': todo_id})
        else:
            todo_list = todo.find_one({'custom_id': todo_id})

        if todo_list is None:
            return await ctx.send('A list with this id does not exist')
        if not ctx.author.id == todo_list['owner']:
            return await ctx.send('Only the owner of a todo list can delete it')

        todo.delete_one({'_id': todo_id})
        return await ctx.send(f'Done! Deleted todo list {todo_list["name"]}')

    @custom_cooldown(4)
    @todo.command()
    async def lists(self, ctx):
        #u todo lists
        #h This shows a liat of todo lists you own or have access to
        lists_owning = todo.find({'owner': ctx.author.id})
        lists_viewing = todo.find({'viewer': ctx.author.id})
        lists_editing = todo.find({'editor': ctx.author.id})
        l_o = []
        l_v = []
        l_e = []

        for l in lists_owning:
            l_o.append(f'{l["name"]} (id: {l["_id"]}/{l["custom_id"] or "No custom id"})')

        for l in lists_viewing:
            l_v.append(f'{l["name"]} (id: {l["_id"]}/{l["custom_id"] or "No custom id"})')

        for l in lists_editing:
            l_e.append(f'{l["name"]} (id: {l["_id"]}/{l["custom_id"] or "No custom id"})')

        l_o = '\n'.join(l_o)
        l_v = '\n'.join(l_v)
        l_e = '\n'.join(l_e)

        embed = discord.Embed.from_dict({
            'title': f'Your todo lists and permissions',
            'description': f'__`todo lists you own`__\n{l_o or "No todo lists"}\n__`todo lists you have viewing permissions`__\n{l_v or "No todo lists"}\n__`todo lists you have editing permissions`__\n{l_e or "No todo lists"}',
            'color': 0x1400ff,
            'footer': {'icon_url': str(ctx.author.avatar_url), 'text': f'Requested by {ctx.author}'}
        })
        return await ctx.send(embed=embed)

'''async function todo_name
Input:
self: inputting because function is outside of cog
ctx: to have somthing to use .send() on

Returns:
title: title of the todo list

Purpose: 
outsourcing todo create in smaller functions
'''

async def todo_name(self, ctx):
    embed = discord.Embed.from_dict({
        'title': f'Creating of a todo list',
        'description': f'Please start by choosing a title for your todo list',
        'color': 0x1400ff,
        'footer': {'icon_url': str(ctx.author.avatar_url), 'text': f'Requested by {ctx.author}'}
    })
    step = await ctx.send(embed=embed)

    def check(m):
        return m.author.id == ctx.author.id

    try:
        confirmmsg = await self.client.wait_for('message', check=check, timeout=60)
    except asyncio.TimeoutError:
        await step.delete
        await ctx.send('Too late...', delete_after=5)
        return None
    else:
        title = confirmmsg.content
            
        await step.delete()
        try:
            await confirmmsg.delete()
        except:
            pass
        if len(title) > 30:
            await ctx.send('Title can\'t be longer than 20 characters, please try again', delete_after=5)
            await asyncio.sleep(5)
            return await todo_name(self, ctx)
        return title

'''async function todo_status
Input:
self: inputting because function is outside of cog
ctx: to have somthing to use .send() on

Returns:
status: if the todo list is public/private

Purpose: 
outsourcing todo create in smaller functions
'''

async def todo_status(self, ctx):
    embed = discord.Embed.from_dict({
        'title': f'Creating of a todo list',
        'description': f'Please choose if this todo list will be `public` (everyone can see the list by ID) or `private` (Only you and people you invite can see this todo list) ',
        'color': 0x1400ff,
        'footer': {'icon_url': str(ctx.author.avatar_url), 'text': f'Requested by {ctx.author}'}
    })
    step = await ctx.send(embed=embed)
    def check(m):
        return m.content.lower() in ['private', 'public'] and m.author.id == ctx.author.id

    try:
        confirmmsg = await self.client.wait_for('message', check=check, timeout=60)
    except asyncio.TimeoutError:
        await step.delete()
        await ctx.send('Too late...', delete_after=5)
        return None
    else:
        status = confirmmsg.content.lower()

        try:
            await confirmmsg.delete()
        except:
            pass
        await step.delete()
        return status

'''async function todo_done_delete
Input:
self: inputting because function is outside of cog
ctx: to have somthing to use .send() on

Returns:
(boolean): If todos should be deleted when they are marketr as done

Purpose: 
outsourcing todo create in smaller functions
'''

async def todo_done_delete(self, ctx):
    embed = discord.Embed.from_dict({
        'title': f'Creating of a todo list',
        'description': f'Should todo tasks marked as "done" be automatically deleted? **[y/n]**',
        'color': 0x1400ff,
        'footer': {'icon_url': str(ctx.author.avatar_url), 'text': f'Requested by {ctx.author}'}
    })
    step = await ctx.send(embed=embed)
    def check(m):
        return m.content.lower() in ['y', 'n'] and m.author.id == ctx.author.id

    try:
        confirmmsg = await self.client.wait_for('message', check=check, timeout=60)
    except asyncio.TimeoutError:
        await step.delete()
        await ctx.send('Too late...', delete_after=5)
        return None
    else:
        try:
            await confirmmsg.delete()
        except:
            pass
        await step.delete()
        if confirmmsg.content.lower() == 'y':
            return True
        elif confirmmsg.content.lower() == 'n':
            return False

'''async function todo_custom_id
Input:
self: inputting because function is outside of cog
ctx: to have somthing to use .send() on

Returns:
(boolean): if the todo list has been assigned to a custom status

Purpose: 
outsourcing todo create in smaller functions
'''

async def todo_custom_id(self, ctx, todo_id, title:str, status:str, done_delete:bool):
    embed = discord.Embed.from_dict({
        'title': f'Creating of a todo list',
        'description': f'Since you are a premium supporter you have the option to use a custom to-do id which can also be a string (f.e. Killua). You can still use to id to go into the todo list. If you want a custom id, enter it now, if you don\'t then enter **n**',
        'color': 0x1400ff,
        'footer': {'icon_url': str(ctx.author.avatar_url), 'text': f'Requested by {ctx.author}'}
    })
    step = await ctx.send(embed=embed)

    def check(m):
        return m.author.id == ctx.author.id

    try:
        confirmmsg = await self.client.wait_for('message', check=check, timeout=60)
    except asyncio.TimeoutError:
        await step.delete()
        return await ctx.send('Too late, canceling...', delete_after=5)
    else:
        if confirmmsg.content.lower() == 'n':
            return False
        else:
            if len(confirmmsg.content) > 20:
                await ctx.send('Your custom id can have max 20 characters')
                return await todo_custom_id(self, ctx, todo_id, title, status, done_delete)
            todo.insert_one({'_id': todo_id, 'name': title, 'owner': ctx.author.id, 'custom_id': confirmmsg.content.lower(),'status': status, 'delete_done': done_delete, 'viewer': [], 'editor': [], 'todos': [{'todo': 'add todos', 'marked': None, 'added_by': 756206646396452975, 'added_on': (datetime.now()).strftime("%b %d %Y %H:%M:%S"), 'views': 0, 'assigned_to': [], 'mark_log': []}], 'created_at': (datetime.now()).strftime("%b %d %Y %H:%M:%S"), 'spots': 10, 'views': 0})
            await ctx.send(f'Created the todo list with the name {title}. You can look at it and edit it through the id `{todo_id}` or your custom id `{confirmmsg.content}`')
            return True

'''async function buy_color
Input:
self: inputting because function is outside of cog
ctx: to have somthing to use .send() on

Returns:
(discord.Message)/itself: Either a confirm message or itself if something was invalid

Purpose: 
outsourcing todo buy in smaller functions
'''

async def buy_color(self, ctx):
    list_id = editing[ctx.author.id]
    todo_list = todo.find_one({'_id': list_id})
    user = teams.find_one({'id': ctx.author.id})
    if user['points'] < 1000:
        return await ctx.send('You don\'t have enough Jenny to buy a color for your todo list. You need 1000 Jenny')
    try:
        color = todo_list['color']
        return await ctx.send('You already have bought a color for this list! Update it with `k!todo color <color>`')
    except KeyError:
        pass
    
    step = await ctx.send('Please provide a color you want your todo list to have, you can always change it later')
    def check(m):
        return m.author.id == ctx.author.id
    try:
        confirmmsg = await self.client.wait_for('message', check=check, timeout=60)
    except asyncio.TimeoutError:
        await step.delete()
        return await ctx.send('Too late, canceling...', delete_after=5)
    else:
        await step.delete()
        try:
            await confirmmsg.delete()
        except:
            pass
        c = f'0x{confirmmsg.content}'
        try:
            if not int(c, 16) <= 16777215:
                await ctx.send('You need to provide a valid color! (Default color is 1400ff f.e.)')
                return await buy_color(self, ctx)
        except:
            await ctx.send('You need to provide a valid color! (Default color is 1400ff f.e.)')
            return await buy_color(self, ctx)

        todo.update_one({'_id': list_id},{'$set':{'color':int(c, 16)}})
        teams.update_one({'id': ctx.author.id}, {'$set':{'points': user['points']-1000}})
        return await ctx.send(f'Successfully bought the color {confirmmsg.content} for your list! You can change it with `k!todo color <url>`')

'''async function buy_thumbnail
Input:
self: inputting because function is outside of cog
ctx: to have somthing to use .send() on

Returns:
(discord.Message)/itself: Either a confirm message or itself if something was invalid

Purpose: 
outsourcing todo buy in smaller functions
'''

async def buy_thumbnail(self, ctx):
    list_id = editing[ctx.author.id]
    todo_list = todo.find_one({'_id': list_id})
    user = teams.find_one({'id': ctx.author.id})
    if user['points'] < 1000:
        return await ctx.send('You don\'t have enough Jenny to buy a thumbnail for your todo list. You need 1000 Jenny')
    try:
        thumbnail = todo_list['thumbnail']
        return await ctx.send('You already have bought a thumbnail for this list! Update it with `k!todo thumbnail <thumbnail_url>`')
    except KeyError:
        pass
    
    step = await ctx.send('Please provide a thumbnail you want your todo list to have, you can always change it later')
    def check(m):
        return m.author.id == ctx.author.id
    try:
        confirmmsg = await self.client.wait_for('message', check=check, timeout=60)
    except asyncio.TimeoutError:
        await step.delete()
        return await ctx.send('Too late, canceling...', delete_after=5)
    else:
        await step.delete()
        try:
            await confirmmsg.delete()
        except:
            pass
        url = re.search(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))', confirmmsg.content)

        if url:
            image = re.search(r'png|jpg|gif|svg', confirmmsg.content)
        else:
            await ctx.send('You didn\'t provide a valid url with an image! Please make sure you do that')
            return await buy_thumbnail(self, ctx)
            
        if image:
            todo.update_one({'_id': list_id},{'$set':{'thumbnail': confirmmsg.content}})
            teams.update_one({'id': ctx.author.id}, {'$set':{'points': user['points']-1000}})
            return await ctx.send(f'Successfully bought the thumbmail `{confirmmsg.content}` for your list! You can change it with `k!todo thumbnail <url>`')
        else:
            await ctx.send('You didn\'t provide a valid url with an image! Please make sure you do that')
            return await buy_thumbnail(self, ctx)

'''async function buy_space
Input:
self: inputting because function is outside of cog
ctx: to have somthing to use .send() on

Returns:
(discord.Message): Confirm message

Purpose: 
outsourcing todo buy in smaller functions
'''

async def buy_space(self, ctx):
    # This is the best thing to buy from your Jenny
    list_id = editing[ctx.author.id]
    todo_list = todo.find_one({'_id': list_id})
    user = teams.find_one({'id': ctx.author.id})

    if user['points'] < (todo_list['spots'] * 100):
        return await ctx.send(f'You don\'t have enough Jenny to buy more space for your todo list. You need {todo_list["spots"]*100} Jenny')

    if todo_list['spots'] >= 100:
        return await ctx.send('You can\'t buy more than 100 spots')

    step = await ctx.send(f'Do you want to buy 10 more to-do spots for this list? Current spots: {todo_list["spots"]} Cost: {todo_list["spots"]*100} points \n**[y/n]**')
    def check(m):
        return m.content.lower() in ['y', 'n'] and m.author.id == ctx.author.id
    try:
        confirmmsg = await self.client.wait_for('message', check=check, timeout=60)
    except asyncio.TimeoutError:
        await step.delete()
        return await ctx.send('Too late, canceling...', delete_after=5)
    else:
        if confirmmsg.content.lower() == 'n':
            return await ctx.send('Alright, see you later then :3')
        await step.delete()
        try:
            await confirmmsg.delete()
        except:
            pass
        teams.update_one({'id': ctx.author.id}, {'$set':{'points': user['points']- todo_list['spots']*100}})
        todo.update_one({'_id': list_id}, {'$set':{'spots': todo_list['spots']+10 }})
        return await ctx.send('Congrats! You just bought 10 more todo spots for the current todo list!')

'''async function buy_description
Input:
self: inputting because function is outside of cog
ctx: to have somthing to use .send() on

Returns:
(discord.Message)/itself: Either a confirm message or itself if something was invalid

Purpose: 
outsourcing todo buy in smaller functions
'''

async def buy_description(self, ctx):
    #Hi! You found a random comment! Now you have to vote for Killua :3 (Also thanks for checking out my code)
    list_id = editing[ctx.author.id]
    todo_list = todo.find_one({'_id': list_id})
    user = teams.find_one({'id': ctx.author.id})
    if user['points'] < 1000:
        return await ctx.send('You don\'t have enough Jenny to buy a thumbnail for your todo list. You need 1000 Jenny')
    
    step = await ctx.send(f'What should the description of your todo list be? (max 200 characters)')
    def check(m):
        return m.author.id == ctx.author.id
    try:
        confirmmsg = await self.client.wait_for('message', check=check, timeout=60)
    except asyncio.TimeoutError:
        await step.delete()
        return await ctx.send('Too late, canceling...', delete_after=5)
    else:
        await step.delete()
        try:
            await confirmmsg.delete()
        except:
            pass
        if len(confirmmsg.content) > 200:
            await ctx.send('Your description can\'t be over 200 characters!')
            return await buy_description(self, ctx)
        teams.update_one({'id': ctx.author.id}, {'$set': {'points': user['points']-1000}})
        todo.update_one({'_id': list_id}, {'$set':{'description': confirmmsg.content}})
        return await ctx.send('Congrats! You bought a description for your current todo list')

'''async function todo_embed_generator
Input:
self: inputting because function is outside of cog
ctx: to have somthing to use .send() on
todo_id: the todo list's id

Returns
embed: An embed with todo tasks of a todo list

Purpose: 
outsourcing making of big embed
'''

async def todo_embed_generator(self, ctx, todo_id):
    if str(todo_id).isdigit():
        todo_id = int(todo_id)
        todo_list = todo.find_one({'_id': todo_id})
    else:
        todo_list = todo.find_one({'custom_id': todo_id.lower()})

    owner = todo_list['owner']
    owner = await self.client.fetch_user(owner)

    l = todo_list['todos']
    new_l = []
    for thing in enumerate(l):
        n, t = thing
        if t['marked']:
            ma = f'\n`Marked as {t["marked"]}`'
        else:
            ma = ''
        if len(t['assigned_to']) == 0:
            at = ''
        else:
            at = []
            for user in t['assigned_to']:
                person = await self.client.fetch_user(user)
                at.append(f'{person.name}#{person.discriminator}')
            at = f'\n`Assigned to: {", ".join(at)}`'
        new_l.append(f'{n+1}) {t["todo"]}{ma}{at}')
    new_l = '\n'.join(new_l)
    embed = discord.Embed.from_dict({
        'title': f'To-do list "{todo_list["name"]}" (ID: {todo_list["_id"]})',
        'description': f'{new_l if len(new_l) > 1 else "No todos"}',
        'color': 0x1400ff,
        'footer': {'icon_url': str(owner.avatar_url), 'text': f'Owned by {owner}'}
    })

    try:
        thumbnail = todo_list['thumbnail']
        embed.set_thumbnail(url=thumbnail)
    except KeyError:
        pass
    try:
        embed.color = todo_list['color']
    except KeyError:
        pass
    return embed

'''async function todo_info_embed_generator
Input:
self: inputting because function is outside of cog
ctx: to have somthing to use .send() on
list_id (string): the todo list's id

Returns:
embed: An embed with infos about a todo list

Purpose: 
outsourcing big embed production 🛠
'''

async def todo_info_embed_generator(self, ctx, list_id:str):
    editors = list()
    viewer = list()
    if str(list_id).isdigit():
        list_id = int(list_id)
        todo_list = todo.find_one({'_id': list_id})
    else:
        todo_list = todo.find_one({'custom_id': list_id.lower()})

    if todo_list is None:
        return await ctx.send('No todo list with the id specified found')

    if todo_list['status'] == 'private' and not ctx.author.id == todo_list['owner'] or ctx.author.id in ['viewer'] or ctx.author.id in todo_list['editor']:
        return await ctx.send('You don\'t have permission to view infos about this list!')
    
    if not ctx.author.id == todo_list['owner'] and not ctx.author.id in todo_list['viewer'] and ctx.author.id in todo_list['editor']:
        todo.update_one({'_id': todo_id}, {'$set':{'views': todo_list['views']+1 }})

    if todo_list['viewer'] == []:
        todo_list['viewer'] = ['No one with viewing permissions']
    else:
        print(todo_list['viewer'])
        for user in todo_list['viewer']:
            u = await self.client.fetch_user(user)
            viewer.append(f'{u.name}#{u.discriminator}')
        print(viewer)
    if todo_list['editor'] == []:
        todo_list['editor'] = ['No one with editing permissions']
    else:
        for user in todo_list['editor']:
            u = await self.client.fetch_user(user)
            editors.append(f'{u.name}#{u.discriminator}')
    try:
        description = todo_list['description']
    except KeyError:
        description = ''
    owner = await self.client.fetch_user(todo_list['owner'])
    if not 'description' in todo_list:
        todo_list['description'] = ''
    
    embed = discord.Embed.from_dict({
        'title': f'Information for the todo list "{todo_list["name"]}" (ID: {todo_list["_id"]})',
        'description': f'''{description}
**Owner**: `{owner}`

**Custom ID**: `{todo_list["custom_id"] or "No custom id"}`

**Status**: `{todo_list["status"]}`

**Editors**: `{", ".join(editors) if len(editors) > 0 else "Nobody has editor perissions"}`

**Viewers**: `{", ".join(viewer) if len(viewer) > 0 else "Nobody has viewer permissions"}`

**Todos**: `{len(todo_list["todos"])}/{todo_list["spots"]}`

**Created on:** `{todo_list["created_at"]}`

*{todo_list["views"]} views*
''',
        'color': 0x1400ff,
    })
    if 'thumbnail' in todo_list:
        embed.set_thumbnail(url=todo_list['thumbnail'])
    if 'color' in todo_list:
        embed.color = todo_list['color']
    return await ctx.send(embed=embed)

'''async function single_todo_info_embed_generator
Input:
self: inputting because function is outside of cog
ctx: to have somthing to use .send() on
todo_id (integer): the number of the todo task
list_id: the id of the list the todo is from

Returns:
embed: An embed with infos about a todo task

Purpose: 
outsourcing big embed production 🛠
'''

async def single_todo_info_embed_generator(self, ctx, todo_id:int, list_id):
    if str(list_id).isdigit():
        list_id = int(list_id)
        todo_list = todo.find_one({'_id': list_id})
    else:
        todo_list = todo.find_one({'custom_id': list_id.lower()})
    if todo_list is None:
        return await ctx.send('No todo list with the specified id found')
    td = todo_list['todos']
    if todo_list['status'] == 'private':
        if not todo_list['owner'] == ctx.author.id and not ctx.author.id in todo_list['viewer'] and ctx.author.id not in todo_list['editor']:
            return await ctx.send('You don\'t have the permissiont to view this todo task')
    if todo_id == 0:
        return await ctx.send('You have no todo number 0 on your list..') 
    todo_infos = td[todo_id-1]

    addist = await self.client.fetch_user(todo_infos['added_by'])
    addist = f'{addist.name}#{addist.discriminator}'

    assigned_to = todo_infos['assigned_to']
    assignees = len(assigned_to)
    people = []
    if assignees == 0:
        people = ['unnassigned']
    else:
        for user in assigned_to:
            assignist = await self.client.fetch_user(user)
            people.append(f'{assignist.name}#{assignist.discriminator}')
    changes = len(todo_infos['mark_log'])
    mark_log = []
    if changes > 3:
        x = changes
        while x != changes-3:
            changist = await self.client.fetch_user(todo_infos['mark_log'][x-1]['author'])
            mark_log.append(f'Changed to: `{todo_infos["mark_log"][x-1]["change"]}`\nBy `{changist.name}#{changist.discriminator}`\nOn `{todo_infos["mark_log"][x-1]["date"]}`')
            x = x-1
    elif changes == 0:
        mark_log = ['todo not marked yet']
    else:
        for mark in todo_infos['mark_log']:
            changist = await self.client.fetch_user(mark['author'])
            mark_log.append(f'Changed to: `{mark["change"]}`\nBy `{changist.name}#{changist.discriminator}`\nOn `{mark["date"]}`')

    mark_log = ' \n'.join(mark_log)

    embed = discord.Embed.from_dict({
        'title': f'Information for the todo task {todo_id}',
        'description': f'''**Added by**: `{addist}`
    
**Content**: {todo_infos["todo"]}
        
**Currently marked as**: `{todo_infos["marked"] or "Not currently marked"}`

**Assigned to**: `{", ".join(people)}`

**Added on:** `{todo_infos["added_on"]}`

**Latest changes marks**:
    {mark_log}

*{todo_list["views"]} views*
''',
        'color': 0x1400ff,
    })
    if 'thumbnail' in todo_list:
        embed.set_thumbnail(url=todo_list['thumbnail'])
    if 'color' in todo_list:
        embed.color = todo_list['color']
    return await ctx.send(embed=embed)


'''async function todo_menu_embed_generator
Input:
self: inputting because function is outside of cog
ctx: to have somthing to use .send() on
todo_id: the todo list's id
page (integer): the page the user is on
msg: the current page's message

Returns:
itself/nothing: if it times out it returns nothing, else it allows you to go through the pages further

Purpose: 
outsourcing big embed production 🛠, also to not have a giant embed with todos on a list, so this is called
when there are more than 10 todos on the list
'''


async def todo_menu_embed_generator(self, ctx, todo_id, page:int, msg=None):
    if str(todo_id).isdigit():
        todo_id = int(todo_id)
        todo_list = todo.find_one({'_id': todo_id})
    else:
        todo_list = todo.find_one({'custom_id': todo_id.lower()})

    owner = todo_list['owner']
    owner = await self.client.fetch_user(owner)

    l = todo_list['todos']
    max_pages = math.ceil(len(l)/10)
    final_todos = []
    new_l = []

    if len(l)-page*10+10 > 10:
        final_todos = l[page*10-10:-(len(l)-page*10)]
    elif len(l)-page*10+10 <= 10:
        final_todos = l[-(len(l)-page*10+10):]

    for thing in enumerate(final_todos, page*10-10):
        n, t = thing
        if t['marked']:
            ma = f'\n`Marked as {t["marked"]}`'
        else:
            ma = ''
        if len(t['assigned_to']) == 0:
            at = ''
        else:
            at = []
            for user in t['assigned_to']:
                person = await self.client.fetch_user(user)
                at.append(f'{person.name}#{person.discriminator}')
            at = f'\n`Assigned to: {", ".join(at)}`'
        new_l.append(f'{n+1}) {t["todo"]}{ma}{at}')
    new_l = '\n'.join(new_l)
    embed = discord.Embed.from_dict({
        'title': f'To-do list "{todo_list["name"]}" (ID: {todo_list["_id"]})',
        'description': f'*Page {page}/{max_pages}*\n{new_l}',
        'color': 0x1400ff,
        'footer': {'icon_url': str(owner.avatar_url), 'text': f'Owned by {owner}'}
    })

    try:
        thumbnail = todo_list['thumbnail']
        embed.set_thumbnail(url=thumbnail)
    except KeyError:
        pass
    try:
        embed.color = todo_list['color']
    except KeyError:
        pass
    if msg:
        await msg.edit(embed=embed)
    else:
        msg = await ctx.send(embed=embed)
        await msg.add_reaction('\U000025c0')
        await msg.add_reaction('\U000025b6')

    def check(reaction, user):
        return user == ctx.author and reaction.message.id == msg.id and user != ctx.me and(reaction.emoji == '\U000025b6' or reaction.emoji == '\U000025c0')
    try:
        reaction, user = await self.client.wait_for('reaction_add', timeout=120, check=check)
    except asyncio.TimeoutError:
        await msg.remove_reaction('\U000025c0', ctx.me)
        await msg.remove_reaction('\U000025b6', ctx.me)
        return
    else:
        if reaction.emoji == '\U000025b6':
            if page == max_pages: 
                page = 0
            try:
                await msg.remove_reaction('\U000025b6', ctx.author)
            except:
                pass
            return await todo_menu_embed_generator(self, ctx, todo_id, page+1, msg)

        if reaction.emoji == '\U000025c0':
            if page == 1:
                page = max_pages+1
            try:
                await msg.remove_reaction('\U000025c0', ctx.author)
            except:
                pass
            return await todo_menu_embed_generator(self, ctx, todo_id, page-1, msg)  

Cog = TodoSystem     

'''function generate_id
Input:
nothing

Returns:
(string): The fresh crafted todo id

Purpose: 
Creating a random id, checking if it exists and if it doesn't, return it, if it does, just make a new one!
'''

def generate_id():
    l = []
    while len(l) != 6:
        l.append(str(randint(0,9)))

    todo_id = todo.find_one({'_id': ''.join(l)})

    if todo_id is None:
        return ''.join(l)
    else:
        return generate_id()

        
def setup(client):
    client.add_cog(TodoSystem(client))
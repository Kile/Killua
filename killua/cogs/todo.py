import discord
from discord.ext import commands
import asyncio
from datetime import datetime
import re
import math
from typing import Union

from killua.static.constants import todo, editing, REPORT_CHANNEL
from killua.utils.checks import check, blcheck
from killua.utils.classes import TodoList, Todo, User, TodoListNotFound, Category, ConfirmButton, Button
from killua.utils.paginator import Paginator

class TodoSystem(commands.Cog):

    def __init__(self,client):
        self.client = client

    async def _get_user(self, u:int) -> discord.User:
        """Gets a user from cache if possible, else makes an API request"""
        r = self.client.get_user(u)
        if not r:
            r = await self.client.fetch_user(u)
        return r

    def _get_color(self, l:TodoList):
        """A shortcut to get the correct embed color for a todo list"""
        return l.color if l.color else 0x1400ff

    async def _wait_for_response(self, step, check) -> Union[discord.Message, None]:
        """Waits for a response and returns the response message"""
        try:
            confirmmsg = await self.client.wait_for('message', check=check, timeout=60)
        except asyncio.TimeoutError:
            await step.delete()
            await step.channel.send('Too late...', delete_after=5)
            return None
        else:
            await step.delete()
            try:
                await confirmmsg.delete()
            except discord.HTTPException:
                pass
            return confirmmsg

    async def _build_embed(self, todo_list:TodoList, page:int=None) -> discord.Embed:
        """Creates an embed for a todo list page"""
        owner = await self._get_user(todo_list.owner)
        l = todo_list.todos
        desc = []

        if len(todo_list) > 10 and page:
            max_pages = math.ceil(len(l)/10)
            final_todos = []

            if len(l)-page*10+10 > 10:
                final_todos = l[page*10-10:-(len(l)-page*10)]
            elif len(l)-page*10+10 <= 10:
                final_todos = l[-(len(l)-page*10+10):]

        async def assigned_users(td: Todo) -> str:
            at = []
            for user in t.assigned_to:
                person = await self._get_user(user)
                at.append(person)
            return f'\n`Assigned to: {", ".join([str(x) for x in at])}`'

        for n, t in enumerate(final_todos if page else l, page*10-10 if page else 0):
            t = Todo(n+1, todo_list.id)
            ma = f'\n`Marked as {t.marked}`' if t.marked else ''
            desc.append(f'{n+1}) {t.todo}{ma}{await assigned_users(t) if len(t.assigned_to) > 0 else ""}')
        desc = '\n'.join(desc) if len(desc) > 0 else "No todos"


        embed = discord.Embed.from_dict({
            'title': f'To-do list "{todo_list.name}" (ID: {todo_list.id})',
            'description': f'{f"*Page {page}/{max_pages}*" if page else ""}\n{desc}',
            'color': self._get_color(todo_list),
            'footer': {'icon_url': str(owner.avatar.url), 'text': f'Owned by {owner}'}
        })

        if todo_list.thumbnail:
            embed.set_thumbnail(url=todo_list.thumbnail)

        return embed


    async def todo_name(self, ctx):
        """outsourcing todo create in smaller functions. Will be rewritten once discord adds text input interaction"""
        embed = discord.Embed.from_dict({
            'title': f'Editing settings',
            'description': f'Please start choose a title for your todo list',
            'color': 0x1400ff,
            'footer': {'icon_url': str(ctx.author.avatar.url), 'text': f'Requested by {ctx.author}'}
        })
        step = await ctx.send(embed=embed)

        def check(m):
            return m.author.id == ctx.author.id

        confirmmsg = await self._wait_for_response(step, check)

        if not confirmmsg:
            return None
        title = confirmmsg.content

        if len(title) > 30:
            await ctx.send('Title can\'t be longer than 20 characters, please try again', delete_after=5)
            await asyncio.sleep(5)
            return await self.todo_name(ctx)
        return title

    async def todo_status(self, ctx):
        """outsourcing todo create in smaller functions. Will be rewritten once discord adds text input interaction"""
        embed = discord.Embed.from_dict({
            'title': f'Editing settings',
            'description': f'Please choose if this todo list will be `public` (everyone can see the list by ID) or `private` (Only you and people you invite can see this todo list) ',
            'color': 0x1400ff,
            'footer': {'icon_url': str(ctx.author.avatar.url), 'text': f'Requested by {ctx.author}'}
        })
        step = await ctx.send(embed=embed)
        def check(m):
            return m.content.lower() in ['private', 'public'] and m.author.id == ctx.author.id

        confirmmsg = await self._wait_for_response(step, check)
        if not confirmmsg:
            return None
        return confirmmsg.content.lower()

    async def todo_done_delete(self, ctx):
        """outsourcing todo create in smaller functions"""
        embed = discord.Embed.from_dict({
            'title': f'Editing settings',
            'description': f'Should todo tasks marked as "done" be automatically deleted?',
            'color': 0x1400ff,
            'footer': {'icon_url': str(ctx.author.avatar.url), 'text': f'Requested by {ctx.author}'}
        })

        view = ConfirmButton(ctx.author.id, timeout=80)
        msg = await ctx.send(embed=embed, view=view)
        await view.wait()
        await view.disable(msg)

        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass
        await msg.delete()

        if not view.value:
            if view.timed_out:
                return None
            else:
                return False

        return True

    async def todo_custom_id(self, ctx):
        """outsourcing todo create in smaller functions. Will be rewritten once discord adds text input interaction"""
        embed = discord.Embed.from_dict({
            'title': f'Editing settings',
            'description': f'Since you are a premium supporter you have the option to use a custom to-do id which can also be a string (f.e. Killua). You can still use to id to go into the todo list. If you want a custom id, enter it now, if you don\'t then enter **n**',
            'color': 0x1400ff,
            'footer': {'icon_url': str(ctx.author.avatar.url), 'text': f'Requested by {ctx.author}'}
        })
        step = await ctx.send(embed=embed)

        def check(m):
            return m.author.id == ctx.author.id
        confirmmsg = await self._wait_for_response(step, check)
        if not confirmmsg:
            return False

        if confirmmsg.content.lower() == 'n':
            return None
        
        if len(confirmmsg.content) > 20:
            await ctx.send('Your custom id can have max 20 characters')
            return await self.todo_custom_id(ctx)

        if confirmmsg.content.lower().isdigit():
            await ctx.send("Your custom id needs to contain at least one character that isn't an integer", delete_after=5)
            return await self.todo_custom_id(ctx)

        try:
            TodoList(confirmmsg.content.lower())
        except TodoListNotFound:
            return confirmmsg.content.lower()
        else:
            await ctx.send('This custom id is already taken', delete_after=5)
            return await self.todo_custom_id(ctx)

    async def todo_info_embed_generator(self, ctx, list_id):
        """outsourcing big embed production 🛠 """
        try:
            todo_list = TodoList(list_id)
        except TodoListNotFound:
            return await ctx.send('No todo list with this id exists')
        if not todo_list.has_view_permission(ctx.author.id):
            return await ctx.send('You don\'t have permission to view infos about this list!')
        todo_list.add_view(ctx.author.id)

        owner = await self._get_user(todo_list.owner)
        
        embed = discord.Embed.from_dict({
            'title': f'Information for the todo list "{todo_list.name}" (ID: {todo_list.id})',
            'description': f'''{todo_list.description if todo_list.description else ""}
    **Owner**: `{owner}`\n
    **Custom ID**: `{todo_list.custom_id or "No custom id"}`\n
    **Status**: `{todo_list.status}`\n
    **Editors**: `{", ".join([str(await self._get_user(u)) for u in todo_list.editor]) if len(todo_list.editor) > 0 else "Nobody has editor perissions"}`\n
    **Viewers**: `{", ".join([str(await self._get_user(u)) for u in todo_list.viewer]) if len(todo_list.viewer) > 0 else "Nobody has viewer permissions"}`\n
    **Todo's**: `{len(todo_list)}/{todo_list.spots}`\n
    **Created on:** `{todo_list.created_at}`\n
    *{todo_list.views} views*
    ''',
            'color': self._get_color(todo_list),
        })
        if todo_list.thumbnail:
            embed.set_thumbnail(url=todo_list.thumbnail)

        return await self.client.send_message(ctx, embed=embed)

    async def single_todo_info_embed_generator(self, ctx, list_id, task_id):
        """outsourcing big embed production 🛠"""
        try:
            todo_list = TodoList(list_id)
        except TodoListNotFound:
            return await ctx.send('No todo list with this id exists')
        try:
            todo_task = Todo(task_id, list_id)
        except Exception:
            return await ctx.send('A todo task with that id is not on the list')
        
        if not todo_list.has_view_permission(ctx.author.id):
            return await ctx.send('You don\'t have permission to view infos about this list!')

        addist = await self._get_user(todo_task.added_by)

        mark_log = '\n'.join([f"""Changed to: `{x['change']}`
        By `{await self.__get_user(x['author'])}`
        On `{x['date']}`""" for x in todo_task.mark_log[3:]])

        embed = discord.Embed.from_dict({
            'title': f'Information for the todo task {task_id}',
            'description': f'''**Added by**: `{addist}`\n
    **Content**: {todo_task.todo}\n
    **Currently marked as**: `{todo_task.marked or "Not currently marked"}`\n
    **Assigned to**: `{", ".join([str(await self._get_user(u)) for u in todo_task.assigned_to]) if len(todo_task.assigned_to) > 0 else "unassigned"}`\n
    **Added on:** `{todo_task.added_on}`\n
    **Latest changes marks**:
    {mark_log}\n
    *{todo_list.views} views*
    ''',
            'color': self._get_color(todo_list),
        })
        if todo_list.thumbnail:
            embed.set_thumbnail(url=todo_list.thumbnail)
        return await self.client.send_message(ctx, embed=embed)

    async def _set_check(self, ctx:commands.Context) -> Union[None, TodoList]:
        """A generic check before every command that edits a todo list property"""
        try:
            list_id = editing[ctx.author.id]
        except KeyError:
            await ctx.send(f'You have to be in the editor mode to use this command! Use `{self.client.command_prefix(self.client, ctx.message)[2]}todo edit <todo_list_id>`', allowed_mentions=discord.AllowedMentions.none())
        else:
            todo_list = TodoList(list_id)

            if getattr(todo_list, ctx.command.name) is None:
                await ctx.send(f'You need to have bought this feature for your current todo list with `{self.client.command_prefix(self.client, ctx.message)[2]}todo buy {ctx.command.name}`', allowed_mentions=discord.AllowedMentions.none())

            return todo_list

    @commands.group(hidden=True, extras={"category":Category.TODO})
    async def todo(self, ctx):
        pass

    @check(10)
    @todo.command(extras={"category":Category.TODO}, usage="create")
    async def create(self, ctx):
        """Let's you create your todo list in an interactive menu"""
        
        user_todo_lists = [x for x in todo.find({'owner': ctx.author.id})]

        if len(user_todo_lists) == 5:
            return await ctx.send('You can currently not own more than 5 todo lists')

        title  = await self.todo_name(ctx)
        if title is None:
            return

        status = await self.todo_status(ctx)
        if status is None:
            return 

        done_delete = await self.todo_done_delete(ctx)
        if done_delete is None:
            return

        user = User(ctx.author.id)
        if user.is_premium:
            custom_id = await self.todo_custom_id(ctx)
            if custom_id is False:
                return
        else:
            custom_id = None
        
        l = TodoList.create(owner=ctx.author.id, title=title, status=status, done_delete=done_delete, custom_id=custom_id)
        await ctx.send(f'Created the todo list with the name {title}. You can look at it and edit it through the id `{l.id}`' + (f' or through your custom id {custom_id}' if custom_id else ''), allowed_mentions=discord.AllowedMentions.none())

    @check()
    @todo.command(extras={"category":Category.TODO}, usage="view <list_id(optional)>")
    async def view(self, ctx, todo_id:Union[int, str]=None):
        """Allows you to view what is on any todo list- provided you have the permissions"""
        if todo_id is None:
            try:
                todo_id = editing[ctx.author.id]
            except KeyError:
                return await ctx.send('You have to be in the editor mode to use this command without providing an id! Use `k!todo edit <todo_list_id>`')

        try:
            todo_list = TodoList(todo_id)
        except TodoListNotFound:
            return await ctx.send('No todo list with specified ID found')

        if not todo_list.has_view_permission(ctx.author.id):
            return await ctx.send('This is a private list you don\'t have the permission to view')
        todo_list.add_view(ctx.author.id)

        if len(todo_list) <= 10:
            return await ctx.send(embed=await self._build_embed(todo_list))

        async def make_embed(page, embed, pages):
            return await self._build_embed(pages, page)
        await Paginator(ctx, todo_list, max_pages=math.ceil(len(todo_list)/10),func=make_embed).start()

    @check()
    @todo.command(extras={"category":Category.TODO}, usage="clear")
    async def clear(self, ctx):
        """Clears all todos from a todo list"""
        try:
            list_id = editing[ctx.author.id]
        except KeyError:
            return await ctx.send('You have to be in the editor mode to use this command without providing an id! Use `k!todo edit <todo_list_id>`')

        todo_list = TodoList(list_id)
        if not todo_list.has_edit_permission(ctx.author.id):
            return await ctx.send("You have to be added as an editor to this list to use this command")
        todo_list.clear()
        await ctx.send("Done! Cleared all your todos")

    @check(1)
    @todo.command(extras={"category":Category.TODO}, usage="info <list_id/task_id> <task_id(if list_id provided)>")
    async def info(self, ctx, todo_or_task_id:Union[int, str]=None, td:int=None):
        """This gives you info about either a todo task or list"""
        if td is None:
            if todo_or_task_id is None:
                try:
                    list_id = editing[ctx.author.id]
                except KeyError:
                    return await ctx.send('You need to be in editor mode for a list or provide an id to use this command')
                return await self.todo_info_embed_generator(ctx, list_id)
            try:
                list_id = editing[ctx.author.id]
            except KeyError:
                return await self.todo_info_embed_generator(ctx, todo_or_task_id)
            return await self.single_todo_info_embed_generator(ctx, list_id, int(todo_or_task_id))
        elif td:
            return await self.single_todo_info_embed_generator(ctx, todo_or_task_id, int(td))

    @check()
    @todo.command(extras={"category":Category.TODO}, usage="edit <list_id>")
    async def edit(self, ctx, list_id: Union[int, str]):
        """The command with which you can change stuff on your todo list"""
        if ctx.author.id in editing and editing[ctx.author.id] == list_id:
            return await ctx.send("You are already editing this list!")
        try:
            todo_list = TodoList(list_id)
        except TodoListNotFound:
            return await ctx.send('No todo list with this id exists')

        if not todo_list.has_edit_permission(ctx.author.id):
            return await ctx.send('You do not have the permission to edit this todo list')
        await ctx.send(f'You are now in editor mode for todo list "{todo_list.name}"', allowed_mentions=discord.AllowedMentions.none())
        editing[ctx.author.id] = todo_list.id

    @check()
    @todo.command(extras={"category":Category.TODO}, usage="name <new_name>")
    async def name(self, ctx, *, new_name:str):
        """Rename your todo list with this command (Only in editor mode)"""
        res = await self._set_check(ctx)
        if not res:
            return

        if len(new_name) > 30:
            return await ctx.send("The name cannot be longer than 30 characters!")
        res.set_property("name", new_name)
        await ctx.send(f'Done! Update your todo list\'s name to "{new_name}"', allowed_mentions=discord.AllowedMentions.none())

    @check()
    @todo.command(extras={"category":Category.TODO}, usage="status <new_status>")
    async def status(self, ctx, status):
        """Change the status of your todo list (public/private) with this command (Only in editor mode)"""
        res = await self._set_check(ctx)
        if not res:
            return

        if not status.lower() in ['private', 'public']:
            return await ctx.send('You need to chose a valid status (private/public)')
        res.set_property("status", status.lower())
        await ctx.send(f'Done! Updated your todo list\'s status to `{status.lower()}`', allowed_mentions=discord.AllowedMentions.none())

    @check()
    @todo.command(extras={"category":Category.TODO}, usage="color <new_color_in_hex>")
    async def color(self, ctx, color):
        """Change your todo list's color with this command (Only in editor mode)"""
        res = await self._set_check(ctx)
        if not res:
            return
            
        c = f'0x{color}'
        try:
            if not int(c, 16) <= 16777215:
                await ctx.send('You need to provide a valid color! (Default color is 1400ff f.e.)')
        except Exception:
            await ctx.send('You need to provide a valid color! (Default color is 1400ff f.e.)')

        res.set_property("color", int(c, 16))
        await ctx.send(f'Done! Updated your todo list\'s color to `{c}`')

    @check()
    @todo.command(extras={"category":Category.TODO}, usage="thumbnail <new_thumbnail>")
    async def thumbnail(self, ctx, url):
        """Change your todo lists thumbnail with this command (Only in editor mode)"""
        res = await self._set_check(ctx)
        if not res:
            return

        search_url = re.search(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))', url)

        if search_url:
            image = re.search(r'png|jpg|gif|svg', url)
        else:
            await ctx.send('You didn\'t provide a valid url with an image! Please make sure your url is valid')
            
        if image:
            res.set_property("thumbnail", url)
            return await ctx.send(f'Done! Updated your todo list\'s thumbnail to `{url}`', allowed_mentions=discord.AllowedMentions.none())
        else:
            await ctx.send('You didn\'t provide a valid url with an image! Please make sure your url is valid')

    @check()
    @todo.command(extras={"category":Category.TODO}, usage="custom_id <new_id>")
    async def custom_id(self, ctx, custom_id):
        """Lets you change your todo lists custom id- provided you are premium supporter (Only in editor mode)"""
        try:
            list_id = editing[ctx.author.id]
        except KeyError:
            return await ctx.send(f'You have to be in the editor mode to use this command! Use `{self.client.command_prefix(self.client, ctx.message)[2]}todo edit <todo_list_id>`', allowed_mentions=discord.AllowedMentions.none())
        user = User(ctx.author.id)
        todo_list = TodoList(list_id)

        if not user.is_premium:
            return await ctx.send('Nice try, but you need to be a premium supporter of Killua to create a custom id')

        if len(custom_id) > 20:
            return await ctx.send('Your custom id can not have more than 20 characters')

        if custom_id.lower() == '-rm' or custom_id.lower() == '-r':
            todo_list.custom_id = None
            return await ctx.send(f'Done! Removed the custom id from your list')

        try:
            TodoList(custom_id.lower())
        except TodoListNotFound:
            todo_list.set_property("custom_id", custom_id.lower())
            return await ctx.send(f'Done! Updated your todo list\'s custom id to `{custom_id}`', allowed_mentions=discord.AllowedMentions.none())
        else:
            await ctx.send("This custom id is already taken!")

    @check()
    @todo.command(extras={"category":Category.TODO}, usage="autodelete <on/off>")
    async def autodelete(self, ctx, on_or_off):
        """Let's you change if you mark a todo task as done if it should automatically delete it or not (Only in editor mode)"""
        res = await self._set_check(ctx)
        if not res:
            return

        if not on_or_off.lower() in ['on', 'off']:
            return await ctx.send('You either need to activate this feature (**on**) or deactivate it (**off**)')

        if on_or_off.lower() == 'on':
            if res.delete_done is True:
                return await ctx.send('You already have this feature enabled')
            res.set_property("delete_done", True)
            return await ctx.send(f'Done! Activated your lists auto delete feature when something is marked as `done`')
        elif on_or_off.lower() == 'off':
            if res.delete_done is False:
                return await ctx.send('You already have this feature disabled')
            res.set_property("delete_done", False)
            return await ctx.send(f'Done! Deactivated your lists auto delete feature when something is marked as `done`')

    @check()
    @todo.command(extras={"category":Category.TODO}, usage="description <new_name>")
    async def description(self, ctx, *, new_desc:str):
        """Change the description of your todo list with this command (Only in editor mode)"""
        res = await self._set_check(ctx)
        if not res:
            return

        if len(new_desc) > 200:
            return await ctx.send("The description cannot be longer than 200 characters!")
        res.set_property("description", new_desc)
        await ctx.send(f'Done! Update your todo list\'s description!')

    @check()
    @todo.command(extras={"category":Category.TODO}, usage="remove <task_id>")
    async def remove(self, ctx, todo_numbers: commands.Greedy[int]):
        """Remove a todo with this command. YAY, GETTING THINGS DONE!! (Only in editor mode)"""
        try:
            list_id = editing[ctx.author.id]
        except KeyError:
            return await ctx.send(f'You have to be in the editor mode to use this command! Use `{self.client.command_prefix(self.client, ctx.message)[2]}todo edit <todo_list_id>`')
        
        if len(todo_numbers) == 0:
            return await ctx.send("No valid numbers provided")

        todo_list = TodoList(list_id)
        todos = todo_list.todos

        failed = []
        for n in todo_numbers:
            if not todo_list.has_todo(n):
                failed.append(n)
                continue
            todos.pop(n-1)
        if len(todo_numbers) == len(failed):
            return await ctx.send("All inputs are invalid task ids. Please try again.")

        todo_list.set_property("todos", todos)
        return await ctx.send(f'You removed todo number{"s" if len(todo_numbers) > 1 else ""} {", ".join([str(x) for x in todo_numbers])} successfully' + (". Failed to remove the following numbers because they are invalid: " + ", ".join([str(x) for x in failed]) if len(failed) > 0 else ""), allowed_mentions=discord.AllowedMentions.none())

    @check()
    @todo.command(extras={"category":Category.TODO}, usage="mark <task_id> <text>")
    async def mark(self, ctx, todo_number:int, *,marked_as:str):
        """Mark a todo with a comment like `done` or `too lazy` (Only in editor mode)"""
        try:
            list_id = editing[ctx.author.id]
        except KeyError:
            return await ctx.send(f'You have to be in the editor mode to use this command! Use `{self.client.command_prefix(self.client, ctx.message)[2]}todo edit <todo_list_id>`')
        
        todo_list = TodoList(list_id)
        todos = todo_list.todos

        if not todo_list.has_todo(todo_number):
            return await ctx.send(f'You don\'t have a number {todo_number} on your current todo list', allowed_mentions=discord.AllowedMentions.none())

        if  marked_as.lower() == 'done' and todo_list.delete_done is True:
            todos.pop(todo_number-1)
            todo_list.set_property("todos", todos)
            return await ctx.send(f'Marked to-do number {todo_number} as done and deleted it per default')
        elif marked_as.lower() == '-r' or marked_as.lower() == '-rm':
            todos[todo_number-1]['marked'] = None
            mark_log = {
                'author': ctx.author.id,
                'change': 'REMOVED MARK',
                'date': (datetime.now()).strftime("%b %d %Y %H:%M:%S")
            }
            todos[todo_number-1]['mark_log'].append(mark_log)
            todo_list.set_property("todos", todos)
            return await ctx.send(f'Removed to-do number {todo_number} successfully!', allowed_mentions=discord.AllowedMentions.none())
        else:
            todos[todo_number-1]['marked'] = marked_as
            mark_log = {
                'author': ctx.author.id,
                'change': marked_as,
                'date': (datetime.now()).strftime("%b %d %Y %H:%M:%S")
            }
            todos[todo_number-1]['mark_log'].append(mark_log)
            todo_list.set_property("todos", todos)
            return await ctx.send(f'Marked to-do number {todo_number} as `{marked_as}`!', allowed_mentions=discord.AllowedMentions.none())

    @check()
    @todo.command(extras={"category":Category.TODO}, usage="add <text>")
    async def add(self, ctx, *, task):
        """Add a todo to your list, *yay, more work* (Only in editor mode)"""
        try:
            list_id = editing[ctx.author.id]
        except KeyError:
            return await ctx.send(f'You have to be in the editor mode to use this command! Use `{self.client.command_prefix(self.client, ctx.message)[2]}todo edit <todo_list_id>`', allowed_mentions=discord.AllowedMentions.none())

        todo_list = TodoList(list_id)

        if len(task) > 100:
            return await ctx.send('Your todo can\'t have more than 100 characters')
        
        if len(todo_list.todos) >= todo_list.spots:
            return await ctx.send(f'You don\'t have enough spots for that! Buy spots with `{self.client.command_prefix(self.client, ctx.message)[2]}todo buy space`. You can currently only have up to {todo_list.spots} spots in this list', allowed_mentions=discord.AllowedMentions.none())

        todos = todo_list.todos
        todos.append({'todo': task, 'marked': None, 'added_by': ctx.author.id, 'added_on': (datetime.now()).strftime("%b %d %Y %H:%M:%S"),'views': 0, 'assigned_to': [], 'mark_log': []})
        
        todo_list.set_property("todos", todos)
        return await ctx.send(f'Great! Added {task} to your todo list!', allowed_mentions=discord.AllowedMentions.none())

    @check(20)
    @todo.command(extras={"category":Category.TODO}, usage="kick <user>")
    async def kick(self, ctx, user: Union[discord.User, int]):
        """Kick someone with permissions from your todo list (this takes **every** permission) (Only in editor mode)"""
        try:
            list_id = editing[ctx.author.id]
        except KeyError:
            return await ctx.send('You are not editing a list at the moment')
        todo_list = TodoList(list_id)

        if isinstance(user, int):
            try:
                user = await self._get_user(user)
            except discord.NotFound:
                return await ctx.send('Invalid ID')

        if not ctx.author.id == todo_list.owner:
            return await ctx.send('You have to own the todo list to remove permissions from users')
            
        if not (user.id in todo_list.viewer or user.id in todo_list.editor):
            return await ctx.send('The user you specified doesn\'t have permission to view or edit the todo list, you can\'t take permissions you never granted')

        if user.id in todo_list.editor:
            todo_list.kick_editor(user.id)
            await ctx.send(f'You have successfully taken the editor permission from {user}', allowed_mentions=discord.AllowedMentions.none())

        if user.id in todo_list.viewer:
            todo_list.kick_viewer(user.id)
            await ctx.send(f'You have successfully taken the viewer permission from {user}', allowed_mentions=discord.AllowedMentions.none())

    @check()
    @todo.command(extras={"category":Category.TODO}, usage="exit")
    async def exit(self, ctx):
        """Exit editing mode with this. I've never used it because it is pointless because my code is so good you realistically never need to be out of editing mode but it is here so use it"""
        try:
            list_id = editing[ctx.author.id]
        except KeyError:
            return await ctx.send('You are not editing a list at the moment')
        
        editing.pop(ctx.author.id, None)
        return await ctx.send('Exiting editing mode!')

    @check(20)
    @todo.command(extras={"category":Category.TODO}, usage="invite <user> <editor/viewer>")
    async def invite(self, ctx, user: Union[discord.User, int], role):
        """Wanna let your friend add more todos for you? Invite them! You can also make people view your todo list when it is set on private (Only in editor mode)"""
        try:
            list_id = editing[ctx.author.id]
        except KeyError:
            return await ctx.send(f'You have to be in the editor mode to use this command! Use `{self.client.command_prefix(self.client, ctx.message)[2]}todo edit <todo_list_id>`', allowed_mentions=discord.AllowedMentions.none())

        if user.id == ctx.author.id:
            return await ctx.send('You are already owner, you don\'t need to invite yourself')

        if blcheck(user.id):
            return await ctx.send('You can\'t invite a blacklisted user')
        
        todo_list = TodoList(list_id)

        if not role.lower() in ['editor', 'viewer']:
            return await ctx.send(f'Please choose a valid role to grant {user.name} (either `viewer` or `editor`)', allowed_mentions=discord.AllowedMentions.none())

        if role.lower() == "viewer" and todo_list.status == "public":
            return await ctx.send("You can't add viewers to a public todo list. Everyone has viewing permissions on this list")

        if user.id in getattr(todo_list, role.lower()):
            return await ctx.send("The specified user already has that role!")

        if role == "viewer" and user.id in todo_list.editor:
            return await ctx.send("User already has editor permissions, you can't also add viewer permission")

        embed = discord.Embed.from_dict({
            'title': f'You were invited to to-do list {todo_list.name} (ID: {todo_list.id})',
            'description': f'{ctx.author} invited you to be {role} in their to-do list. To accept, click "confirm", to deny click "cancel". If this invitation was inappropriate, click "report"',
            'color': self._get_color(todo_list),
            'footer': {'icon_url': str(ctx.author.avatar.url), 'text': f'Requested by {ctx.author}'}
        })

        try:
            view = ConfirmButton(user.id, timeout=80)
            view.add_item(Button(label="Report", custom_id="report", style=discord.ButtonStyle.red))
            msg = await user.send(embed=embed, view=view)
            await ctx.send('Successfully send the invitation to the specified user! They have 24 hours to accept or deny')
        except discord.Forbidden:
            return await ctx.send('Failed to send the user a dm. Make sure they are on a guild Killua is on and has their dms open')

        await view.wait()
        await view.disable(msg)

        if not view.value:
            if view.timed_out:
                await user.send("Timed out!")
                return await ctx.author.send(f"{user} has not responded to your invitation in 24 hours so the invitation went invalid")
            else:
                await user.send('Successfully denied invitation')
                return await ctx.author.send(f'{user} has denied your invitation the todo list `{todo_list.name}`', allowed_mentions=discord.AllowedMentions.none())
        
        elif view.value == "report":
            channel = self.client.get_channel(REPORT_CHANNEL)
            embed = discord.Embed.from_dict({
                "title": f"Report from {user}",
                "fields": [
                    {"name": "Guild", "value": f"ID: {ctx.guild.id}\nName: {ctx.guild.name}"},
                    {"name": "Reported user", "value": f"ID: {ctx.author.id}\nName: {ctx.author.name}"},
                    {"name": "Todo list", "value": f"ID: {todo_list.id}\nName: {todo_list.name}"}
                ],
                "color": 0xff0000,
                "footer": {"text": user.id, "icon_url": str(user.avatar.url)},
                "thumbnail": {"url": str(ctx.author.avatar.url)}
            })
            await channel.send(embed=embed)
            await ctx.author.send(f"{user} reported your invite to your todo list")
            return await user.send(f"Successfully reported {ctx.author.name}!")

        if role.lower() == 'viewer':
            todo_list.add_viewer(user.id)

        if role.lower() == 'editor':
            if user.id in todo_list.viewer:
                todo_list.kick_viewer(user.id) # handled like a promotion and exchanges viewer perms for edit perms
            todo_list.add_editor(user.id)

        await user.send(f'Success! You have now {role} permissions in the todo list `{todo_list.name}`', allowed_mentions=discord.AllowedMentions.none())
        return await ctx.author.send(f'{user} accepted your invitation to your todo list `{todo_list.name}`!', allowed_mentions=discord.AllowedMentions.none())


    @check()
    @todo.command(extras={"category":Category.TODO}, usage="assign <task_id> <user>")
    async def assign(self, ctx, todo_number:int, user: Union[discord.User, int], rm=None):
        """Assign someone a todo task with this to coordinate who does what (Only in editor mode)"""
        try:
            list_id = editing[ctx.author.id]
        except KeyError:
            return await ctx.send('You have to be in the editor mode to use this command! Use `k!todo edit <todo_list_id>`')

        todo_list = TodoList(list_id)

        if isinstance(user, int):
            try:
                user = await self._get_user(user)
            except discord.NotFound:
                return await ctx.send('Invalid user id')

        if not user.id == todo_list.owner and not user.id in todo_list.editor:
            return await ctx.send('You can only assign people todos who have permission to edit this todo list')

        todos = todo_list.todos

        if not todo_list.has_todo(todo_number):
            return await ctx.send(f'You don\'t have a number {todo_number} on your current todo list')
        if rm:
            if rm.lower() == '-rm' or rm.lower() == '-r':
                if not user.id in todos[todo_number-1]['assigned_to']:
                    return await ctx.send('The user is not assigned to this todo task so you can\'t remove them')
                if not ctx.author == user:
                    embed = discord.Embed.from_dict({
                    'title': f'Removed assignment to todo on list {todo_list.name} (ID: {todo_list.id})',
                    'description': f'{ctx.author} removed assignment you to the todo {todos[todo_number-1]["todo"]}',
                    'color': self._get_color(todo_list),
                    'footer': {'icon_url': str(ctx.author.avatar.url), 'text': f'Requested by {ctx.author}'}
                    })
                    try:
                        await user.send(embed=embed)
                    except discord.Forbidden:
                        pass
                todos[todo_number-1]['assigned_to'].remove(user.id)
                todo_list.set_property("todos", todos)
                return await ctx.send(f'Successfully removed assignment of todo task {todo_number} to {user}')
            else:
                await ctx.send(f'Invalid argument for `rm`. Command usage: `{self.client.command_prefix(self.client, ctx.message)[2]}todo assign <todo_number> <user> <optional_rm>` where -rm would remove them from that task', allowed_mentions=discord.AllowedMentions.none())

        if user in todos[todo_number-1]['assigned_to']:
            return await ctx.send('The user specified is already assigned to that todo task')

        todos[todo_number-1]['assigned_to'].append(user.id)
        todo_list.set_property("todos", todos)

        if not ctx.author == user:
            embed = discord.Embed.from_dict({
                'title': f'Assigned to todo on list {todo_list.name} (ID: {todo_list.id})',
                'description': f'{ctx.author} assigned you to the todo {todos[todo_number-1]["todo"]}',
                'color': self._get_color(todo_list),
                'footer': {'icon_url': str(ctx.author.avatar.url), 'text': f'Requested by {ctx.author}'}
            })
            try:
                await user.send(embed=embed)
            except discord.Forbidden:
                pass
        return await ctx.send(f'Successfully assigned the task with number {todo_number} to `{user}`', allowed_mentions=discord.AllowedMentions.none())
    
    @check()
    @todo.command(extras={"category":Category.TODO}, usage="delete <list_id>")
    async def delete(self, ctx, todo_id:Union[int, str]):
        """Use this command to delete your todo list. Make sure to say goodbye a last time"""
        try:
            todo_list = TodoList(todo_id)
        except TodoListNotFound:
            return await ctx.send('A list with this id does not exist')

        if not ctx.author.id == todo_list.owner:
            return await ctx.send('Only the owner of a todo list can delete it')

        todo_list.delete()
        return await ctx.send(f'Done! Deleted todo list {todo_list.name}', allowed_mentions=discord.AllowedMentions.none())

    @check()
    @todo.command(extras={"category":Category.TODO}, usage="lists")
    async def lists(self, ctx):
        """This shows a list of todo lists you own or have access to"""
        lists_owning = todo.find({'owner': ctx.author.id})
        lists_viewing = todo.find({'viewer': ctx.author.id})
        lists_editing = todo.find({'editor': ctx.author.id})

        l_o = '\n'.join([f'{l["name"]} (id: {l["_id"]}/{l["custom_id"] or "No custom id"})' for l in lists_owning])
        l_v = '\n'.join([f'{l["name"]} (id: {l["_id"]}/{l["custom_id"] or "No custom id"})' for l in lists_viewing])
        l_e = '\n'.join([f'{l["name"]} (id: {l["_id"]}/{l["custom_id"] or "No custom id"})' for l in lists_editing])

        embed = discord.Embed.from_dict({
            'title': f'Your todo lists and permissions',
            'description': f'__`todo lists you own`__\n\n{l_o or "No todo lists"}\n\n__`todo lists you have viewing permissions`__\n\n{l_v or "No todo lists"}\n\n__`todo lists you have editing permissions`__\n\n{l_e or "No todo lists"}',
            'color': 0x1400ff,
            'footer': {'icon_url': str(ctx.author.avatar.url), 'text': f'Requested by {ctx.author}'}
        })
        return await ctx.send(embed=embed)
  
Cog = TodoSystem
        
def setup(client):
    client.add_cog(TodoSystem(client))
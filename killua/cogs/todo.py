import discord
from discord.ext import commands
from killua.checks import check, blcheck
import asyncio
from datetime import datetime
import re
import math
from typing import Union
from killua.classes import TodoList, Todo, User, TodoListNotFound, Category
from killua.constants import teams, todo
from killua.paginator import Paginator

editing = {}

class TodoSystem(commands.Cog):

    def __init__(self,client):
        self.client = client

    async def _get_user(self, u:int) -> discord.User:
        r = self.client.get_user(u)
        if not r:
            r = await self.client.fetch_user(u)
        return r

    def _get_color(self, l:TodoList):
        return l.color if l.color else 0x1400ff

    async def _wait_for_response(self, step, check) -> Union[discord.Message, None]:
        try:
            confirmmsg = await self.client.wait_for('message', check=check, timeout=60)
        except asyncio.TimeoutError:
            await step.delete()
            await ctx.send('Too late...', delete_after=5)
            return None
        else:
            await step.delete()
            try:
                await confirmmsg.delete()
            except discord.HTTPException:
                pass
            return confirmmsg

    async def _build_embed(self, todo_list:TodoList, page:int=None) -> discord.Embed:
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
            t = Todo(n+1, str(todo_list.id))
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
        """async function todo_name
        Input:
        ctx: to have somthing to use .send() on

        Returns:
        title: title of the todo list

        Purpose: 
        outsourcing todo create in smaller functions
        """
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
        """async function todo_status
        Input:
        ctx: to have somthing to use .send() on

        Returns:
        status: if the todo list is public/private

        Purpose: 
        outsourcing todo create in smaller functions
        """
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
        """async function todo_done_delete
        Input:
        ctx: to have somthing to use .send() on

        Returns:
        (boolean): If todos should be deleted when they are marketr as done

        Purpose: 
        outsourcing todo create in smaller functions
        """
        embed = discord.Embed.from_dict({
            'title': f'Editing settings',
            'description': f'Should todo tasks marked as "done" be automatically deleted? **[y/n]**',
            'color': 0x1400ff,
            'footer': {'icon_url': str(ctx.author.avatar.url), 'text': f'Requested by {ctx.author}'}
        })
        step = await ctx.send(embed=embed)
        def check(m):
            return m.content.lower() in ['y', 'n'] and m.author.id == ctx.author.id

        confirmmsg = await self._wait_for_response(step, check)

        if not confirmmsg:
            return None
        return confirmmsg.content.lower() == 'y'

    async def todo_custom_id(self, ctx):
        """async function todo_custom_id
        Input:
        ctx: to have somthing to use .send() on

        Returns:
        (boolean): if the todo list has been assigned to a custom status

        Purpose: 
        outsourcing todo create in smaller functions
        """
        embed = discord.Embed.from_dict({
            'title': f'Editing',
            'description': f'Since you are a premium supporter you have the option to use a custom to-do id which can also be a string (f.e. Killua). You can still use to id to go into the todo list. If you want a custom id, enter it now, if you don\'t then enter **n**',
            'color': 0x1400ff,
            'footer': {'icon_url': str(ctx.author.avatar.url), 'text': f'Requested by {ctx.author}'}
        })
        step = await ctx.send(embed=embed)

        def check(m):
            return m.author.id == ctx.author.id
        confirmmsg = await self._wait_for_response(step, check)
        if not confirmmsg:
            return None

        if confirmmsg.content.lower() == 'n':
            return None
        
        if len(confirmmsg.content) > 20:
            await ctx.send('Your custom id can have max 20 characters')
            return await self.todo_custom_id(ctx)
        return confirmmsg.content.lower()

    async def todo_info_embed_generator(self, ctx, list_id):
        """async function todo_info_embed_generator
        Input:
        ctx: to have somthing to use .send() on
        list_id (string/int): the todo list's id

        Returns:
        embed: An embed with infos about a todo list

        Purpose: 
        outsourcing big embed production 🛠
        """
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
    **Todos**: `{len(todo_list)}/{todo_list.spots}`\n
    **Created on:** `{todo_list.created_at}`\n
    *{todo_list.views} views*
    ''',
            'color': self._get_color(todo_list),
        })
        if todo_list.thumbnail:
            embed.set_thumbnail(url=todo_list.thumbnail)

        return await ctx.send(embed=embed)

    async def single_todo_info_embed_generator(self, ctx, list_id, task_id):
        """async function single_todo_info_embed_generator
        Input:
        ctx: to have somthing to use .send() on
        todo_id (integer): the number of the todo task
        list_id: the id of the list the todo is from

        Returns:
        embed: An embed with infos about a todo task

        Purpose: 
        outsourcing big embed production 🛠
        """
        
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
        return await ctx.send(embed=embed)

    async def buy_color(self, ctx):
        """async function buy_color
        Input:
        ctx: to have somthing to use .send() on

        Returns:
        (discord.Message)/itself: Either a confirm message or itself if something was invalid

        Purpose: 
        outsourcing todo buy in smaller functions
        """
        list_id = editing[ctx.author.id]
        todo_list = TodoList(list_id)
        user = User(ctx.author.id)
        if user.jenny < 1000:
            return await ctx.send('You don\'t have enough Jenny to buy a color for your todo list. You need 1000 Jenny')
        
        if todo_list.color:
            return await ctx.send('You already have bought a color for this list! Update it with `k!todo color <color>`')

        step = await ctx.send('Please provide a color you want your todo list to have, you can always change it later')
        def check(m):
            return m.author.id == ctx.author.id

        confirmmsg = await self._wait_for_response(step, check)
        if not confirmmsg:
            return
        c = f'0x{confirmmsg.content}'
        try:
            if not int(c, 16) <= 16777215:
                await ctx.send('You need to provide a valid color! (Default color is 1400ff f.e.)')
                return await self.buy_color(ctx)
        except Exception:
            await ctx.send('You need to provide a valid color! (Default color is 1400ff f.e.)')
            return await self.buy_color(ctx)

        user.remove_jenny(1000)
        todo_list.set_property('color', int(c, 16))
        return await ctx.send(f'Successfully bought the color {confirmmsg.content} for your list! You can change it with `k!todo color <url>`')


    async def buy_thumbnail(self, ctx):
        """async function buy_thumbnail
        Input:
        ctx: to have somthing to use .send() on

        Returns:
        (discord.Message)/itself: Either a confirm message or itself if something was invalid

        Purpose: 
        outsourcing todo buy in smaller functions
        """
        list_id = editing[ctx.author.id]
        todo_list = TodoList(list_id)
        user = User(ctx.author.id)
        if user.jenny < 1000:
            return await ctx.send('You don\'t have enough Jenny to buy a thumbnail for your todo list. You need 1000 Jenny')

        if todo_list.thumbnail:
            return await ctx.send('You already have bought a thumbnail for this list! Update it with `k!todo thumbnail <thumbnail_url>`')

        step = await ctx.send('Please provide a thumbnail you want your todo list to have, you can always change it later')
        def check(m):
            return m.author.id == ctx.author.id

        confirmmsg = await self._wait_for_response(step, check)
        if not confirmmsg:
            return

        url = re.search(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))', confirmmsg.content)

        if url:
            image = re.search(r'png|jpg|gif|svg', confirmmsg.content)
        else:
            await ctx.send('You didn\'t provide a valid url with an image! Please make sure you do that')
            return await self.buy_thumbnail(ctx)
                
        if image:
            user.remove_jenny(1000)
            todo_list.set_property('thumbnail', confirmmsg.content)
            return await ctx.send(f'Successfully bought the thumbmail `{confirmmsg.content}` for your list! You can change it with `k!todo thumbnail <url>`')
        else:
            await ctx.send('You didn\'t provide a valid url with an image! Please make sure you do that')
            return await self.buy_thumbnail(ctx)

    async def buy_space(self, ctx):
        # This is the best thing to buy for your todo list
        """async function buy_space
        Input:
        ctx: to have somthing to use .send() on

        Returns:
        (discord.Message): Confirm message

        Purpose: 
        outsourcing todo buy in smaller functions
        """
        list_id = editing[ctx.author.id]
        todo_list = TodoList(list_id)
        user = User(ctx.author.id)

        if user.jenny < (todo_list.spots * 100 * 0.5):
            return await ctx.send(f'You don\'t have enough Jenny to buy more space for your todo list. You need {todo_list["spots"]*100} Jenny')

        if todo_list.spots >= 100:
            return await ctx.send('You can\'t buy more than 100 spots')

        step = await ctx.send(f'Do you want to buy 10 more to-do spots for this list? Current spots: {todo_list.spots} Cost: {todo_list.spots*100*0.5} points \n**[y/n]**')
        def check(m):
            return m.content.lower() in ['y', 'n'] and m.author.id == ctx.author.id

        confirmmsg = await self._wait_for_response(step, check)
        if not confirmmsg:
            return

        if confirmmsg.content.lower() == 'n':
            return await ctx.send('Alright, see you later then :3')

        user.remove_jenny(int(100*todo_list.spots*0.5))
        todo_list.add_spots(10)
        return await ctx.send('Congrats! You just bought 10 more todo spots for the current todo list!')

    async def buy_description(self, ctx):
        #Hi! You found a random comment! Now you have to vote for Killua :3 (Also thanks for checking out my code)
        """async function buy_description
        Input:
        self: inputting because function is outside of cog
        ctx: to have somthing to use .send() on

        Returns:
        (discord.Message)/itself: Either a confirm message or itself if something was invalid

        Purpose: 
        outsourcing todo buy in smaller functions
        """
        list_id = editing[ctx.author.id]
        todo_list = TodoList(list_id)
        user = User(ctx.author.id)
        if user.jenny < 1000:
            return await ctx.send('You don\'t have enough Jenny to buy a thumbnail for your todo list. You need 1000 Jenny')
        
        step = await ctx.send(f'What should the description of your todo list be? (max 200 characters)')
        def check(m):
            return m.author.id == ctx.author.id
        
        confirmmsg = await self._wait_for_response(step, check)
        if not confirmmsg:
            return

        if len(confirmmsg.content) > 200:
            await ctx.send('Your description can\'t be over 200 characters!')
            return await self.buy_description(ctx)
        tuser.remove_jenny(1000)
        todo_list.set_property('description', description)
        return await ctx.send('Congrats! You bought a description for your current todo list')

    @commands.group(hidden=True)
    async def todo(self, ctx):
        #h You most likely want info about another todo command. Use `k!help command todo <todo_command>` for that
        pass

    @check(10)
    @todo.command(extras={"category":Category.TODO}, usage="todo create")
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
            if custom_id is None:
                return
        else:
            custom_id = None
        
        TodoList.create(owner=ctx.author.id, title=title, status=status, done_delete=done_delete, custom_id=custom_id)
        await ctx.send(f'Created the todo list with the name {title}. You can look at it and edit it through the id `{todo_id}`' + f'or through your custom id {custom_id}' if custom_id else '')

    @check()
    @todo.command(extras={"category":Category.TODO}, usage="todo view <list_id(optional)>")
    async def view(self, ctx, todo_id=None):
        """Allows you to view what is on any todo list- provided you have the permissions"""
        if todo_id is None:
            try:
                list_id = editing[ctx.author.id]
            except KeyError:
                return await ctx.send('You have to be in the editor mode to use this command without providing an id! Use `k!todo edit <todo_list_id>`')

            todo_id = str(list_id)

        try:
            todo_list = TodoList(todo_id)
        except TodoListNotFound:
            return await ctx.send('No todo list with specified ID found')

        if not todo_list.has_view_permission(ctx.author.id):
            return await ctx.send('This is a private list you don\'t have the permission to view')
        todo_list.add_view(ctx.author.id)

        if len(todo_list) <= 10:
            return await ctx.send(self._build_embed(todo_list))

        async def make_embed(page, embed, pages):
            return await self._build_embed(pages, page)
        await Paginator(ctx, todo_list, max_pages=math.ceil(len(todo_list)/10),func=make_embed).start()

    @check()
    @todo.command(extras={"category":Category.TODO}, usage="todo clear")
    async def clear(self, ctx):
        """Clears all todos from a todo list"""
        try:
            list_id = editing[ctx.author.id]
        except KeyError:
            return await ctx.send('You have to be in the editor mode to use this command without providing an id! Use `k!todo edit <todo_list_id>`')

        todo_list = TodoList(str(list_id))
        if not todo_list.has_edit_permission(ctx.author.id):
            return await ctx.send("You have to be added as an editor to this list to use this command")
        todo_list.clear()
        await ctx.send("Done! Cleared all your todos")

    @check(1)
    @todo.command(extras={"category":Category.TODO}, usage="todo info <list_id/task_id> <task_id(if list_id provided)>")
    async def info(self, ctx, todo_or_task_id=None, td:int=None):
        """This gives you info about either a todo task or list"""
        if td is None:
            if todo_or_task_id is None:
                try:
                    list_id = editing[ctx.author.id]
                except KeyError:
                    return await ctx.send('You need to be in editor mode for a list or provide an id to use this command')
                return await self.todo_info_embed_generator(ctx, str(list_id))
            try:
                list_id = editing[ctx.author.id]
            except KeyError:
                return await self.todo_info_embed_generator(ctx, todo_or_task_id)
            return await self.single_todo_info_embed_generator(ctx, list_id, int(todo_or_task_id))
        elif td:
            return await self.single_todo_info_embed_generator(ctx, todo_or_task_id, int(td))

    @check()
    @todo.command(extras={"category":Category.TODO}, usage="todo edit <list_id>")
    async def edit(self, ctx, list_id):
        """The command with which you can change stuff on your todo list"""
        try:
            todo_list = TodoList(list_id)
        except TodoListNotFound:
            return await ctx.send('No todo list with this id exists')

        if not todo_list.has_edit_permission(ctx.author.id):
            return await ctx.send('You do not have the permission to edit this todo list')
        await ctx.send(f'You are now in editor mode for todo list "{todo_list.name}"')
        editing[ctx.author.id] = todo_list.id

    @check()
    @todo.command(extras={"category":Category.TODO}, usage="todo name <new_name>")
    async def name(self, ctx, new_name:str):
        """Rename your todo list with thsi command (Only in editor mode)"""
        try:
            list_id = editing[ctx.author.id]
        except KeyError:
            return await ctx.send('You have to be in the editor mode to use this command! Use `k!todo edit <todo_list_id>`')
        TodoList(list_id).set_property('name', new_name)
        await ctx.send(f'Done! Update your todo list\'s name to "{new_name}"')

    @check()
    @todo.command(extras={"category":Category.TODO}, usage="todo status <new_status>")
    async def status(self, ctx, status):
        """Change the status of your todo list (public/private) with this command (Only in editor mode)"""
        try:
            list_id = editing[ctx.author.id]
        except KeyError:
            return await ctx.send('You have to be in the editor mode to use this command! Use `k!todo edit <todo_list_id>`')
        if not status.lower() in ['private', 'public']:
            return await ctx.send('You need to chose a valid status (private/public)')
        TodoList(list_id).set_property('status', status.lower())
        await ctx.send(f'Done! Updated your todo list\'s status to `{status.lower()}`')

    @check()
    @todo.command(extras={"category":Category.TODO}, usage="todo color <new_color_in_hex>")
    async def color(self, ctx, color):
        """Change your todo list's color with this command (Only in editor mode)"""
        try:
            list_id = editing[ctx.author.id]
        except KeyError:
            return await ctx.send('You have to be in the editor mode to use this command! Use `k!todo edit <todo_list_id>`')
        todo_list = TodoList(list_id)
        if not todo_list.color:
            return await ctx.send('You need to have bought this feature for your current todo list with `k!todo buy color`')
            
        c = f'0x{color}'
        try:
            if not int(c, 16) <= 16777215:
                await ctx.send('You need to provide a valid color! (Default color is 1400ff f.e.)')
        except Exception:
            await ctx.send('You need to provide a valid color! (Default color is 1400ff f.e.)')

        todo_list.set_property('color', int(c, 16))
        await ctx.send(f'Done! Updated your todo list\'s color to `{c}`')

    @check()
    @todo.command(extras={"category":Category.TODO}, usage="todo thumbnail <new_thumbnail>")
    async def thumbnail(self, ctx, url):
        """Change your todo lists thumbnail with this command (Only in editor mode)"""
        try:
            list_id = editing[ctx.author.id]
        except KeyError:
            return await ctx.send('You have to be in the editor mode to use this command! Use `k!todo edit <todo_list_id>`')
        todo_list = TodoList(list_id)

        if not todo_list.thumbnail:
            return await ctx.send('You need to have bought this feature for your current todo list with `k!todo buy color`')

        search_url = re.search(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))', url)

        if search_url:
            image = re.search(r'png|jpg|gif|svg', url)
        else:
            await ctx.send('You didn\'t provide a valid url with an image! Please make sure you do')
            
        if image:
            todo_list.set_property('thumbnail', url)
            return await ctx.send(f'Done! Updated your todo list\'s thumbnail to `{url}`')
        else:
            await ctx.send('You didn\'t provide a valid url with an image! Please make sure you do that')

    @check()
    @todo.command(extras={"category":Category.TODO}, usage="todo custom_id <new_id>")
    async def custom_id(self, ctx, custom_id):
        """Lets you change your todo lists custom id- provided you are premium supporter (Only in editor mode)"""
        try:
            list_id = editing[ctx.author.id]
        except KeyError:
            return await ctx.send('You have to be in the editor mode to use this command! Use `k!todo edit <todo_list_id>`')
        user = User(ctx.author.id)
        todo_list = TodoList(list_id)

        if not user.is_premium:
            return await ctx.send('Nice try, but you need to be a premium supporter of Killua to create a custom id')

        if len(custom_id) > 20:
            return await ctx.send('Your custom id can not have more than 20 characters')

        if custom_id.lower() == '-rm' or custom_id.lower() == '-r':
            todo_list.set_property('custom_id', None)
            return await ctx.send(f'Done! Removed the custom id from your list')
        todo_list.set_property('custom_id', custom_id)
        return await ctx.send(f'Done! Updated your todo list\'s custom id to `{custom_id}`')

    @check()
    @todo.command(extras={"category":Category.TODO}, usage="todo autodelete <on/off>")
    async def autodelete(self, ctx, on_or_off):
        """Let's you change if you mark a todo task as done if it should automatically delete it or not (Only in editor mode)"""
        try:
            list_id = editing[ctx.author.id]
        except KeyError:
            return await ctx.send('You have to be in the editor mode to use this command! Use `k!todo edit <todo_list_id>`')
        if not on_or_off.lower() in ['on', 'off']:
            return await ctx.send('You either need to activate this feature (**on**) or deactivate it (**off**)')
        
        todo_list = TodoList(list_id)

        if on_or_off.lower() == 'on':
            if todo_list.delete_done is True:
                return await ctx.send('You already have this feature enabled')
            todo_list.set_property('delete_done', True)
            return await ctx.send(f'Done! Activated your lists auto delete feature when something is marked as `done`')
        elif on_or_off.lower() == 'off':
            if todo_list.delete_done is False:
                return await ctx.send('You already have this feature disabled')
            todo_list.set_property('delete_done', False)
            return await ctx.send(f'Done! Deactivated your lists auto delete feature when something is marked as `done`')

    @check()
    @todo.command(extras={"category":Category.TODO}, usage="todo remove <task_id>")
    async def remove(self, ctx, todo_numbers: commands.Greedy[int]):
        """Remove a todo with this command. YAY, GETTING THINGS DONE!! (Only in editor mode)"""
        try:
            list_id = editing[ctx.author.id]
        except KeyError:
            return await ctx.send('You have to be in the editor mode to use this command! Use `k!todo edit <todo_list_id>`')
        
        todo_list = TodoList(list_id)
        for n in todo_numbers:
            if n < 0:
                return await ctx.send('You can\'t remove a number less than 1')
        try:
            todos = todo_list.todos
            for n in todo_numbers:
                todos.pop(n-1)
            todo_list.set_property('todos', todos)
            return await ctx.send(f'You removed todo number{"s" if len(todo_numbers) > 1 else ""} {", ".join(todo_numbers)} successfully')
        except Exception:
            return await ctx.send('You need to provide only valid numbers!')

    @check()
    @todo.command(extras={"category":Category.TODO}, usage="todo mark <task_id> <text>")
    async def mark(self, ctx, todo_number:int, *,marked_as:str):
        """Mark a todo with a comment like `done` or `too lazy` (Only in editor mode)"""
        try:
            list_id = editing[ctx.author.id]
        except KeyError:
            return await ctx.send('You have to be in the editor mode to use this command! Use `k!todo edit <todo_list_id>`')
        
        todo_list = TodoList(list_id)
        todos = todo_list.todos

        if not todo_list.has_todo(todo_number):
            return await ctx.send(f'You don\'t have a number {todo_number} on your current todo list')

        if  marked_as.lower() == 'done' and todo_list.delete_done is True:
            todos.pop(todo_number-1)
            todo_list.set_property('todos', todos)
            return await ctx.send(f'Marked to-do number {todo_number} as done and deleted it per default')
        elif marked_as.lower() == '-r' or marked_as.lower() == '-rm':
            todos[todo_number-1]['marked'] = None
            mark_log = {
                'author': ctx.author.id,
                'change': 'REMOVED MARK',
                'date': (datetime.now()).strftime("%b %d %Y %H:%M:%S")
            }
            todos[todo_number-1]['mark_log'].append(mark_log)
            todo_list.set_property('todos', todos)
            return await ctx.send(f'Removed to-do number {todo_number} successfully!')
        else:
            todos[todo_number-1]['marked'] = marked_as
            mark_log = {
                'author': ctx.author.id,
                'change': marked_as,
                'date': (datetime.now()).strftime("%b %d %Y %H:%M:%S")
            }
            todos[todo_number-1]['mark_log'].append(mark_log)
            todo_list.set_property('todos', todos)
            return await ctx.send(f'Marked to-do number {todo_number} as `{marked_as}`!')

    @check(2)
    @todo.command(extras={"category":Category.TODO}, usage="todo buy <item>")
    async def buy(self, ctx, what):
        """Buy cool stuff for your todo list with this command! (Only in editor mode)"""
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
            return await self.buy_color(ctx)
        elif what.lower() == 'thumbnail':
            return await self.buy_thumbnail(ctx)
        elif what.lower() == 'space':
            return await self.buy_space(ctx)
        elif what.lower() == 'description':
            return await self.buy_description(ctx)

    @check()
    @todo.command(extras={"category":Category.TODO}, usage="todo shop")
    async def shop(self, ctx):
        """Get some info about what cool stuff you can buy for your todo list with this command"""
        embed = discord.Embed.from_dict({
            'title': '**The todo shop**',
            'description': '''You can buy the following items with `k!todo buy <item>` while you are in the edit menu for the todo list you want to buy the item for
            
**Cost**: 1000 Jenny
`color` change the color of the embed which displays your todo list!

**Cost**: 1000 Jenny
`thumbnail` add a neat thumbnail to your todo list (small image on the top right)

**Cost**: 1000 Jenny
`description` add a description to your todo list (recommended for public lists with custom id)

**Cost**: number of current spots * 100 * 0.5
Buy 10 more spots for todos for your list''',
            'color': 0x1400ff
        })
        await ctx.send(embed=embed)

    @check()
    @todo.command(extras={"category":Category.TODO}, usage="todo add <text>")
    async def add(self, ctx, *, td):
        """Add a todo to your list, *yay, more work* (Only in editor mode)"""
        try:
            list_id = editing[ctx.author.id]
        except KeyError:
            return await ctx.send('You have to be in the editor mode to use this command! Use `k!todo edit <todo_list_id>`')

        todo_list = TodoList(list_id)

        if len(td) > 100:
            return await ctx.send('Your todo can\'t have more than 100 characters')
        
        if len(todo_list.todos) >= todo_list.spots:
            return await ctx.send(f'You don\'t have enough spots for that! Buy spots with `{self.client.command_prefix(self.client, ctx.message)[2]}todo buy space`. You can currently only have up to {todo_list.spots} spots in this list')

        todos = todo_list.todos
        todos.append({'todo': td, 'marked': None, 'added_by': ctx.author.id, 'added_on': (datetime.now()).strftime("%b %d %Y %H:%M:%S"),'views': 0, 'assigned_to': [], 'mark_log': []})
        
        todo_list.set_property('todos', todos)
        return await ctx.send(f'Great! Added {td} to your todo list!')

    @check(20)
    @todo.command(extras={"category":Category.TODO}, usage="todo kick <user>")
    async def kick(self, ctx, user: Union[discord.User, int]):
        """Kick someone with permissions from your todo list (this takes **every** permission) (Only in editor mode)"""
        try:
            list_id = editing[ctx.author.id]
        except KeyError:
            return await ctx.send('You are not editing a list at the moment')
        todo_list = TodoList(str(list_id))

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
            await ctx.send(f'You have successfully taken the editor permission from {user}')

        if user.id in todo_list.viewer:
            todo_list.kick_viewer(user.id)
            await ctx.send(f'You have successfully taken the viewer permission from {user}')

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
    @todo.command(extras={"category":Category.TODO}, usage="todo invite <user> <editor/viewer>")
    async def invite(self, ctx, user: Union[discord.User, int], role):
        """Wanna let your friend add more todos for you? Invite them! You can also make people view your todo list when it is set on private (Only in editor mode)"""
        try:
            list_id = editing[ctx.author.id]
        except KeyError:
            return await ctx.send('You have to be in the editor mode to use this command! Use `k!todo edit <todo_list_id>`')

        if isinstance(user, int):
            try:
                user = await self._get_user(user)
            except discord.NotFound:
                return await ctx.send('Invalid user id')

        if user.id == ctx.author.id:
            return await ctx.send('You are already owner, you don\'t need to invite yourself')

        if blcheck(user.id):
            return await ctx.send('You can\'t invite a blacklisted user')
        
        todo_list = TodoList(list_id)

        if not role.lower() in ['editor', 'viewer']:
            return await ctx.send(f'Please choose a valid role to grant {user.name} (either `viewer` or `editor`)')

        embed = discord.Embed.from_dict({
            'title': f'You were invited to to-do list {todo_list.name} (ID: {todo_list.id})',
            'description': f'{ctx.author} invited you to be {role} in their to-do list. To accept, reply with **[y/n]**. To report abuse/harrassment, reply with **r**',
            'color': self._get_color(todo_list),
            'footer': {'icon_url': str(ctx.author.avatar.url), 'text': f'Requested by {ctx.author}'}
        })

        try:
            await user.send(embed=embed)
            await ctx.send('Successfully send the invitation to the specified user! They have 24 hours to accept or deny')
        except discord.Forbidden:
            return await ctx.send('Failed to send the user a dm. Make sure they are on a guild Killua is on and has their dms open')

        def check(m):
            return m.author.id == user.id and m.guild is None and m.content.lower() in ['y', 'n', 'r']

        try:
            confirmmsg = await self.client.wait_for('message', check=check, timeout=86400)
        except asyncio.TimeoutError:
            try:
                await user.send('Time to respond is up')
            except discord.Forbidden:
                pass
            return await ctx.author.send(f'{user} has not responded to your invitation in 24 hours so the invitation went invalid')
        else:
            if confirmmsg.content.lower() == 'y':
                if role.lower() == 'viewer':
                    todo_list.add_viewer(user.id)

                if role.lower() == 'editor':
                    todo_list.add_editor(user.id)

                await user.send(f'Sucess! You have now {role} permissions in the todo list `{todo_list.name}`')
                return await ctx.author.send(f'{user} accepted your invitation to your todo list `{todo_list.name}`!')

            elif confirmmsg.content.lower() == 'n':
                await user.send('Successfully denied invitation')
                return await ctx.author.send(f'{user} has denied your invitation the todo list `{todo_list.name}`')

            elif confirmmsg.content.lower() == 'r':
                channel = self.client.get_channel(796306329756893184)

                await channel.send(f'Report: \nReported by {user} (id: {user.id})\nInvite author {ctx.author} (id: {ctx.author.id})\ntodo list name: {todo_list["name"]} (id: {todo_list["_id"]})')
                await user.send('User has been reported for harrasment/abuse of the invite command. Abuse of reporting may lead to blacklisting')
                await ctx.author.send(f'You have been reported for inviting {user}, a staff member will look into the issue soon')

    @check()
    @todo.command(extras={"category":Category.TODO}, usage="todo assign <task_id> <user>")
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
                todo_list.set_property('todos', todos)
                return await ctx.send(f'Succesfully removed assignment of todo task {todo_number} to {user}')
            else:
                await ctx.send(f'Invalid argument for `rm`. Command usage: `{self.client.command_prefix(self.client, ctx.message)[2]}todo assign <todo_number> <user> <optional_rm>` where -rm would remove them from that task')

        if user in todos[todo_number-1]['assigned_to']:
            return await ctx.send('The user specified is already assigned to that todo task')

        todos[todo_number-1]['assigned_to'].append(user.id)
        todo_list.set_property('todos', todos)

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
        return await ctx.send(f'Succesfully assigned the task with number {todo_number} to `{user}`')
    
    @check()
    @todo.command(extras={"category":Category.TODO}, usage="todo delete <list_id>")
    async def delete(self, ctx, todo_id):
        """Use this command to delete your todo list. Make sure to say goodbye a last time"""
        try:
            todo_list = TodoList(todo_id)
        except TodoListNotFound:
            return await ctx.send('A list with this id does not exist')

        if not ctx.author.id == todo_list.owner:
            return await ctx.send('Only the owner of a todo list can delete it')

        todo_list.delete()
        return await ctx.send(f'Done! Deleted todo list {todo_list.name}')

    @check()
    @todo.command(extras={"category":Category.TODO}, usage="lists")
    async def lists(self, ctx):
        """This shows a liat of todo lists you own or have access to"""
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
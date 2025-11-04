import discord
from discord.ext import commands, tasks
from datetime import datetime
import math, re
from typing import Union, Optional, List, Literal, cast

from killua.bot import BaseBot
from killua.static.enums import Category
from killua.static.constants import DB, URL_REGEX, editing, REPORT_CHANNEL
from killua.utils.checks import check, blcheck
from killua.utils.classes import TodoList, Todo, User, TodoListNotFound
from killua.utils.interactions import ConfirmButton, Button
from killua.utils.paginator import Paginator
from killua.utils.converters import TimeConverter


class TodoSystem(commands.Cog):

    def __init__(self, client: BaseBot):
        self.client = client
        self._init_menus()

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.check_todo_dues.is_running():
            self.check_todo_dues.start()

    def _init_menus(self) -> None:
        menus = []
        menus.append(
            discord.app_commands.ContextMenu(
                name="Add as todo",
                callback=self.client.callback_from_command(self.add, message=True),
                allowed_installs=discord.app_commands.AppInstallationType(
                    guild=True, user=True
                ),
                allowed_contexts=discord.app_commands.AppCommandContext(
                    guild=True, dm_channel=True, private_channel=True
                ),
            )
        )

        for menu in menus:
            self.client.tree.add_command(menu)

    @tasks.loop(seconds=60)
    async def check_todo_dues(self):
        """
        Checks if any todo's are due and sends a message to the owner if so
        """
        lists = [await TodoList.new(r["_id"]) async for r in DB.todo.find({})]

        for todo_list in lists:
            for todo in todo_list.todos:

                if (
                    "due_at" in todo
                    and todo["due_at"]
                    and todo["due_at"] < datetime.now()
                    and not todo["notified"]
                ):
                    to_be_notified = []
                    to_be_notified.append(self.client.get_user(todo["added_by"]))
                    to_be_notified.extend(
                        [self.client.get_user(u) for u in todo["assigned_to"]]
                    )

                    for user in to_be_notified:
                        if user:
                            try:
                                embed = discord.Embed.from_dict(
                                    {
                                        "title": "Todo due",
                                        "description": f"Your todo `{todo['todo']}` is due\nAdded <t:{int(todo['added_on'].timestamp())}:R>",
                                        "color": todo_list.color or 0x3E4A78,
                                        "footer": {
                                            "text": f"From todo list: {todo_list.name} (ID: {todo_list.id})",
                                            "icon_url": todo_list.thumbnail,
                                        },
                                    }
                                )
                                await cast(discord.User, user).send(embed=embed)
                            except discord.HTTPException:
                                continue  # If dms are closed we don't want to interrupt the loop

                    todo["notified"] = True
                    await todo_list.set_property("todos", todo_list.todos)

    @check_todo_dues.before_loop
    async def before_check_todo_dues(self):
        await self.client.wait_until_ready()

    async def _get_user(self, u: int) -> discord.User:
        """Gets a user from cache if possible, else makes an API request"""
        r = self.client.get_user(u)
        if not r:
            r = await self.client.fetch_user(u)
        return r

    async def _build_embed(
        self, todo_list: TodoList, page: int = None
    ) -> discord.Embed:
        """Creates an embed for a todo list page"""
        owner = await self._get_user(todo_list.owner)
        l = todo_list.todos
        desc = []

        if len(todo_list) > 10 and page:
            max_pages = math.ceil(len(l) / 10)
            final_todos = []

            if len(l) - page * 10 + 10 > 10:
                final_todos = l[page * 10 - 10 : -(len(l) - page * 10)]
            elif len(l) - page * 10 + 10 <= 10:
                final_todos = l[-(len(l) - page * 10 + 10) :]

        async def assigned_users(t: Todo) -> str:
            at: List[discord.User] = []
            for user in t.assigned_to:
                person = await self._get_user(user)
                at.append(person)
            return f"\n`Assigned to: {', '.join([x.display_name for x in at])}`"

        for n, t in enumerate(
            final_todos if page else l, page * 10 - 10 if page else 0
        ):
            t = await Todo.new(n + 1, todo_list.id)
            ma = f"\n`Marked as {t.marked}`" if t.marked else ""
            due = f"\nDue <t:{int(t.due_at.timestamp())}:R>" if t.due_at else ""
            desc.append(
                f"{n+1}) {t.todo}{ma}{due}{await assigned_users(t) if len(t.assigned_to) > 0 else ''}"
            )
        desc = "\n".join(desc) if len(desc) > 0 else "No todos"

        embed = discord.Embed.from_dict(
            {
                "title": f'To-do list "{todo_list.name}" (ID: {todo_list.id})',
                "description": f"{f'*Page {page}/{max_pages}*' if page else ''}\n{desc}",
                "color": todo_list.color or 0x3E4A78,
                "footer": {
                    "icon_url": str(owner.display_avatar.url),
                    "text": f"Owned by {owner.display_name}",
                },
            }
        )

        if todo_list.thumbnail:
            embed.set_thumbnail(url=todo_list.thumbnail)

        return embed

    async def todo_info_embed_generator(
        self, ctx: commands.Context, list_id: Union[int, str]
    ) -> discord.Message:
        """outsourcing big embed production 🛠"""
        try:
            todo_list = await TodoList.new(list_id)
        except TodoListNotFound:
            return await ctx.send("No todo list with this id exists")
        if not todo_list.has_view_permission(ctx.author.id):
            return await ctx.send(
                "You don't have permission to view infos about this list!"
            )

        await todo_list.add_view(ctx.author.id)

        owner = await self._get_user(todo_list.owner)
        created_at = (
            f"<t:{int(todo_list.created_at.timestamp())}:f>"
            if isinstance(todo_list.created_at, datetime)
            else todo_list.created_at
        )

        embed = discord.Embed.from_dict(
            {
                "title": f'Information for the todo list "{todo_list.name}" (ID: {todo_list.id})',
                "description": f"{todo_list.description if todo_list.description else ''}"
                + f"\n\n**Owner**: `{owner.display_name}`\n\n"
                + f"**Created on:** {created_at}\n\n"
                + f"**Custom ID**: `{todo_list.custom_id or 'No custom id'}`\n\n"
                + f"**Status**: `{todo_list.status}`\n\n"
                + f"**Editors**: `{', '.join([(await self._get_user(u)).display_name for u in todo_list.editor]) if len(todo_list.editor) > 0 else 'Nobody has editor perissions'}`\n"
                + f"**Viewers**: `{', '.join([(await self._get_user(u)).display_name for u in todo_list.viewer]) if len(todo_list.viewer) > 0 else 'Nobody has viewer permissions'}`\n\n"
                + f"**Todos**: `{len(todo_list)}/{todo_list.spots}`",
                "color": todo_list.color or 0x3E4A78,
                "footer": {
                    "text": f"{todo_list.views} view{'s' if todo_list.views != 1 else ''}"
                },
            }
        )
        if todo_list.thumbnail:
            embed.set_thumbnail(url=todo_list.thumbnail)

        return await self.client.send_message(ctx, embed=embed)

    async def single_todo_info_embed_generator(
        self, ctx: commands.Context, list_id: Union[int, str], task_id: int
    ) -> discord.Message:
        """outsourcing big embed production 🛠"""
        try:
            todo_list = await TodoList.new(list_id)
        except TodoListNotFound:
            return await ctx.send("No todo list with this id exists")
        try:
            todo_task = await Todo.new(task_id, list_id)
        except Exception:
            return await ctx.send("A todo task with that id is not on the list")

        if not todo_list.has_view_permission(ctx.author.id):
            return await ctx.send(
                "You don't have permission to view infos about this list!"
            )

        await todo_list.add_task_view(ctx.author.id, todo_task.position)

        adder = await self._get_user(todo_task.added_by)
        added_on = (
            f"<t:{int(todo_task.added_on.timestamp())}:f>"
            if isinstance(todo_task.added_on, datetime)
            else todo_task.added_on
        )

        mark_log = ("\n" + "-" * 20 + "\n").join(
            [
                f"Changed to: `{x['change']}`\nBy `{(await self._get_user(x['author'])).display_name}`\n"
                + (
                    f"<t:{int(x['date'].timestamp())}:f>"
                    if isinstance(x["date"], datetime)
                    else f"`{x['date']}`"
                )
                for x in todo_task.mark_log[:3]
            ]
        )

        mark_log = mark_log if len(mark_log) > 0 else "No recent changes"

        due = (
            f"**Due** <t:{int(todo_task.due_at.timestamp())}:R>\n"
            if todo_task.due_at
            else ""
        )
        embed = discord.Embed.from_dict(
            {
                "title": f"Information for the todo task {task_id}",
                "description": f"**Added by**: `{adder.display_name}`\n\n"
                + f"**Content**: {todo_task.todo}\n\n"
                + f"**Currently marked as**: `{todo_task.marked or 'Not currently marked'}`\n\n"
                + f"**Assigned to**: `{', '.join([(await self._get_user(u)).display_name for u in todo_task.assigned_to]) if len(todo_task.assigned_to) > 0 else 'unassigned'}`\n\n"
                + f"**Added on:** {added_on}\n{due}\n"
                + f"**Latest changes marks**:\n"
                + f"{mark_log}",
                "color": todo_list.color or 0x3E4A78,
                "footer": {
                    "text": f"{todo_task.views} view{'s' if todo_task.views != 1 else ''}"
                },
            }
        )
        if todo_list.thumbnail:
            embed.set_thumbnail(url=todo_list.thumbnail)
        return await self.client.send_message(ctx, embed=embed)

    async def _edit_check(self, ctx: commands.Context) -> Union[None, TodoList]:
        """A generic check before every command that edits a todo list property"""
        try:
            list_id = editing[ctx.author.id]
        except KeyError:
            await ctx.send(
                f"You have to be in the editor mode to use this command! Use `/todo edit <todo_list_id>`",
                allowed_mentions=discord.AllowedMentions.none(),
            )
        else:
            return await TodoList.new(list_id)

    @commands.hybrid_group(hidden=True, extras={"category": Category.TODO})
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    async def todo(self, _: commands.Context):
        """All commands relating to todo lists"""
        ...

    @check(10)
    @todo.command(extras={"category": Category.TODO, "id": 100}, usage="create")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(discord.AppCommandContext.all())
    @discord.app_commands.describe(
        name="The name of the todo list",
        status="Wether a todo list is publicly viewable or not",
        delete_when_done="Wether a todo should be deleted when marked done",
        custom_id="A custom id for the todo list- Premium only",
    )
    async def create(
        self,
        ctx: commands.Context,
        name: str,
        status: Literal["public", "private"],
        delete_when_done: Literal["yes", "no"],
        custom_id: Optional[str] = None,
    ):
        """Lets you create your todo list in an interactive menu"""

        user_todo_lists = [x async for x in DB.todo.find({"owner": ctx.author.id})]

        if len(user_todo_lists) == 5:
            return await ctx.send(
                "You can currently not own more than 5 todo lists", ephemeral=True
            )

        if len(name) > 30:
            return await ctx.send(
                "Name can't be longer than 20 characters", ephemeral=True
            )

        user = await User.new(ctx.author.id)
        if custom_id:
            if not user.is_premium:
                return await ctx.send(
                    "You need to be a premium user to use custom ids", ephemeral=True
                )

            if len(custom_id) > 20:
                return await ctx.send(
                    "Your custom id can have max 20 characters", ephemeral=True
                )

            if custom_id.lower().isdigit():
                return await ctx.send(
                    "Your custom id needs to contain at least one character that isn't an integer",
                    ephemeral=True,
                )

            try:
                await TodoList.new(custom_id.lower())
            except TodoListNotFound:
                pass
            else:
                return await ctx.send("This custom id is already taken", ephemeral=True)

        l = await TodoList.create(
            owner=ctx.author.id,
            title=name,
            status=status,
            done_delete=delete_when_done == "yes",
            custom_id=custom_id,
        )
        await ctx.send(
            f"Created the todo list with the name {name}. You can look at it and edit it through the id `{l.id}`"
            + (f" or through your custom id {custom_id}" if custom_id else ""),
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @check()
    @todo.command(
        extras={"category": Category.TODO, "id": 101}, usage="view <list_id(optional)>"
    )
    @discord.app_commands.describe(todo_id="The id of the todo list you want to view")
    async def view(self, ctx: commands.Context, todo_id: str = None):
        """Allows you to view what is on any todo list- provided you have the permissions"""
        if todo_id is None:
            todo_list = await self._edit_check(ctx)
            if todo_list is None:
                return
        else:
            try:
                todo_list = await TodoList.new(todo_id)
            except TodoListNotFound:
                return await ctx.send("No todo list with specified ID found")

        if not todo_list.has_view_permission(ctx.author.id):
            return await ctx.send(
                "This is a private list you don't have the permission to view"
            )
        await todo_list.add_view(ctx.author.id)

        if len(todo_list) <= 10:
            return await ctx.send(embed=await self._build_embed(todo_list))

        async def make_embed(page, _, pages):
            return await self._build_embed(pages, page)

        await Paginator(
            ctx, todo_list, max_pages=math.ceil(len(todo_list) / 10), func=make_embed
        ).start()

    @check()
    @todo.command(extras={"category": Category.TODO, "id": 102}, usage="clear")
    async def clear(self, ctx: commands.Context):
        """Clears all todos from a todo list"""
        try:
            list_id = editing[ctx.author.id]
        except KeyError:
            return await ctx.send(
                "You have to be in the editor mode to use this command without providing an id! Use `/todo edit <todo_list_id>`"
            )

        todo_list = await TodoList.new(list_id)
        if not todo_list.has_edit_permission(ctx.author.id):
            return await ctx.send(
                "You have to be added as an editor to this list to use this command"
            )
        await todo_list.clear()
        await ctx.send("Done! Cleared all your todos")

    @check(1)
    @todo.command(
        extras={"category": Category.TODO, "id": 103},
        usage="info <list_id/task_id> <task_id(if list_id provided)>",
    )
    @discord.app_commands.describe(
        todo_or_task_id="The task or todo list you want information about",
        task_id="The id of the tasks you want information about",
    )
    async def info(
        self, ctx: commands.Context, todo_or_task_id: str = None, task_id: int = None
    ):
        """This gives you info about either a todo task or list"""
        if task_id is None:
            if todo_or_task_id is None:
                todo_list = await self._edit_check(ctx)
                if not todo_list:
                    return
                return await self.todo_info_embed_generator(ctx, todo_list.id)
            try:
                list_id = editing[ctx.author.id]
            except KeyError:
                return await self.todo_info_embed_generator(ctx, todo_or_task_id)
            if not todo_or_task_id.isdigit():
                return await self.todo_info_embed_generator(ctx, todo_or_task_id)
            return await self.single_todo_info_embed_generator(
                ctx, list_id, int(todo_or_task_id)
            )
        elif task_id:
            return await self.single_todo_info_embed_generator(
                ctx, todo_or_task_id, int(task_id)
            )

    @check()
    @todo.command(extras={"category": Category.TODO, "id": 104}, usage="edit <list_id>")
    @discord.app_commands.describe(list_id="The id of the todo list you want to edit")
    async def edit(self, ctx: commands.Context, list_id: str):
        """The command with which you can change stuff on your todo list"""
        if ctx.author.id in editing and editing[ctx.author.id] == list_id:
            return await ctx.send("You are already editing this list!")
        try:
            todo_list = await TodoList.new(list_id)
        except TodoListNotFound:
            return await ctx.send("No todo list with this id exists")

        if not todo_list.has_edit_permission(ctx.author.id):
            return await ctx.send(
                "You do not have the permission to edit this todo list"
            )

        editing[ctx.author.id] = todo_list.id
        await ctx.send(
            f"You are now in editor mode for todo list '{todo_list.name}'",
            allowed_mentions=discord.AllowedMentions.none(),
        )

    async def _update_name(
        self, todo_list: TodoList, new_name: str
    ) -> Optional[str]:
        """Updates the name of a todo list"""
        if len(new_name) > 30:
            return "Name can't be longer than 30 characters"
        await todo_list.set_property("title", new_name)
        return None

    async def _update_custom_id(
        self, todo_list: TodoList, new_custom_id: str, user: User
    ) -> Optional[str]:
        """Updates the custom id of a todo list"""
        if not user.is_premium:
            return "You need to be a premium user to use custom ids"

        if len(new_custom_id) > 20:
            return "Your custom id can have max 20 characters"

        if new_custom_id.lower().isdigit():
            return "Your custom id needs to contain at least one character that isn't an integer"

        try:
            await TodoList.new(new_custom_id.lower())
        except TodoListNotFound:
            pass
        else:
            return "This custom id is already taken"

        await todo_list.set_property("custom_id", new_custom_id.lower())
        return None # None means success
    
    async def _update_color(
        self, todo_list: TodoList, color: str
    ) -> Optional[str]:
        """Updates the color of a todo list"""
        if not todo_list.has_addon("color"):
            return "You can't customize this property, you need to buy it in the shop"
        if color.lower() == "none":
            await todo_list.set_property("color", None)
            return None
        else:
            try:
                await todo_list.set_property("color", int(color, 16))
                return None
            except ValueError:
                return "Color needs to be a valid hexadecimal number"
    
    async def _update_thumbnail(
        self, todo_list: TodoList, thumbnail: str
    ) -> Optional[str]:
        """Updates the thumbnail of a todo list"""
        if not todo_list.has_addon("thumbnail"):
            return "You can't customize this property, you need to buy it in the shop"
        search_url = re.search(URL_REGEX, thumbnail)

        if search_url:
            image = re.search(r"png|jpg|gif|svg", thumbnail)
        else:
            return "You didn't provide a valid url with an image! Please make sure your url is valid"

        if image:
            await todo_list.set_property("thumbnail", thumbnail)
            return None
        else:
            return "You didn't provide a valid url with an image! Please make sure your url is valid"
    
    async def _update_description(
        self, todo_list: TodoList, description: str
    ) -> Optional[str]:
        """Updates the description of a todo list"""
        if not todo_list.has_addon("description"):
            return "You can't customize this property, you need to buy it in the shop"
        if len(description) > 200:
            return "Description can't be longer than 200 characters"
        await todo_list.set_property("description", description)
        return None

    @check()
    @todo.command(
        extras={"category": Category.TODO, "id": 105}, usage="update <settings>"
    )
    @discord.app_commands.describe(
        name="The name of the todo list you want to change",
        status="The status of the todo list you want to change",
        delete_when_done="Whether you want to delete a todo when it's done",
        custom_id="The custom id of the todo list you want to change",
        color="The color of the todo list you want to change",
        thumbnail="The thumbnail of the todo list you want to change",
        description="The description of the todo list you want to change",
    )
    async def update(
        self,
        ctx: commands.Context,
        name: Optional[str] = None,
        status: Optional[Literal["private", "public"]] = None,
        delete_when_done: Optional[Literal["yes", "no"]] = None,
        custom_id: Optional[str] = None,
        color: Optional[str] = None,
        thumbnail: Optional[str] = None,
        description: Optional[str] = None,
    ):
        """Update your todo list with this command (Only in editor mode)"""

        res = await self._edit_check(ctx)
        if not res:
            return

        updated = []

        user = await User.new(ctx.author.id)
        if name:
            error = await self._update_name(res, name)
            if error:
                return await ctx.send(error, ephemeral=True)
            updated.append("name")

        if status:
            await res.set_property("status", status)
            updated.append("status")

        if delete_when_done:
            await res.set_property("delete_when_done", delete_when_done == "yes")
            updated.append("delete_when_done")

        if custom_id:
            error = await self._update_custom_id(res, custom_id, user)
            if error:
                return await ctx.send(error, ephemeral=True)
            updated.append("custom_id")

        if color:
            error = await self._update_color(res, color)
            if error:
                return await ctx.send(error, ephemeral=True)
            updated.append("color")

        if thumbnail:
            error = await self._update_thumbnail(res, thumbnail)
            if error:
                return await ctx.send(error, ephemeral=True)
            updated.append("thumbnail")

        if description:
            error = await self._update_description(res, description)
            if error:
                return await ctx.send(error, ephemeral=True)
            updated.append("description")

        await ctx.send(
            f"Successfully updated {', '.join(updated)} of your todo list!",
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @check()
    @todo.command(
        extras={"category": Category.TODO, "id": 106}, usage="remove <task_id>"
    )
    @discord.app_commands.describe(todo_numbers="The todo tasks you want to delete")
    async def remove(self, ctx: commands.Context, todo_numbers: commands.Greedy[int]):
        """Remove a todo with this command. YAY, GETTING THINGS DONE!! (Only in editor mode)"""
        todo_list = await self._edit_check(ctx)
        if todo_list is None:
            return

        if len(todo_numbers) == 0:
            return await ctx.send("No valid numbers provided")

        todos = todo_list.todos

        failed = []
        for n in todo_numbers:
            if not todo_list.has_todo(n):
                failed.append(n)
                continue
            todos.pop(n - 1)
        if len(todo_numbers) == len(failed):
            return await ctx.send("All inputs are invalid task ids. Please try again.")

        todo_list.set_property("todos", todos)
        return await ctx.send(
            f"You removed todo number{'s' if len(todo_numbers) > 1 else ''} {', '.join([str(x) for x in todo_numbers])} successfully"
            + (
                ". Failed to remove the following numbers because they are invalid: "
                + ", ".join([str(x) for x in failed])
                if len(failed) > 0
                else ""
            ),
            allowed_mentions=discord.AllowedMentions.none(),
        )

    async def marked_as_autocomplete(
        self, _: discord.Interaction, current: str
    ) -> List[discord.app_commands.Choice[str]]:
        return [
            discord.app_commands.Choice(name=x, value=x)
            for x in ["done", "in progress", "high priority", "low priority"]
            if x.startswith(current) or current in x
        ]

    @check()
    @todo.command(
        extras={"category": Category.TODO, "id": 107}, usage="mark <task_id> <text>"
    )
    @discord.app_commands.describe(
        todo_number="The todo task you want to mark",
        marked_as="What you want to make the todo task as",
    )
    @discord.app_commands.autocomplete(marked_as=marked_as_autocomplete)
    async def mark(self, ctx: commands.Context, todo_number: int, *, marked_as: str):
        """Mark a todo with a comment like `done` or `too lazy` (Only in editor mode)"""
        todo_list = await self._edit_check(ctx)
        if todo_list is None:
            return

        todos = todo_list.todos

        if not todo_list.has_todo(todo_number):
            return await ctx.send(
                f"You don't have a number {todo_number} on your current todo list",
                allowed_mentions=discord.AllowedMentions.none(),
            )

        if marked_as.lower() == "done" and todo_list.delete_done is True:
            todos.pop(todo_number - 1)
            await todo_list.set_property("todos", todos)
            return await ctx.send(
                f"Marked to-do number {todo_number} as done and deleted it per default"
            )
        elif marked_as.lower() == "-r" or marked_as.lower() == "-rm":
            todos[todo_number - 1]["marked"] = None
            mark_log = {
                "author": ctx.author.id,
                "change": "REMOVED MARK",
                "date": datetime.now(),
            }
            cast(list, todos[todo_number - 1]["mark_log"]).append(mark_log)
            await todo_list.set_property("todos", todos)
            return await ctx.send(
                f"Removed to-do number {todo_number} successfully!",
                allowed_mentions=discord.AllowedMentions.none(),
            )
        else:
            todos[todo_number - 1]["marked"] = marked_as
            mark_log = {
                "author": ctx.author.id,
                "change": marked_as,
                "date": datetime.now(),
            }
            cast(list, todos[todo_number - 1]["mark_log"]).append(mark_log)
            await todo_list.set_property("todos", todos)
            return await ctx.send(
                f"Marked to-do number {todo_number} as `{marked_as}`!",
                allowed_mentions=discord.AllowedMentions.none(),
            )

    async def due_in_autocomplete(
        self, _: discord.Interaction, current: str
    ) -> List[discord.app_commands.Choice[TimeConverter]]:
        """
        Autocomplete for the due in parameter
        """
        times = ["1m", "5m", "10m", "30m", "1h", "12h", "1d", "7d"]
        return [
                discord.app_commands.Choice(name=opt, value=opt)
                for opt in times
                if opt.lower().startswith(current.lower())
            ]

    @check()
    @todo.command(extras={"category": Category.TODO, "id": 108}, usage="add <text>")
    @discord.app_commands.describe(text="What to add to the todo list")
    @discord.app_commands.autocomplete(due_in=due_in_autocomplete)
    async def add(
        self,
        ctx: commands.Context,
        *,
        text: str,
        due_in: Optional[TimeConverter] = None,
    ):
        """Add a todo to your list, *yay, more work* (Only in editor mode)"""
        todo_list = await self._edit_check(ctx)
        if todo_list is None:
            return
        if len(text) > 100:
            return await ctx.send(
                "Your todo can't have more than 100 characters", ephemeral=True
            )

        if len(todo_list.todos) >= todo_list.spots:
            return await ctx.send(
                f"You don't have enough spots for that! Buy spots with `/todo buy space`. You can currently only have up to {todo_list.spots} spots in this list",
                allowed_mentions=discord.AllowedMentions.none(),
                ephemeral=True,
            )

        if due_in and not todo_list.has_addon("due_in"):
            return await ctx.send(
                "You cannot assign a time to a todo yet, you need to buy it in the shop",
                ephemeral=True,
            )

        todos = todo_list.todos
        todos.append(
            {
                "todo": text,
                "marked": None,
                "added_by": ctx.author.id,
                "added_on": datetime.now(),
                "views": 0,
                "assigned_to": [],
                "mark_log": [],
                "due_at": (datetime.now() + due_in) if due_in else None,
                "notified": False if due_in else None,
            }
        )

        await todo_list.set_property("todos", todos)
        return await ctx.send(
            f'Great! Added "{text}" to your todo list!'
            + (
                f" I'll remind you and everyone assigned <t:{int((datetime.now() + due_in).timestamp())}:R>"
                if due_in
                else ""
            ),
            allowed_mentions=discord.AllowedMentions.none(),
            ephemeral=hasattr(ctx, "invoked_by_context_menu"),
        )

    @check(20)
    @todo.command(extras={"category": Category.TODO, "id": 109}, usage="kick <user>")
    @discord.app_commands.describe(user="The user to kick from the todo list")
    async def kick(self, ctx: commands.Context, user: discord.User):
        """Take all permissions from someone from your todo list (Only in editor mode)"""
        todo_list = await self._edit_check(ctx)
        if todo_list is None:
            return

        if ctx.author.id != todo_list.owner:
            return await ctx.send(
                "You have to own the todo list to remove permissions from users"
            )

        if not (user.id in todo_list.viewer or user.id in todo_list.editor):
            return await ctx.send(
                "The user you specified doesn't have permission to view or edit the todo list, you can't take permissions you never granted"
            )

        if user.id in todo_list.editor:
            todo_list.kick_editor(user.id)
            await ctx.send(
                f"You have successfully taken the editor permission from {user}",
                allowed_mentions=discord.AllowedMentions.none(),
            )

        if user.id in todo_list.viewer:
            todo_list.kick_viewer(user.id)
            await ctx.send(
                f"You have successfully taken the viewer permission from {user}",
                allowed_mentions=discord.AllowedMentions.none(),
            )

    @check()
    @todo.command(extras={"category": Category.TODO, "id": 110}, usage="exit")
    async def exit(self, ctx: commands.Context):
        """Exit editing mode with this. (Only in editor mode)"""
        # I"ve never used it because it is pointless because my code is so good you realistically never need to be out of editing mode but it is here so use it
        todo_list = await self._edit_check(ctx)
        if todo_list is None:
            return

        editing.pop(ctx.author.id, None)
        return await ctx.send("Exiting editing mode!")

    @check(20)
    @todo.command(
        extras={"category": Category.TODO, "id": 111},
        usage="invite <user> <editor/viewer>",
    )
    @discord.app_commands.describe(
        user="The user to give permissions to", role="The role to give the user"
    )
    async def invite(
        self,
        ctx: commands.Context,
        user: discord.User,
        role: Literal["editor", "viewer"],
    ):
        """Wanna let your friend add more todos for you? Invite them! (Only in editor mode)"""
        todo_list = await self._edit_check(ctx)
        if todo_list is None:
            return

        if user.id == ctx.author.id:
            return await ctx.send(
                "You are already owner, you don't need to invite yourself"
            )

        if user.bot:
            return await ctx.send("You can't invite a bot to your todo list")

        if await blcheck(user.id):
            return await ctx.send("You can't invite a blacklisted user")

        if role == "viewer" and todo_list.status == "public":
            return await ctx.send(
                "You can't add viewers to a public todo list. Everyone has viewing permissions on this list",
                ephemeral=True,
            )

        if user.id in getattr(todo_list, role):
            return await ctx.send("The specified user already has that role!")

        if role == "viewer" and user.id in todo_list.editor:
            return await ctx.send(
                "User already has editor permissions, you can't also add viewer permission",
                ephemeral=True,
            )

        if await self.client._dm_check(user) is False:
            return await ctx.send(
                "The user you are trying to invite has their dms closed, they need to open them to accept the invitation"
            )

        # embed = discord.Embed.from_dict(
        #     {
        #         "title": f"You were invited to to-do list {todo_list.name} (ID: {todo_list.id})",
        #         "description": f'{ctx.author} invited you to be {role} in their to-do list. To accept, click "confirm", to deny click "cancel". If this invitation was inappropriate, click "report"',
        #         "color": todo_list.color or 0x3E4A78,
        #         "footer": {
        #             "icon_url": str(ctx.author.avatar.url),
        #             "text": f"Requested by {ctx.author}",
        #         },
        #     }
        # )

        try:
            view = ConfirmButton(
                user.id,
                f"# You were invited to to-do list {todo_list.name} (ID: {todo_list.id})\n"
                + f'{ctx.author} invited you to be {role} in their to-do list. To accept, click "confirm", to deny click "cancel". If this invitation was inappropriate, click "report"',
                timeout=60 * 60 * 24,
            )
            view._children[0]._children[1].add_item(
                Button(
                    label="report", custom_id="report", style=discord.ButtonStyle.red
                )
            )
            msg = await user.send(view=view)
            await ctx.send(
                "Successfully send the invitation to the specified user! They have 24 hours to accept or deny"
            )
        except discord.Forbidden:
            return await ctx.send(
                "Failed to send the user a dm. Make sure they are on a guild Killua is on and has their dms open"
            )

        await view.wait()
        await view.disable(msg)

        if not view.value:
            if view.timed_out:
                await user.send("Timed out!")
                return await ctx.author.send(
                    f"{user} has not responded to your invitation in 24 hours so the invitation went invalid"
                )
            else:
                await user.send("Successfully denied invitation")
                return await ctx.author.send(
                    f"{user} has denied your invitation the todo list `{todo_list.name}`",
                    allowed_mentions=discord.AllowedMentions.none(),
                )

        elif view.value == "report":
            channel = self.client.get_channel(REPORT_CHANNEL)
            embed = discord.Embed.from_dict(
                {
                    "title": f"Report from {user}",
                    "fields": [
                        {
                            "name": "Guild",
                            "value": f"ID: {ctx.guild.id}\nName: {ctx.guild.name}",
                        },
                        {
                            "name": "Reported user",
                            "value": f"ID: {ctx.author.id}\nName: {ctx.author.display_name}",
                        },
                        {
                            "name": "Todo list",
                            "value": f"ID: {todo_list.id}\nName: {todo_list.name}",
                        },
                    ],
                    "color": 0xFF0000,
                    "footer": {"text": user.id, "icon_url": str(user.avatar.url)},
                    "thumbnail": {"url": str(ctx.author.avatar.url)},
                }
            )
            await channel.send(embed=embed)
            await ctx.author.send(f"{user} reported your invite to your todo list")
            return await user.send(f"Successfully reported {ctx.author.display_name}!")

        if role == "viewer":
            todo_list.add_viewer(user.id)

        if role == "editor":
            if user.id in todo_list.viewer:
                todo_list.kick_viewer(
                    user.id
                )  # handled like a promotion and exchanges viewer perms for edit perms
            todo_list.add_editor(user.id)

        await user.send(
            f"Success! You have now {role} permissions in the todo list `{todo_list.name}`",
            allowed_mentions=discord.AllowedMentions.none(),
        )
        return await ctx.author.send(
            f"{user} accepted your invitation to your todo list `{todo_list.name}`!",
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @check()
    @todo.command(
        extras={"category": Category.TODO, "id": 112}, usage="assign <task_id> <user>"
    )
    @discord.app_commands.describe(
        todo_number="What todo to assign someone to", user="Who to assign the todo to"
    )
    async def assign(self, ctx: commands.Context, todo_number: int, user: discord.User):
        """Assign someone a todo task with this. If already asigned they are removed. (Only in editor mode)"""
        todo_list = await self._edit_check(ctx)
        if todo_list is None:
            return

        if user.id != todo_list.owner and user.id not in todo_list.editor:
            return await ctx.send(
                "You can only assign people todos who have permission to edit this todo list"
            )

        todos = todo_list.todos

        if not todo_list.has_todo(todo_number):
            return await ctx.send(
                f"You don't have a number {todo_number} on your current todo list"
            )

        if user.id in todos[todo_number - 1]["assigned_to"]:
            if ctx.author != user:
                embed = discord.Embed.from_dict(
                    {
                        "title": f"Removed assignment to todo on list {todo_list.name} (ID: {todo_list.id})",
                        "description": f"{ctx.author} removed assignment you to the todo {todos[todo_number-1]['todo']}",
                        "color": todo_list.color or 0x3E4A78,
                        "footer": {
                            "icon_url": str(ctx.author.avatar.url),
                            "text": f"Requested by {ctx.author}",
                        },
                    }
                )
                try:
                    await user.send(embed=embed)
                except discord.Forbidden:
                    pass
            todos[todo_number - 1]["assigned_to"].remove(user.id)
            todo_list.set_property("todos", todos)
            return await ctx.send(
                f"Successfully removed assignment of todo task {todo_number} of {user}"
            )

        todos[todo_number - 1]["assigned_to"].append(user.id)
        todo_list.set_property("todos", todos)

        if ctx.author != user:
            embed = discord.Embed.from_dict(
                {
                    "title": f"Assigned to todo on list {todo_list.name} (ID: {todo_list.id})",
                    "description": f"{ctx.author} assigned you to the todo {todos[todo_number-1]['todo']}",
                    "color": todo_list.color or 0x3E4A78,
                    "footer": {
                        "icon_url": str(ctx.author.avatar.url),
                        "text": f"Requested by {ctx.author}",
                    },
                }
            )
            try:
                await user.send(embed=embed)
            except discord.Forbidden:
                pass
        return await ctx.send(
            f"Successfully assigned the task with number {todo_number} to `{user}`",
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @check()
    @todo.command(
        extras={"category": Category.TODO, "id": 113},
        usage="reorder <task_id> <position>",
    )
    @discord.app_commands.describe(
        position="The position the todo is currently at",
        new_position="Where to put the todo",
    )
    async def reorder(self, ctx: commands.Context, position: int, new_position: int):
        """Reorder a todo task with this. (Only in editor mode)"""
        todo_list = await self._edit_check(ctx)
        if todo_list is None:
            return

        if (
            ctx.author.id != todo_list.owner
            and ctx.author.id not in todo_list.editor
        ):
            return await ctx.send(
                "You can only reorder tasks who have permission to edit this todo list"
            )

        if not todo_list.has_todo(position):
            return await ctx.send(
                f"You don't have a number {position} on your current todo list"
            )

        if new_position > len(todo_list.todos) or new_position < 1:
            return await ctx.send(
                f"You can't reorder todo task {position} to position {new_position} because it's out of range"
            )

        todo_list.todos.insert(new_position - 1, todo_list.todos.pop(position - 1))
        todo_list.set_property("todos", todo_list.todos)
        return await ctx.send(
            f"Successfully reordered todo task {position} to position {new_position}"
        )

    @check()
    @todo.command(
        extras={"category": Category.TODO, "id": 114}, usage="delete <list_id>"
    )
    @discord.app_commands.describe(todo_id="The todo list to delete")
    async def delete(self, ctx: commands.Context, todo_id: str):
        """Use this command to delete your todo list. Make sure to say goodbye a last time"""
        try:
            todo_list = await TodoList.new(todo_id)
        except TodoListNotFound:
            return await ctx.send("No todo list with this id exists")

        if ctx.author.id != todo_list.owner:
            return await ctx.send("Only the owner of a todo list can delete it")

        await todo_list.delete()
        return await ctx.send(
            f"Done! Deleted todo list {todo_list.name}",
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @check()
    @todo.command(extras={"category": Category.TODO, "id": 115}, usage="lists")
    async def lists(self, ctx: commands.Context):
        """This shows a list of todo lists you own or have access to"""
        lists_owning = DB.todo.find({"owner": ctx.author.id})
        lists_viewing = DB.todo.find({"viewer": ctx.author.id})
        lists_editing = DB.todo.find({"editor": ctx.author.id})

        l_o = "\n".join(
            [
                f"{l['name']} (id: {l['_id']}/{l['custom_id'] or 'No custom id'})"
                async for l in lists_owning
            ]
        )
        l_v = "\n".join(
            [
                f"{l['name']} (id: {l['_id']}/{l['custom_id'] or 'No custom id'})"
                async for l in lists_viewing
            ]
        )
        l_e = "\n".join(
            [
                f"{l['name']} (id: {l['_id']}/{l['custom_id'] or 'No custom id'})"
                async for l in lists_editing
            ]
        )

        embed = discord.Embed.from_dict(
            {
                "title": "Your todo lists and permissions",
                "description": f"**todo lists you own**\n\n{l_o or 'No todo lists'}\n\n**todo lists you have viewing permissions**\n\n{l_v or 'No todo lists'}\n\n**todo lists you have editing permissions**\n\n{l_e or 'No todo lists'}",
                "color": 0x3E4A78,
                "footer": {
                    "icon_url": str(ctx.author.avatar.url),
                    "text": f"Requested by {ctx.author}",
                },
            }
        )
        return await ctx.send(embed=embed)


Cog = TodoSystem

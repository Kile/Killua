from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, patch

from ..types import DiscordMember
from ...utils.classes import User
from ..testing import Testing, test
from ...cogs.todo import TodoSystem
from ...static.constants import DB, editing
from ...utils.classes.todo import TodoList

from ..harnesses import embed_footer_page, patch_user_confirm_dm, press_paginator_button


def _clear_todo_state() -> None:
    """Reset TodoList caches, editing dict, and the todo DB collection."""
    TodoList.cache.clear()
    TodoList.custom_id_cache.clear()
    editing.clear()
    DB.todo.db["todo"] = []


async def _make_list(owner_id: int, enter_editing=True, **overrides) -> TodoList:
    """Helper to create a todo list and optionally enter editor mode."""
    defaults = dict(
        owner=owner_id,
        title="Test list",
        status="public",
        done_delete=False,
    )
    defaults.update(overrides)
    todo_list = await TodoList.create(**defaults)
    if enter_editing:
        editing[owner_id] = todo_list.id
    return todo_list


class TestingTodo(Testing):
    requires_command = True

    _menus_registered = False

    def __init__(self):
        if not TestingTodo._menus_registered:
            TestingTodo._menus_registered = True
        else:
            TodoSystem._init_menus = lambda self: None
        super().__init__(cog=TodoSystem)


class Create(TestingTodo):

    def __init__(self):
        super().__init__()

    @test
    async def create_basic(self) -> None:
        _clear_todo_state()
        await self.command(
            self.cog, self.base_context,
            name="My list", status="public", delete_when_done="no",
        )

        assert "Created the todo list with the name My list" in (
            self.base_context.result.message.content
        ), self.base_context.result.message.content

    @test
    async def name_too_long(self) -> None:
        _clear_todo_state()
        await self.command(
            self.cog, self.base_context,
            name="A" * 31, status="public", delete_when_done="no",
        )

        assert (
            self.base_context.result.message.content
            == "Name can't be longer than 20 characters"
        ), self.base_context.result.message.content

    @test
    async def max_five_lists(self) -> None:
        _clear_todo_state()
        for i in range(5):
            await TodoList.create(
                owner=self.base_author.id,
                title=f"list{i}",
                status="public",
                done_delete=False,
            )

        await self.command(
            self.cog, self.base_context,
            name="sixth", status="public", delete_when_done="no",
        )

        assert (
            self.base_context.result.message.content
            == "You can currently not own more than 5 todo lists"
        ), self.base_context.result.message.content

    @test
    async def custom_id_not_premium(self) -> None:
        _clear_todo_state()
        await self.command(
            self.cog, self.base_context,
            name="Test", status="public", delete_when_done="no",
            custom_id="mylist",
        )

        assert (
            self.base_context.result.message.content
            == "You need to be a premium user to use custom ids"
        ), self.base_context.result.message.content

    @test
    async def custom_id_all_digits(self) -> None:
        _clear_todo_state()
        user = await User.new(self.base_author.id)
        user._badges.append("tier_one")

        await self.command(
            self.cog, self.base_context,
            name="Test", status="public", delete_when_done="no",
            custom_id="12345",
        )

        assert (
            self.base_context.result.message.content
            == "Your custom id needs to contain at least one character that isn't an integer"
        ), self.base_context.result.message.content
        user._badges.remove("tier_one")

    @test
    async def custom_id_too_long(self) -> None:
        _clear_todo_state()
        user = await User.new(self.base_author.id)
        user._badges.append("tier_one")

        await self.command(
            self.cog, self.base_context,
            name="Test", status="public", delete_when_done="no",
            custom_id="a" * 21,
        )

        assert (
            self.base_context.result.message.content
            == "Your custom id can have max 20 characters"
        ), self.base_context.result.message.content
        user._badges.remove("tier_one")


class Edit(TestingTodo):

    def __init__(self):
        super().__init__()

    @test
    async def enter_edit_mode(self) -> None:
        _clear_todo_state()
        todo_list = await TodoList.create(
            owner=self.base_author.id,
            title="Editable",
            status="public",
            done_delete=False,
        )

        await self.command(self.cog, self.base_context, list_id=str(todo_list.id))

        assert (
            self.base_context.result.message.content
            == "You are now in editor mode for todo list 'Editable'"
        ), self.base_context.result.message.content
        assert editing[self.base_author.id] == todo_list.id

    @test
    async def edit_nonexistent_list(self) -> None:
        _clear_todo_state()
        await self.command(self.cog, self.base_context, list_id="999999")

        assert (
            self.base_context.result.message.content
            == "No todo list with this id exists"
        ), self.base_context.result.message.content

    @test
    async def no_edit_permission(self) -> None:
        _clear_todo_state()
        todo_list = await TodoList.create(
            owner=99999,
            title="Private",
            status="private",
            done_delete=False,
        )

        await self.command(self.cog, self.base_context, list_id=str(todo_list.id))

        assert (
            self.base_context.result.message.content
            == "You do not have the permission to edit this todo list"
        ), self.base_context.result.message.content


class Exit(TestingTodo):

    def __init__(self):
        super().__init__()

    @test
    async def exit_edit_mode(self) -> None:
        _clear_todo_state()
        await _make_list(self.base_author.id)

        await self.command(self.cog, self.base_context)

        assert (
            self.base_context.result.message.content == "Exiting editing mode!"
        ), self.base_context.result.message.content
        assert self.base_author.id not in editing

    @test
    async def exit_without_editing(self) -> None:
        _clear_todo_state()
        await self.command(self.cog, self.base_context)

        assert "editor mode" in self.base_context.result.message.content, (
            self.base_context.result.message.content
        )


class Add(TestingTodo):

    def __init__(self):
        super().__init__()

    @test
    async def add_todo(self) -> None:
        _clear_todo_state()
        todo_list = await _make_list(self.base_author.id)

        await self.command(self.cog, self.base_context, text="Buy milk")

        assert (
            self.base_context.result.message.content
            == 'Great! Added "Buy milk" to your todo list!'
        ), self.base_context.result.message.content
        assert any(
            t["todo"] == "Buy milk" for t in todo_list.todos
        ), todo_list.todos

    @test
    async def add_without_editing(self) -> None:
        _clear_todo_state()
        await self.command(self.cog, self.base_context, text="Test")

        assert "editor mode" in self.base_context.result.message.content, (
            self.base_context.result.message.content
        )

    @test
    async def add_text_too_long(self) -> None:
        _clear_todo_state()
        await _make_list(self.base_author.id)

        await self.command(self.cog, self.base_context, text="A" * 101)

        assert (
            self.base_context.result.message.content
            == "Your todo can't have more than 100 characters"
        ), self.base_context.result.message.content

    @test
    async def add_when_spots_full(self) -> None:
        _clear_todo_state()
        todo_list = await _make_list(self.base_author.id)
        for i in range(9):
            todo_list.todos.append({
                "todo": f"todo {i+2}", "marked": None, "added_by": self.base_author.id,
                "added_on": datetime.now(), "views": 0, "assigned_to": [],
                "mark_log": [], "due_at": None, "notified": None,
            })

        await self.command(self.cog, self.base_context, text="Overflow")

        assert "don't have enough spots" in self.base_context.result.message.content, (
            self.base_context.result.message.content
        )


class Remove(TestingTodo):

    def __init__(self):
        super().__init__()

    @test
    async def remove_todo(self) -> None:
        _clear_todo_state()
        await _make_list(self.base_author.id)

        await self.command(self.cog, self.base_context, todo_numbers=[1])

        assert "removed todo number 1 successfully" in (
            self.base_context.result.message.content
        ), self.base_context.result.message.content

    @test
    async def remove_invalid_number(self) -> None:
        _clear_todo_state()
        await _make_list(self.base_author.id)

        await self.command(self.cog, self.base_context, todo_numbers=[99])

        assert (
            self.base_context.result.message.content
            == "All inputs are invalid task ids. Please try again."
        ), self.base_context.result.message.content

    @test
    async def remove_no_numbers(self) -> None:
        _clear_todo_state()
        await _make_list(self.base_author.id)

        await self.command(self.cog, self.base_context, todo_numbers=[])

        assert (
            self.base_context.result.message.content == "No valid numbers provided"
        ), self.base_context.result.message.content

    @test
    async def remove_without_editing(self) -> None:
        _clear_todo_state()
        await self.command(self.cog, self.base_context, todo_numbers=[1])

        assert "editor mode" in self.base_context.result.message.content, (
            self.base_context.result.message.content
        )


class Mark(TestingTodo):

    def __init__(self):
        super().__init__()

    @test
    async def mark_as_text(self) -> None:
        _clear_todo_state()
        await _make_list(self.base_author.id)

        await self.command(self.cog, self.base_context, todo_number=1, marked_as="in progress")

        assert (
            self.base_context.result.message.content
            == "Marked to-do number 1 as `in progress`!"
        ), self.base_context.result.message.content

    @test
    async def mark_as_done_with_delete(self) -> None:
        _clear_todo_state()
        await _make_list(self.base_author.id, done_delete=True)

        await self.command(self.cog, self.base_context, todo_number=1, marked_as="done")

        assert (
            self.base_context.result.message.content
            == "Marked to-do number 1 as done and deleted it per default"
        ), self.base_context.result.message.content

    @test
    async def remove_mark(self) -> None:
        _clear_todo_state()
        await _make_list(self.base_author.id)

        await self.command(self.cog, self.base_context, todo_number=1, marked_as="-r")

        assert (
            self.base_context.result.message.content
            == "Removed to-do number 1 successfully!"
        ), self.base_context.result.message.content

    @test
    async def mark_invalid_number(self) -> None:
        _clear_todo_state()
        await _make_list(self.base_author.id)

        await self.command(self.cog, self.base_context, todo_number=99, marked_as="done")

        assert "don't have a number 99" in self.base_context.result.message.content, (
            self.base_context.result.message.content
        )

    @test
    async def mark_without_editing(self) -> None:
        _clear_todo_state()
        await self.command(self.cog, self.base_context, todo_number=1, marked_as="done")

        assert "editor mode" in self.base_context.result.message.content, (
            self.base_context.result.message.content
        )


class Clear(TestingTodo):

    def __init__(self):
        super().__init__()

    @test
    async def clear_todos(self) -> None:
        _clear_todo_state()
        todo_list = await _make_list(self.base_author.id)

        await self.command(self.cog, self.base_context)

        assert (
            self.base_context.result.message.content == "Done! Cleared all your todos"
        ), self.base_context.result.message.content
        assert len(todo_list.todos) == 0, todo_list.todos

    @test
    async def clear_without_editing(self) -> None:
        _clear_todo_state()
        await self.command(self.cog, self.base_context)

        assert "editor mode" in self.base_context.result.message.content, (
            self.base_context.result.message.content
        )


class Delete(TestingTodo):

    def __init__(self):
        super().__init__()

    @test
    async def delete_own_list(self) -> None:
        _clear_todo_state()
        todo_list = await _make_list(self.base_author.id, title="Goodbye")

        await self.command(self.cog, self.base_context, todo_id=str(todo_list.id))

        assert (
            self.base_context.result.message.content
            == "Done! Deleted todo list Goodbye"
        ), self.base_context.result.message.content
        assert todo_list.id not in TodoList.cache

    @test
    async def delete_not_owner(self) -> None:
        _clear_todo_state()
        todo_list = await TodoList.create(
            owner=99999, title="NotMine", status="public", done_delete=False,
        )

        await self.command(self.cog, self.base_context, todo_id=str(todo_list.id))

        assert (
            self.base_context.result.message.content
            == "Only the owner of a todo list can delete it"
        ), self.base_context.result.message.content

    @test
    async def delete_nonexistent(self) -> None:
        _clear_todo_state()
        await self.command(self.cog, self.base_context, todo_id="999999")

        assert (
            self.base_context.result.message.content
            == "No todo list with this id exists"
        ), self.base_context.result.message.content


class View(TestingTodo):

    def __init__(self):
        super().__init__()

    @test
    async def view_nonexistent(self) -> None:
        _clear_todo_state()
        await self.command(self.cog, self.base_context, todo_id="999999")

        assert (
            self.base_context.result.message.content
            == "No todo list with specified ID found"
        ), self.base_context.result.message.content

    @test
    async def view_private_no_permission(self) -> None:
        _clear_todo_state()
        todo_list = await TodoList.create(
            owner=99999, title="Secret", status="private", done_delete=False,
        )

        await self.command(self.cog, self.base_context, todo_id=str(todo_list.id))

        assert (
            self.base_context.result.message.content
            == "This is a private list you don't have the permission to view"
        ), self.base_context.result.message.content

    @test
    async def view_public_list(self) -> None:
        _clear_todo_state()
        todo_list = await _make_list(self.base_author.id, title="Visible")

        await self.command(self.cog, self.base_context, todo_id=str(todo_list.id))

        assert self.base_context.result.message.embeds, (
            self.base_context.result.message.embeds
        )
        assert f'To-do list "Visible"' in (
            self.base_context.result.message.embeds[0].title
        ), self.base_context.result.message.embeds[0].title

    @test
    async def view_paginator_next_page(self) -> None:
        """Paginator: long todo list view advances with next."""
        _clear_todo_state()
        todo_list = await _make_list(self.base_author.id, enter_editing=False)
        row = {
            "todo": "x",
            "marked": None,
            "added_by": self.base_author.id,
            "added_on": datetime.now(),
            "views": 0,
            "assigned_to": [],
            "mark_log": [],
            "due_at": None,
            "notified": None,
        }
        for i in range(11):
            d = dict(row)
            d["todo"] = f"task-{i}"
            todo_list.todos.append(d)
        await todo_list.set_property("todos", todo_list.todos)

        self.base_context.timeout_view = False

        async def _pn(ctx):
            await press_paginator_button(
                ctx.current_view,
                "next",
                context=ctx,
                message=ctx.result.message,
            )
            ctx.current_view.stop()

        _prev_rtv = self.base_context.respond_to_view
        self.base_context.respond_to_view = _pn
        try:
            with patch("killua.bot.randint", return_value=100):
                await self.command(self.cog, self.base_context, todo_id=str(todo_list.id))
        finally:
            self.base_context.respond_to_view = _prev_rtv
        emb = self.base_context.result.message.embeds[0]
        assert "Page 2/2" in emb.description, emb.description
        fp = embed_footer_page(emb)
        if fp is not None:
            assert fp == (2, 2), fp


class Invite(TestingTodo):

    def __init__(self):
        super().__init__()

    @test
    async def invite_editor_accept_via_dm_confirm(self) -> None:
        _clear_todo_state()
        await _make_list(self.base_author.id, status="private")
        invitee = DiscordMember(
            id=self.base_author.id + 9001,
            username="EditorFriend",
            mutual_guilds=[object()],
        )
        await patch_user_confirm_dm(invitee, self.base_context, invitee=invitee)
        with patch("killua.cogs.todo.blcheck", AsyncMock(return_value=False)):
            await self.command(
                self.cog, self.base_context, user=invitee, role="editor"
            )

        todo_list = await TodoList.new(editing[self.base_author.id])
        assert invitee.id in todo_list.editor, todo_list.editor

    @test
    async def invite_denied_via_dm_cancel(self) -> None:
        _clear_todo_state()
        await _make_list(self.base_author.id, status="private")
        invitee = DiscordMember(
            id=self.base_author.id + 9002,
            username="DenyFriend",
            mutual_guilds=[object()],
        )
        await patch_user_confirm_dm(
            invitee, self.base_context, invitee=invitee, confirm=False
        )
        with patch("killua.cogs.todo.blcheck", AsyncMock(return_value=False)):
            await self.command(
                self.cog, self.base_context, user=invitee, role="editor"
            )

        todo_list = await TodoList.new(editing[self.base_author.id])
        assert invitee.id not in todo_list.editor, todo_list.editor
        assert invitee.id not in todo_list.viewer, todo_list.viewer

    @test
    async def cannot_invite_self(self) -> None:
        _clear_todo_state()
        await _make_list(self.base_author.id)
        await self.command(
            self.cog, self.base_context, user=self.base_author, role="editor"
        )
        assert "don't need to invite yourself" in (
            self.base_context.result.message.content
        ), self.base_context.result.message.content


class Assign(TestingTodo):

    def __init__(self):
        super().__init__()

    @test
    async def assign_task_to_editor(self) -> None:
        _clear_todo_state()
        todo_list = await _make_list(self.base_author.id)
        editor = DiscordMember(id=self.base_author.id + 9010, username="Ed")
        todo_list.editor.append(editor.id)
        await todo_list.set_property("editor", todo_list.editor)
        todo_list.todos.append({
            "todo": "task one",
            "marked": None,
            "added_by": self.base_author.id,
            "added_on": datetime.now(),
            "views": 0,
            "assigned_to": [],
            "mark_log": [],
            "due_at": None,
            "notified": None,
        })
        await todo_list.set_property("todos", todo_list.todos)

        await self.command(
            self.cog, self.base_context, todo_number=1, user=editor
        )
        assert "Successfully assigned" in self.base_context.result.message.content, (
            self.base_context.result.message.content
        )


class Kick(TestingTodo):

    def __init__(self):
        super().__init__()

    @test
    async def kick_editor(self) -> None:
        _clear_todo_state()
        todo_list = await _make_list(self.base_author.id)
        editor_id = self.base_author.id + 9020
        await todo_list.add_editor(editor_id)

        editor = DiscordMember(id=editor_id, username="KickMe")
        await self.command(self.cog, self.base_context, user=editor)
        assert "taken the editor permission" in (
            self.base_context.result.message.content
        ), self.base_context.result.message.content
        todo_list = await TodoList.new(todo_list.id)
        assert editor_id not in todo_list.editor


class Reorder(TestingTodo):

    def __init__(self):
        super().__init__()

    @test
    async def reorder_success(self) -> None:
        _clear_todo_state()
        todo_list = await _make_list(self.base_author.id)
        todo_list.todos.append({
            "todo": "second task", "marked": None, "added_by": self.base_author.id,
            "added_on": datetime.now(), "views": 0, "assigned_to": [],
            "mark_log": [], "due_at": None, "notified": None,
        })

        await self.command(self.cog, self.base_context, position=1, new_position=2)

        assert (
            self.base_context.result.message.content
            == "Successfully reordered todo task 1 to position 2"
        ), self.base_context.result.message.content

    @test
    async def reorder_invalid_position(self) -> None:
        _clear_todo_state()
        await _make_list(self.base_author.id)

        await self.command(self.cog, self.base_context, position=99, new_position=1)

        assert "don't have a number 99" in self.base_context.result.message.content, (
            self.base_context.result.message.content
        )

    @test
    async def reorder_out_of_range(self) -> None:
        _clear_todo_state()
        await _make_list(self.base_author.id)

        await self.command(self.cog, self.base_context, position=1, new_position=99)

        assert "out of range" in self.base_context.result.message.content, (
            self.base_context.result.message.content
        )

    @test
    async def reorder_without_editing(self) -> None:
        _clear_todo_state()
        await self.command(self.cog, self.base_context, position=1, new_position=2)

        assert "editor mode" in self.base_context.result.message.content, (
            self.base_context.result.message.content
        )

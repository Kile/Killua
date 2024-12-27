from __future__ import annotations

from random import randint
from typing import Any, ClassVar, Dict, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime

from killua.static.constants import DB
from killua.utils.classes.exceptions import TodoListNotFound

@dataclass
class TodoList:
    id: int
    owner: int
    name: str
    _custom_id: Optional[str]
    status: str
    delete_done: bool
    viewer: List[int]
    editor: List[int]
    created_at: Union[str, datetime]
    spots: int
    views: int
    todos: List[dict]
    _bought: List[str]
    thumbnail: Optional[str]
    color: Optional[int]
    description: Optional[str]

    cache: ClassVar[Dict[int, TodoList]] = {}
    custom_id_cache: ClassVar[Dict[str, int]] = {}

    @classmethod
    def __get_cache(cls, list_id: Union[int, str]):
        """Returns a cached object"""
        if isinstance(list_id, str) and not list_id.isdigit():
            if not list_id in cls.custom_id_cache:
                return None
            list_id = cls.custom_id_cache[list_id]
        return cls.cache[int(list_id)] if list_id in cls.cache else None

    @classmethod
    async def new(cls, list_id: Union[int, str]) -> TodoList:
        cached = cls.__get_cache(list_id)
        if cached is not None:
            return cached

        raw = await DB.todo.find_one(
            {
                (
                    "_id"
                    if (isinstance(list_id, int) or list_id.isdigit())
                    else "custom_id"
                ): (
                    int(list_id)
                    if (isinstance(list_id, int) or list_id.isdigit())
                    else list_id.lower()
                )
            }
        )

        if raw is None:
            raise TodoListNotFound()

        td_list = TodoList(
            id=raw["_id"],
            owner=raw["owner"],
            name=raw["name"],
            _custom_id=raw["custom_id"],
            status=raw["status"],
            delete_done=raw["delete_done"],
            viewer=raw["viewer"],
            editor=raw["editor"],
            created_at=raw["created_at"],
            spots=raw["spots"],
            views=raw["views"],
            todos=raw["todos"],
            _bought=raw.get("bought", []),
            thumbnail=raw.get("thumbnail", None),
            color=raw.get("color", None),
            description=raw.get("description", None),
        )

        if td_list.custom_id:
            td_list.custom_id_cache[td_list.custom_id] = td_list.id
        td_list.cache[td_list.id] = td_list

        return td_list

    @property
    def custom_id(self) -> Union[str, None]:
        return self._custom_id

    @custom_id.setter
    def custom_id(self, value: str) -> None:
        del self.custom_id_cache[self._custom_id]
        self._custom_id = value
        self.custom_id_cache[value] = self.id

    def __len__(self) -> int:
        """Makes it nicer to get the "length" of a todo list, or rather the length of its todo"s"""
        return len(self.todos)

    @staticmethod
    async def _generate_id() -> int:
        l = []
        while len(l) != 6:
            l.append(str(randint(0, 9)))

        todo_id = await DB.todo.find_one({"_id": "".join(l)})

        if todo_id is None:
            return int("".join(l))
        else:
            return await TodoList._generate_id()

    @staticmethod
    async def create(
        owner: int, title: str, status: str, done_delete: bool, custom_id: str = None
    ) -> TodoList:
        """Creates a todo list and returns a TodoList class"""
        list_id = await TodoList._generate_id()
        await DB.todo.insert_one(
            {
                "_id": list_id,
                "name": title,
                "owner": owner,
                "custom_id": custom_id,
                "status": status,
                "delete_done": done_delete,
                "viewer": [],
                "editor": [],
                "todos": [
                    {
                        "todo": "add todos",
                        "marked": None,
                        "added_by": 756206646396452975,
                        "added_on": datetime.now(),
                        "views": 0,
                        "assigned_to": [],
                        "mark_log": [],
                    }
                ],
                "marks": [],
                "created_at": (datetime.now()).strftime("%b %d %Y %H:%M:%S"),
                "spots": 10,
                "views": 0,
            }
        )
        return await TodoList.new(list_id)

    async def delete(self) -> None:
        """Deletes a todo list"""
        del self.cache[self.id]
        if self.custom_id:
            del self.custom_id_cache[self.custom_id]
        await DB.todo.delete_one({"_id": self.id})

    def has_view_permission(self, user_id: int) -> bool:
        """Checks if someone has permission to view a todo list"""
        if self.status == "private":
            if not (
                user_id in self.viewer
                or user_id in self.editor
                or user_id == self.owner
            ):
                return False
        return True

    def has_edit_permission(self, user_id: int) -> bool:
        """Checks if someone has permission to edit a todo list"""
        if not (user_id in self.editor or user_id == self.owner):
            return False
        return True

    async def _update_val(self, key: str, value: Any, operator: str = "$set") -> None:
        """An easier way to update a value"""
        await DB.todo.update_one({"_id": self.id}, {operator: {key: value}})

    async def set_property(self, prop: str, value: Any) -> None:
        """Sets any property and updates the db as well"""
        setattr(self, prop, value)
        await self._update_val(prop, value)

    async def add_view(self, viewer: int) -> None:
        """Adds a view to a todo lists view count"""
        if (
            not viewer == self.owner
            and not viewer in self.viewer
            and viewer in self.editor
        ):
            self.views += 1
            await self._update_val("views", 1, "$inc")

    async def add_task_view(self, viewer: int, task_id: int) -> None:
        """Adds a view to a todo task"""
        if (
            not viewer == self.todos[task_id - 1]["added_by"]
            and not viewer in self.todos[task_id - 1]["assigned_to"]
        ):
            self.todos[task_id - 1]["views"] += 1
            await self._update_val("todos", self.todos)

    async def add_spots(self, spots: int) -> None:
        """Easy way to add max spots"""
        self.spots += spots
        await self._update_val("spots", spots, "$inc")

    async def add_editor(self, user: int) -> None:
        """Easy way to add an editor"""
        self.editor.append(user)
        await self._update_val("editor", user, "$push")

    async def add_viewer(self, user: int) -> None:
        """Easy way to add a viewer"""
        self.viewer.append(user)
        await self._update_val("viewer", user, "$push")

    async def kick_editor(self, editor: int) -> None:
        """Easy way to kick an editor"""
        self.editor.remove(editor)
        await self._update_val("editor", editor, "$pull")

    async def kick_viewer(self, viewer: int) -> None:
        """Easy way to kick a viewer"""
        self.viewer.remove(viewer)
        await self._update_val("viewer", viewer, "$pull")

    def has_todo(self, task: int) -> bool:
        """Checks if a list contains a certain todo task"""
        try:
            if task < 1:
                return False
            self.todos[task - 1]
        except Exception:
            return False
        return True

    async def clear(self) -> None:
        """Removes all todos from a todo list"""
        self.todos = []
        await self._update_val("todos", [])

    async def enable_addon(self, addon: str) -> None:
        """Adds an attribute to the bought list to be able to be used"""
        if not addon.lower() in self._bought:
            await self._update_val("bought", addon.lower(), "$push")
            self._bought.append(addon.lower())

    def has_addon(self, addon: str) -> bool:
        """Checks if a todo list can be customized with the given attribute"""
        return addon.lower() in self._bought


@dataclass
class Todo:
    position: int
    todo: str
    marked: str
    added_by: int
    added_on: Union[str, datetime]
    views: int
    assigned_to: List[int]
    mark_log: List[dict]
    due_at: datetime = None
    notified: bool = None

    @classmethod
    async def new(cls, position: Union[int, str], list_id: Union[int, str]) -> Todo:
        parent = await TodoList.new(list_id)
        task = parent.todos[int(position) - 1]

        return Todo(position=position, **task)

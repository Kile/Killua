from typing import Optional, List, Dict
from copy import deepcopy
from random import randint


class AsyncCursor:
    """An async-iterable wrapper around a list, mimicking motor's AsyncIOMotorCursor."""

    def __init__(self, items: List[dict]):
        self._items = items
        self._index = 0

    def __aiter__(self):
        self._index = 0
        return self

    async def __anext__(self):
        if self._index >= len(self._items):
            raise StopAsyncIteration
        item = self._items[self._index]
        self._index += 1
        return item

    async def to_list(self, length=None):
        if length is not None:
            return self._items[:length]
        return list(self._items)

    def __await__(self):
        async def _resolve():
            return self._items
        return _resolve().__await__()


class TestingDatabase:
    """A database class imitating pymongos collection classes"""

    db: Dict[str, List[dict]] = {}

    @classmethod
    def reset_all(cls) -> None:
        """Clear all in-memory collections (call between test groups)."""
        cls.db.clear()

    def __init__(self, collection: str):
        self._collection = collection

    @property
    def collection(self) -> str:
        if self._collection not in self.db:
            self.db[self._collection] = []
        return self._collection

    @staticmethod
    def _resolve_path(obj: dict, dotted_key: str):
        """Traverses *obj* along a dotted key and returns (parent, final_key)."""
        parts = dotted_key.split(".")
        for part in parts[:-1]:
            obj = obj[part]
        return obj, parts[-1]

    def _matches(self, doc: dict, where: dict) -> bool:
        """Check if a document matches all conditions in *where*."""
        for wk, wv in where.items():
            if wk not in doc:
                return False
            if isinstance(wv, dict) and any(k.startswith("$") for k in wv):
                if "$in" in wv and doc[wk] not in wv["$in"]:
                    return False
                continue
            if doc[wk] != wv:
                return False
        return True

    async def find_one(self, where: dict, **kwargs) -> Optional[dict]:
        coll = self.db[self.collection]
        for d in coll:
            if self._matches(d, where):
                return deepcopy(d)

    def find(self, where: dict, *args, **kwargs) -> AsyncCursor:
        coll = self.db[self.collection]
        results = [deepcopy(d) for d in coll if self._matches(d, where)]
        return AsyncCursor(results)

    async def insert_one(self, object: dict) -> None:
        if "_id" not in object:
            object["_id"] = randint(0, 2**63)
        self.db[self.collection].append(object)

    async def insert_many(self, objects: List[dict]) -> None:
        for obj in objects:
            await self.insert_one(obj)

    async def update_one(self, where: dict, update: Dict[str, dict]) -> dict:
        operator = list(update.keys())[0]

        for p, item in enumerate(self.db[self.collection]):
            if self._matches(item, where):
                record = self.db[self.collection][p]
                for k, val in update[operator].items():
                    parent, final = self._resolve_path(record, k)

                    if operator == "$set":
                        parent[final] = val
                    elif operator == "$push":
                        parent[final].append(val)
                    elif operator == "$pull":
                        parent[final].remove(val)
                    elif operator == "$inc":
                        parent[final] += val
                break

        return update

    async def count_documents(self, where: dict = {}) -> int:
        return len([x async for x in self.find(where)])

    async def delete_one(self, where: dict) -> None:
        coll = self.db[self.collection]
        for i, d in enumerate(coll):
            if self._matches(d, where):
                coll.pop(i)
                return

    async def delete_many(self, where: dict) -> None:
        coll = self.db[self.collection]
        self.db[self.collection] = [d for d in coll if not self._matches(d, where)]

    async def update_many(self, where: dict, update: dict) -> None:
        operator = list(update.keys())[0]
        for p, item in enumerate(self.db[self.collection]):
            if self._matches(item, where):
                record = self.db[self.collection][p]
                for k, val in update[operator].items():
                    parent, final = self._resolve_path(record, k)
                    if operator == "$set":
                        parent[final] = val
                    elif operator == "$push":
                        parent[final].append(val)
                    elif operator == "$pull":
                        parent[final].remove(val)
                    elif operator == "$inc":
                        parent[final] += val

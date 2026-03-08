from typing import Optional, List, Dict
from random import randint

class TestingDatabase:
    """A database class imitating pymongos collection classes"""

    db: Dict[str, List[dict]] = {}

    def __init__(self, collection: str):
        self._collection = collection

    @property
    def collection(self) -> str:
        if self._collection not in self.db:
            self.db[self._collection] = []
        return self._collection

    def _random_id(self) -> int:
        """Creates a random 8 digit number"""
        res = int(str(randint(0, 99999999)).zfill(8))
        ids = [x.get("_id") for x in self.db.get(self.collection, [])]
        if res in ids:
            return self._random_id()
        return res

    def _normalize_dict(self, dictionary: dict) -> dict:
        """Changes the {one.two: } to {one: {two: }} for $set/$inc shape"""
        for _, d in dictionary.items():
            if isinstance(d, dict):
                for key, val in list(d.items()):
                    if "." in key:
                        k1, k2 = key.split(".", 1)
                        d.setdefault(k1, {})
                        d[k1][k2] = val
                        del d[key]
        return dictionary

    def _matches(self, doc: dict, where: dict) -> bool:
        if not where:
            return True
        for k, v in where.items():
            if k not in doc:
                return False
            if isinstance(v, dict) and "$in" in v:
                if doc[k] not in v["$in"]:
                    return False
            else:
                if doc[k] != v:
                    return False
        return True

    async def find_one(self, where: dict) -> Optional[dict]:
        coll = self.db[self.collection]
        for d in coll:
            if self._matches(d, where):
                return d

    async def find(self, where: dict) -> Optional[list]:
        coll = self.db[self.collection]
        return [d for d in coll if self._matches(d, where)]

    async def insert_one(self, object: dict) -> None:
        obj = dict(object)  # copy
        if "_id" not in obj:
            obj["_id"] = self._random_id()
        self.db[self.collection].append(obj)

    async def insert_many(self, objects: List[dict]) -> None:
        for obj in objects:
            await self.insert_one(obj)

    def _apply_update(self, item: dict, update: Dict[str, dict]) -> None:
        operator = list(update.keys())[0]

        def _set_by_path(target: dict, dotted_key: str, value):
            parts = dotted_key.split(".")
            cur = target
            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    cur[part] = value
                else:
                    cur.setdefault(part, {})
                    cur = cur[part]

        if operator == "$set":
            # Do not try to pick a single subkey; set the whole value,
            # and support dotted paths.
            for k, val in update[operator].items():
                _set_by_path(item, k, val)

        elif operator == "$push":
            for k, val in update[operator].items():
                parts = k.split(".")
                cur = item
                for i, part in enumerate(parts):
                    if i == len(parts) - 1:
                        cur.setdefault(part, [])
                        cur[part].append(val)
                    else:
                        cur.setdefault(part, {})
                        cur = cur[part]

        elif operator == "$pull":
            for k, val in update[operator].items():
                parts = k.split(".")
                cur = item
                for i, part in enumerate(parts):
                    if i == len(parts) - 1:
                        if part in cur and isinstance(cur[part], list):
                            try:
                                cur[part].remove(val)
                            except ValueError:
                                pass
                    else:
                        cur = cur.get(part, {})
                        if not isinstance(cur, dict):
                            break

        elif operator == "$inc":
            for k, val in update[operator].items():
                parts = k.split(".")
                cur = item
                for i, part in enumerate(parts):
                    if i == len(parts) - 1:
                        cur[part] = (cur.get(part, 0) or 0) + val
                    else:
                        cur.setdefault(part, {})
                        cur = cur[part]

        elif operator == "$unset":
            for dotted_key, _ in update[operator].items():
                parts = dotted_key.split(".")
                target = item
                for i, part in enumerate(parts):
                    if i == len(parts) - 1:
                        if isinstance(target, dict) and part in target:
                            del target[part]
                    else:
                        target = target.get(part, {})
                        if not isinstance(target, dict):
                            break

    async def update_one(self, where: dict, update: Dict[str, dict]) -> dict:
        for p, item in enumerate(self.db[self.collection]):
            if self._matches(item, where):
                self._apply_update(self.db[self.collection][p], update)
                return update
        return update

    async def count_documents(self, where: dict = {}) -> int:
        return len(await self.find(where) or [])

    async def delete_one(self, where: dict) -> None:
        coll = self.db[self.collection]
        for i, d in enumerate(coll):
            if self._matches(d, where):
                del coll[i]
                return

    async def delete_many(self, where: dict) -> None:
        coll = self.db[self.collection]
        self.db[self.collection] = [d for d in coll if not self._matches(d, where)]

    async def update_many(self, where: dict, update: dict) -> dict:
        modified_count = 0
        for p, item in enumerate(self.db[self.collection]):
            if self._matches(item, where):
                self._apply_update(self.db[self.collection][p], update)
                modified_count += 1

        class UpdateManyResult:
            def __init__(self, modified_count: int):
                self.modified_count = modified_count
        
        return UpdateManyResult(modified_count)
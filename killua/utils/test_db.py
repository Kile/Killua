from typing import Optional, List, Dict


class TestingDatabase:
    """A database class imitating pymongos collection classes"""

    db: Dict[str, List[dict]] = {}

    def __init__(self, collection: str):
        self._collection = collection

    @property
    def collection(self) -> str:
        if not self._collection in self.db:
            self.db[self._collection] = []
        return self._collection

    # def _random_id(self) -> int:
    #     """Creates a random 8 digit number"""
    #     res = int(str(randint(0, 99999999)).zfill(8))
    #     if res in [x["_id"] for x in self.db[self.collection]]:
    #         return self._random_id()
    #     else:
    #         return res

    def _normalize_dict(self, dictionary: dict) -> dict:
        """Changes the {one.two: } to {one: {two: }}"""
        for _, d in dictionary.items():
            if isinstance(d, dict):
                for key, val in d.items():
                    if "." in key:
                        k1 = key.split(".")[0]
                        k2 = key.split(".")[1]
                        d[k1][k2] = val
                        del d[key]
        return dictionary

    async def find_one(self, where: dict) -> Optional[dict]:
        coll = self.db[self.collection]
        for d in coll:
            for key, value in d.items():
                if len([k for k, v in where.items() if k == key and v == value]) == len(
                    where
                ):  # When all conditions defined in "where" are met
                    return d

    async def find(self, where: dict) -> Optional[list]:
        coll = self.db[self.collection]
        results = []

        for d in coll:
            for key, value in d.items():
                if [
                    x
                    for x in list(where.values())
                    if isinstance(x, dict) and "$in" in x.keys()
                ]:
                    for k, v in [
                        (k, v)
                        for k, v in list(where.items())
                        if isinstance(v, dict) and "$in" in v.keys()
                    ]:
                        if k == key and value in v["$in"]:
                            results.append(d)

                elif len(
                    [k for k, v in where.items() if k == key and v == value]
                ) == len(
                    where
                ):  # When all conditions defined in "where" are met
                    results.append(d)

        return results

    async def insert_one(self, object: dict) -> None:
        self.db[self.collection].append(object)

    async def insert_many(self, objects: List[dict]) -> None:
        for obj in objects:
            await self.insert_one(obj)

    async def update_one(self, where: dict, update: Dict[str, dict]) -> dict:
        # updated = False
        operator = list(update.keys())[0]  # This does not support multiple keys

        for v in update.values():  # Making sure it is all in the right format
            v = self._normalize_dict(v)  # lgtm [py/multiple-definition]

        for p, item in enumerate(self.db[self.collection]):
            for key, value in item.items():
                if len([k for k, v in where.items() if key == k and value == v]) == len(
                    where
                ):
                    if operator == "$set":
                        for k, val in update[operator].items():
                            if isinstance(val, dict):
                                self.db[self.collection][p][k][list(val.keys())[0]] = (
                                    list(val.values())[0]
                                )
                            else:
                                self.db[self.collection][p][k] = val
                    if operator == "$push":
                        for k, val in update[operator].items():
                            if isinstance(val, dict):
                                self.db[self.collection][p][k][
                                    list(val.keys())[0]
                                ].append(list(val.values())[0])
                            else:
                                self.db[self.collection][p][k].append(val)
                    if operator == "$pull":
                        for k, val in update[operator].items():
                            if isinstance(val, dict):
                                self.db[self.collection][p][k][
                                    list(val.keys())[0]
                                ].remove(list(val.values())[0])
                            else:
                                self.db[self.collection][p][k].remove(val)
                    elif operator == "$inc":
                        for k, val in update[operator].items():
                            if isinstance(val, dict):
                                self.db[self.collection][p][k][
                                    list(val.keys())[0]
                                ] += list(val.values())[0]
                            else:
                                self.db[self.collection][p][k] += val
                    # updated = True

        # if not updated:
        #     self.insert_one(update)

        return update  # I only need this when the update would equal the object

    async def count_documents(self, where: dict = {}) -> int:
        return len(await self.find(where) or [])

    async def delete_one(self, where: dict) -> None:
        ... # TODO: Implement this

    async def delete_many(self, where: dict) -> None:
        ... # TODO: Implement this

    async def update_many(self, where: dict, update: dict) -> None:
        ... # TODO: Implement this

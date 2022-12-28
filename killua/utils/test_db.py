from typing import Optional, List, Dict, Any

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

    def _format_dict(self, dictionary: Dict[str, Any]) -> dict:
        """Changes the {one.two: } to {one: {two: }}"""
        new = {}
        for k, d in dictionary.items():
            if "." in k:
                part = self._format_path_dict(k, d)
                # Combine the two dictionaries
                new = new | part
            else:
                new[k] = d

        return new

    # Thank you so much https://gist.github.com/NextChai/437db74df926d099032f40ca9cf9ec1f for helping me out with this!!
    def _format_path_dict(self, path: str, value: Any) -> Dict[str, Any]:
        return (
            {path.split(".")[0]: self._format_path_dict(".".join(path.split(".")[1:]), value)}
            if "." in path
            else {path: value}
        )

    def _change_val(self, dictionary: Dict[str, Any], path: str, value: str) -> Dict[str, Any]:
        if "." in path:
            dictionary[path.split(".")[0]] = self._change_val(
                dictionary[path.split(".")[0]], ".".join(path.split(".")[1:]), value
            )
        else:
            dictionary[path] = value

        return dictionary

    def _get_val(self, dictionary: Dict[str, Any], path: str) -> Any:
        if "." in path:
            return self._get_val(dictionary[path.split(".")[0]], ".".join(path.split(".")[1:]))
        else:
            return dictionary[path]

    def find_one(self, where: dict) -> Optional[dict]:
        coll = self.db[self.collection]
        for d in coll:
            for key, value in d.items():
                if len([k for k, v in where.items() if k == key and v == value]) == len(where): # When all conditions defined in "where" are met
                    return d

    def find(self, where: dict) -> Optional[dict]:
        coll = self.db[self.collection]
        results = []

        for d in coll:
            for key, value in d.items():
                if [x for x in list(where.values()) if isinstance(x, dict) and "$in" in x.keys()]:
                    for k, v in [(k, v) for k, v in list(where.items()) if isinstance(v, dict) and "$in" in v.keys()]:
                        if k == key and value in v["$in"]:
                            results.append(d)

                elif len([k for k, v in where.items() if k == key and v == value]) == len(where): # When all conditions defined in "where" are met
                    results.append(d)

        return results
    
    def insert_one(self, object: dict) -> None:
        self.db[self.collection].append(self._format_dict(object))

    def insert_many(self, objects: List[dict]) -> None:
        for obj in objects:
            self.insert_one(obj)

    def update_one(self, where: dict, update: Dict[str, dict]) -> dict:
        # updated = False
        operator = list(update.keys())[0] # This does not support multiple keys

        for v in update.values(): # Making sure it is all in the right format
            v = self._format_dict(v) #lgtm [py/multiple-definition]

        for p, item in enumerate(self.db[self.collection]):
            for key, value in item.items():
                if len([k for k, v in where.items() if key == k and value == v]) == len(where):
                    if operator == "$set":
                        for k, val in update[operator].items():
                            # if isinstance(val, dict):
                            #     self._change_val(self.db[self.collection][p][k], list(val.keys())[0], list(val.values())[0])
                            #     # self.db[self.collection][p][k][list(val.keys())[0]] = list(val.values())[0]
                            # else:
                            self._change_val(self.db[self.collection][p], k, val)
                                # self.db[self.collection][p][k] = val
                    if operator == "$push":
                        for k, val in update[operator].items():
                            # if isinstance(val, dict):
                            #     old: list = self._get_val(self.db[self.collection][p][k], list(val.keys())[0])
                            #     old.append(list(val.values())[0])
                            #     self._change_val(self.db[self.collection][p][k], list(val.keys())[0], old)
                            #     # self.db[self.collection][p][k][list(val.keys())[0]].append(list(val.values())[0])
                            # else:
                            old: list = self._get_val(self.db[self.collection][p], k)
                            old.append(val)
                            self._change_val(self.db[self.collection][p], k, old)
                                # self.db[self.collection][p][k].append(val)
                    if operator == "$pull":
                        for k, val in update[operator].items():
                            # if isinstance(val, dict):
                            #     old: list = self._get_val(self.db[self.collection][p][k], list(val.keys())[0])
                            #     old.remove(list(val.values())[0])
                            #     self._change_val(self.db[self.collection][p][k], list(val.keys())[0], old)
                            #     # self.db[self.collection][p][k][list(val.keys())[0]].remove(list(val.values())[0])
                            # else:
                            old: list = self._get_val(self.db[self.collection][p], k)
                            old.remove(val)
                            self._change_val(self.db[self.collection][p], k, old)
                                # self.db[self.collection][p][k].remove(val)
                    elif operator == "$inc":
                        for k, val in update[operator].items():
                            # if isinstance(val, dict):
                            #     old = self._get_val(self.db[self.collection][p][k], list(val.keys())[0])
                            #     self._change_val(self.db[self.collection][p][k], list(val.keys())[0], old + list(val.values())[0])
                            #     # self.db[self.collection][p][k][list(val.keys())[0]] += list(val.values())[0]
                            # else:
                            old = self._get_val(self.db[self.collection][p], k)
                            self._change_val(self.db[self.collection][p], k, old + val)
                                # self.db[self.collection][p][k] += val
                    # updated = True

        # if not updated:
        #     self.insert_one(update)

        return update # I only need this when the update would equal the object

    def try_update_one(self, where: dict, update: Dict[str, dict]) -> dict:
        # updated = False
        self.update_one(where, update)

    def count_documents(self, where: dict = {}) -> int:
        return len(self.find(where))
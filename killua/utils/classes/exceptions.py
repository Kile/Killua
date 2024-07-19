class NotInPossession(Exception):
    pass


class CardLimitReached(Exception):
    pass


class TodoListNotFound(Exception):
    pass


class CardNotFound(Exception):
    pass


class NoMatches(Exception):
    pass


class CheckFailure(Exception):
    def __init__(self, message: str, **kwargs):
        self.message = message
        super().__init__(**kwargs)


class SuccessfulDefense(CheckFailure):
    pass
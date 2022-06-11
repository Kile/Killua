from discord.ext.commands import Context

from discord import Message

from enum import Enum
from typing import Any, Coroutine

class Result(Enum):
    passed = 0
    failed = 1
    errored = 2

class ResultData:
    """An object containing the result of a command test"""

    def __init__(self, message: Message = None, error: Exception = None, actual_result: Any = None):
        self.message = message
        self.error = error
        self.actual_result = actual_result

class TestResult:

    def __init__(self):
        self.passed = []
        self.failed = []
        self.errors = []

    def completed_test(self, command: str, result: Result, result_data: ResultData = None) -> None:
        if result == Result.passed:
            self.passed.append(command)
        elif result == Result.failed:
            self.failed.append({"command": command, "result": result_data})
        else:
            self.errors.append({"command": command, "error": result_data})

class Testing:
    """Modifies several discord classes to be suitable in a testing environment"""

    @classmethod
    async def run_command(self, command: Coroutine, context: Context, *args, **kwargs) -> Any:
        try:
            return await command(context, *args, **kwargs)
        except Exception as e:
            return e
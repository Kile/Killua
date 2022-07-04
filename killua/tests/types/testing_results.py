from .message import Message

from discord.ext.commands import Command

from enum import Enum
from typing import Any

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
        self.errored = []

    def completed_test(self, command: Command, result: Result, result_data: ResultData = None) -> None:
        if result == Result.passed:
            self.passed.append(command)
        elif result == Result.failed:
            self.failed.append({"command": command, "result": result_data})
        else:
            self.errored.append({"command": command, "error": result_data})
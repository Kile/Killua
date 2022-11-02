import argparse

from typing import Optional

class _Args:

    development: Optional[bool] = None
    migrate: Optional[bool] = None
    test: Optional[bool] = None
    log: Optional[str] = None

    @classmethod
    def get_args(cls) -> None:

        parser = argparse.ArgumentParser(description="CLI arguments for the bot")
        parser.add_argument("-d", "--development", help="Run the bot in development mode", action="store_const", const=True)
        parser.add_argument("-m", "--migrate", help="Migrates the database setup from a previous version to the current one", action="store_const", const=True)
        parser.add_argument("-t", "--test", help="Run the tests", nargs="*", default=None, metavar=("cog", "command"))
        parser.add_argument("-l", "--log", help="Set the logging level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], metavar="level")
        parser.add_argument("-dl", "--download", help="Download all cards into a file for offline testing", action="store_const", const=True)

        parsed = parser.parse_args()

        cls.development = parsed.development
        cls.migrate = parsed.migrate
        cls.test = parsed.test
        cls.log = parsed.log
        cls.download = parsed.download

def init():
    global Args
    Args = _Args
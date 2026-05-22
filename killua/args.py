import argparse


class _Args:
    development: bool | None = None
    migrate: bool | None = None
    test: bool | None = None
    test_json: bool = False
    log: str | None = None
    download: str | None = None

    @classmethod
    def get_args(cls) -> None:

        parser = argparse.ArgumentParser(description="CLI arguments for the bot")
        parser.add_argument(
            "-d",
            "--development",
            help="Run the bot in development mode",
            action="store_const",
            const=True,
        )
        parser.add_argument(
            "-m",
            "--migrate",
            help="Migrates the database setup from a previous version to the current one",
            action="store_const",
            const=True,
        )
        parser.add_argument(
            "-t",
            "--test",
            help="Run the tests",
            nargs="*",
            default=None,
            metavar=("cog", "command"),
        )
        parser.add_argument(
            "--json",
            dest="test_json",
            action="store_true",
            help="With --test, print only a JSON report to stdout (exit 1 if any test failed).",
        )
        parser.add_argument(
            "-l",
            "--log",
            help="Set the logging level",
            default="INFO",
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            metavar="level",
        )
        parser.add_argument(
            "-dl",
            "--download",
            help="Download all cards into a file for testing and modifying cards",
            default=None,
            choices=["public", "private"],
            metavar="type",
        )
        parser.add_argument(
            "-dc",
            "--docker",
            help="Set if the bot is running in a docker container",
            action="store_const",
            const=True,
        )
        parser.add_argument(
            "-fl",
            "--force-local",
            help="Force the bot to download the cards data from the local API. Only relevant for development. Useful if server is down or you want to test new cards defined locally.",
            action="store_const",
            const=True,
        )

        parsed = parser.parse_args()

        if getattr(parsed, "test_json", False) and parsed.test is None:
            parser.error("--json requires -t/--test")

        cls.development = parsed.development
        cls.migrate = parsed.migrate
        cls.test = parsed.test
        cls.test_json = parsed.test_json
        cls.log = parsed.log
        cls.download = parsed.download
        cls.docker = parsed.docker
        cls.force_local = parsed.force_local


def init():
    global Args
    Args = _Args

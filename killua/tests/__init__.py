import json
import logging
import sys

from . import config
from .groups import tests
from .types import Bot
from ..static.enums import PrintColors
from datetime import datetime


# CAREFUL. This is a fairly hacky fix as assertion erros still get printed even though they are caught for some reason.
# With this, only logging messages get printed. HOWEVER this means all errors that happen outside of tests will also not be printed.
# If you get no output at all and nothing is happening, comment this section out.
class DevMod:
    def write(self, msg):
        for level in ["INFO:", "DEBUG:", "WARNING:", "ERROR:", "CRITICAL:"]:
            if level in msg:
                sys.__stderr__.write(msg)


async def _close_test_bot_session() -> None:
    """TestingBot.setup_hook creates an aiohttp ClientSession; close it after the suite."""
    session = getattr(Bot, "session", None)
    if session is None or getattr(session, "closed", True):
        return
    await session.close()


def _exit_code_for_result(tr) -> int:
    return 1 if (tr.failed or tr.errored) else 0


def _print_json_report(payload: dict, json_output: bool) -> None:
    if json_output:
        print(json.dumps(payload, indent=2), flush=True)


def _group_name(group) -> str:
    return group.__name__.replace("Testing", "")


def _log_result_counts(
    passed_count: int, failed_count: int, errored_count: int
) -> None:
    if failed_count == 0 and errored_count == 0:
        logging.info(
            PrintColors.OKGREEN
            + f"All ({passed_count}) tests passed \U00002713"
            + PrintColors.ENDC
        )
    else:
        logging.info(
            PrintColors.OKGREEN
            + f"{passed_count} tests passed \U00002713"
            + PrintColors.ENDC
        )
        logging.info(
            PrintColors.WARNING
            + f"{failed_count} tests failed \U00002715"
            + PrintColors.ENDC
        )
        logging.info(
            PrintColors.FAIL
            + f"{errored_count} tests raised unhandled exceptions \U000026a0"
            + PrintColors.ENDC
        )


def _log_elapsed(start: datetime) -> None:
    logging.info(
        PrintColors.OKCYAN
        + "Tests finished after: "
        + PrintColors.OKBLUE
        + f"{round((datetime.now() - start).total_seconds())}"
        + PrintColors.OKCYAN
        + " seconds"
        + PrintColors.ENDC
    )


def _log_run_heading(heading: str) -> None:
    logging.info(PrintColors.OKCYAN + heading + PrintColors.ENDC)


async def run_tests(args, *, json_output: bool = False) -> int:
    # sys.stderr = DevMod()

    async def _test_prefix(*_):
        return ["mention1", "mention2", "k!"]

    Bot.command_prefix = _test_prefix
    await Bot.setup_hook()
    from .fixtures import ensure_test_cards

    ensure_test_cards()
    if json_output:
        config.SUPPRESS_TEST_TRACEBACKS = True
        root = logging.getLogger()
        root.handlers = [logging.NullHandler()]
        root.setLevel(logging.CRITICAL)
    try:
        start = datetime.now()

        if args:
            if len(args) == 1:
                for group in tests:
                    if _group_name(group).lower() == args[0].lower():
                        gname = _group_name(group)
                        _log_run_heading(f"Testing group {gname}...")
                        result = await group().run_tests()
                        payload = {gname: dict(result.by_command)}
                        code = _exit_code_for_result(result)
                        _log_run_heading(f"Test results to test group {gname}:")
                        _log_result_counts(
                            len(result.passed),
                            len(result.failed),
                            len(result.errored),
                        )
                        _log_elapsed(start)
                        _print_json_report(payload, json_output)
                        return code

                sys.stderr = sys.__stderr__  # Making sure the error is displayed
                raise ValueError(
                    f"Invalid argument: {args[0]}. Make sure to provide a valid group/cog name."
                )

            for group in tests:
                if _group_name(group).lower() == args[0].lower():
                    gname = _group_name(group)
                    _log_run_heading(
                        f"Testing command {args[1]} of group {gname}..."
                    )
                    result = await group().run_tests(args[1])
                    payload = {gname: dict(result.by_command)}
                    code = _exit_code_for_result(result)
                    _log_run_heading(
                        f"Test results to test command {args[1]} of group {gname}:"
                    )
                    _log_result_counts(
                        len(result.passed),
                        len(result.failed),
                        len(result.errored),
                    )
                    _log_elapsed(start)
                    _print_json_report(payload, json_output)
                    return code

            sys.stderr = sys.__stderr__  # Making sure the error is displayed
            raise ValueError(
                f"Invalid arguments: {' '.join(args)}. Make sure to provide a valid cog and command."
            )

        total = {"passed": [], "failed": [], "errors": []}
        json_payload = {}

        for group in tests:
            gname = _group_name(group)
            _log_run_heading(f"Testing group {gname}...")
            result = await group().run_tests()
            json_payload[gname] = dict(result.by_command)
            _log_run_heading(f"Test results to test group {gname}:")
            _log_result_counts(
                len(result.passed), len(result.failed), len(result.errored)
            )

            total["passed"].extend(result.passed)
            total["failed"].extend(result.failed)
            total["errors"].extend(result.errored)
            del group

        sys.stderr = sys.__stderr__  # Reset stderr to default in case an error happens here
        logging.info(PrintColors.OKCYAN + "Total test results:" + PrintColors.ENDC)
        _log_result_counts(
            len(total["passed"]), len(total["failed"]), len(total["errors"])
        )
        _log_elapsed(start)
        suite_code = 1 if (total["failed"] or total["errors"]) else 0
        _print_json_report(json_payload, json_output)
        return suite_code
    finally:
        config.SUPPRESS_TEST_TRACEBACKS = False
        await _close_test_bot_session()

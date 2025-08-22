import logging, sys
from .groups import tests
from .types import Bot
from ..static.enums import PrintColors
from datetime import datetime
from aiohttp import ClientSession

# CAREFUL. This is a fairly hacky fix as assertion erros still get printed even though they are caught for some reason.
# With this, only logging messages get printed. HOWEVER this means all errors that happen outside of tests will also not get printed.
# If you get no output at all and nothing is happening, comment this section out.
class DevMod:
    def write(self, msg):
        for level in ["INFO:", "DEBUG:", "WARNING:", "ERROR:", "CRITICAL:"]:
            if level in msg and not "Unclosed" in msg: # Shush aiohttp random errors
                sys.__stderr__.write(msg)

async def run_tests(args) -> None:
    sys.stderr = DevMod()

    # Set up the bot for testing
    Bot.command_prefix = lambda *_: ["mention1", "mention2", "k!"]
    await Bot.setup_hook()
    start = datetime.now()
    
    # Create a single shared session for all tests
    if not hasattr(Bot, 'session') or Bot.session is None or getattr(Bot.session, 'closed', True):
        Bot.session = ClientSession()

    if args:
        if len(args) == 1:
            for group in tests:
                if group.__name__.replace("Testing", "").lower() == args[0].lower(): # If the argument was only a specific group/cog
                    logging.info(PrintColors.OKCYAN + f"Testing group {group.__name__.replace('Testing', '')}..." + PrintColors.ENDC)
                    result = await group().run_tests()
                    logging.info(PrintColors.OKCYAN + f"Test results to test group {group.__name__.replace('Testing', '')}:" + PrintColors.ENDC)
                    if len(result.failed) == 0 and len(result.errored) == 0:
                        logging.info(PrintColors.OKGREEN + f"All ({len(result.passed)}) tests passed \U00002713" + PrintColors.ENDC)
                    else:
                        logging.info(PrintColors.OKGREEN + f"{len(result.passed)} tests passed \U00002713" + PrintColors.ENDC)
                        logging.info(PrintColors.WARNING + f"{len(result.failed)} tests failed \U00002715" + PrintColors.ENDC)
                        logging.info(PrintColors.FAIL + f"{len(result.errored)} tests raised unhandled exceptions \U000026a0" + PrintColors.ENDC)
                    logging.info(PrintColors.OKCYAN + "Tests finished after: " + PrintColors.OKBLUE + f"{round((datetime.now() - start).total_seconds())}" + PrintColors.OKCYAN + " seconds" + PrintColors.ENDC)
                    return
            
            sys.stderr = sys.__stderr__ # Making sure the error is displayed
            raise ValueError(f"Invalid argument: {args[0]}. Make sure to provide a valid group/cog name.")

        else: # Both a cog and command are supplied so only the command is tested
            for group in tests:
                if group.__name__.replace("Testing", "").lower() == args[0].lower():
                    logging.info(PrintColors.OKCYAN + f"Testing command {args[1]} of group {group.__name__.replace('Testing', '')}..." + PrintColors.ENDC)
                    result = await group().run_tests(args[1])
                    logging.info(PrintColors.OKCYAN + f"Test results to test command {args[1]} of group {group.__name__.replace('Testing', '')}:" + PrintColors.ENDC)
                    if len(result.failed) == 0 and len(result.errored) == 0:
                        logging.info(PrintColors.OKGREEN + f"All ({len(result.passed)}) tests passed \U00002713" + PrintColors.ENDC)
                    else:
                        logging.info(PrintColors.OKGREEN + f"{len(result.passed)} tests passed \U00002713" + PrintColors.ENDC)
                        logging.info(PrintColors.WARNING + f"{len(result.failed)} tests failed \U00002715" + PrintColors.ENDC)
                        logging.info(PrintColors.FAIL + f"{len(result.errored)} tests raised unhandled exceptions \U000026a0" + PrintColors.ENDC)
                    logging.info(PrintColors.OKCYAN + "Tests finished after: " + PrintColors.OKBLUE + f"{round((datetime.now() - start).total_seconds())}" + PrintColors.OKCYAN + " seconds" + PrintColors.ENDC)
                    return

            sys.stderr = sys.__stderr__ # Making sure the error is displayed
            raise ValueError(f"Invalid arguments: {' '.join(args)}. Make sure to provide a valid group/cog and command.")


    total = {"passed": [], "failed": [], "errors": []}

    for group in tests:
        logging.info(PrintColors.OKCYAN + f"Testing group {group.__name__.replace('Testing', '')}..." + PrintColors.ENDC)
        result = await group().run_tests()
        logging.info(PrintColors.OKCYAN + f"Test results to test group {group.__name__.replace('Testing', '')}:" + PrintColors.ENDC)

        if len(result.failed) == 0 and len(result.errored) == 0:
            logging.info(PrintColors.OKGREEN + f"All ({len(result.passed)}) tests passed \U00002713" + PrintColors.ENDC)
        else:
            logging.info(PrintColors.OKGREEN + f"{len(result.passed)} tests passed \U00002713" + PrintColors.ENDC)
            logging.info(PrintColors.WARNING + f"{len(result.failed)} tests failed \U00002715" + PrintColors.ENDC)
            logging.info(PrintColors.FAIL + f"{len(result.errored)} tests raised unhandled exceptions \U000026a0" + PrintColors.ENDC)
        
        total["passed"].extend(result.passed)
        total["failed"].extend(result.failed)
        total["errors"].extend(result.errored)
        del group
    
    sys.stderr = sys.__stderr__ # Reset stderr to default in case an error happens here
    logging.info(PrintColors.OKCYAN + "Total test results:" + PrintColors.ENDC)
    if len(total["failed"]) == 0 and len(total["errors"]) == 0:
        logging.info(PrintColors.OKGREEN + f"All ({len(total['passed'])}) tests passed \U00002713" + PrintColors.ENDC)
    else:
        logging.info(PrintColors.OKGREEN + f"{len(total['passed'])} tests passed \U00002713" + PrintColors.ENDC)
        logging.info(PrintColors.WARNING + f"{len(total['failed'])} tests failed \U00002715" + PrintColors.ENDC)
        logging.info(PrintColors.FAIL + f"{len(total['errors'])} tests raised unhandled exceptions \U000026a0" + PrintColors.ENDC)
    
    # Ensure all client sessions are properly closed
    if hasattr(Bot, 'session') and Bot.session is not None and not getattr(Bot.session, 'closed', False):
        await Bot.session.close()
        
    logging.info(PrintColors.OKCYAN + "Tests finished after: " + PrintColors.OKBLUE + f"{round((datetime.now() - start).total_seconds())}" + PrintColors.OKCYAN + " seconds" + PrintColors.ENDC)
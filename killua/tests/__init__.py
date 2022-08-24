import logging, sys
from .groups import tests
from .types import Bot
from ..static.enums import PrintColors
from datetime import datetime

# CAREFUL. This is a fairly hacky fix as assertion erros still get printed even though they are caught for some reason.
# With this, only logging messages get printed. HOWEVER this means all errors that happen outside of tests will also not get printed.
# If you get no output at all and nothing is happening, comment this section out.
class DevMod:
    def write(self, msg):
        for level in ["INFO:", "DEBUG:", "WARNING:", "ERROR:", "CRITICAL:"]:
            if level in msg:
                sys.__stderr__.write(msg)

sys.stderr = DevMod()

async def run_tests() -> None:
    sys.stderr.write
    await Bot.setup_hook()
    start = datetime.now()
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
        # for failed in total["errors"]:
        #     print(PrintColors.FAIL + f"Errored test: {failed['command'].__name__}" + PrintColors.ENDC)
        #     print(PrintColors.FAIL + f"Error: {failed['error'].error}" + PrintColors.ENDC)
        # for failed in total["failed"]:
        #     print(PrintColors.WARNING + f"Failed test: {failed['command'].__name__}" + PrintColors.ENDC)
        #     print(PrintColors.WARNING + f"Result: {failed['result'].error}" + PrintColors.ENDC)
    logging.info(PrintColors.OKCYAN + "Tests finished after: " + PrintColors.OKBLUE + f"{round((datetime.now() - start).total_seconds())}" + PrintColors.OKCYAN + " seconds" + PrintColors.ENDC)
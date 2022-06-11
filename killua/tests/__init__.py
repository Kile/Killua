from .groups import tests
from ..static.enums import PrintColors
from datetime import datetime

async def run_tests() -> None:
    start = datetime.now()
    total = {"passed": [], "failed": [], "errors": []}
    for group in tests:
        print(PrintColors.OKCYAN + f"Testing group {group.__name__.replace('Testing', '')}..." + PrintColors.ENDC)
        result = await group().run_tests()
        print(PrintColors.OKCYAN + f"Test results to test group {group.__name__.replace('Testing', '')}:" + PrintColors.ENDC)
        if len(result.failed) == 0 and len(result.errors) == 0:
            print(PrintColors.OKGREEN + f"All ({len(result.passed)}) tests passed \U00002713" + PrintColors.ENDC)
        else:
            print(PrintColors.OKGREEN + f"{len(result.passed)} tests passed \U00002713" + PrintColors.ENDC)
            print(PrintColors.WARNING + f"{len(result.failed)} tests failed \U00002715" + PrintColors.ENDC)
            print(PrintColors.FAIL + f"{len(result.errors)} tests raised an unhandled exceptions \U000026a0" + PrintColors.ENDC)
        
        total["passed"] = [*total["passed"], *result.passed]
        total["failed"] = [*total["failed"], *result.failed]
        total["errors"] = [*total["errors"], *result.errors]
    
    print(PrintColors.OKCYAN + "Total test results:" + PrintColors.ENDC)
    if len(total["failed"]) == 0 and len(total["errors"]) == 0:
        print(PrintColors.OKGREEN + f"All ({len(total['passed'])}) tests passed \U00002713" + PrintColors.ENDC)
    else:
        print(PrintColors.OKGREEN + f"{len(total['passed'])} tests passed \U00002713" + PrintColors.ENDC)
        print(PrintColors.WARNING + f"{len(total['failed'])} tests failed \U00002715" + PrintColors.ENDC)
        print(PrintColors.FAIL + f"{len(total['errors'])} tests raised an unhandled exceptions \U000026a0" + PrintColors.ENDC)
        for failed in total["errors"]:
            print(PrintColors.FAIL + f"Errored test: {failed['command'].name}" + PrintColors.ENDC)
            print(PrintColors.FAIL + f"Error: {failed['error'].error}" + PrintColors.ENDC)
    print(PrintColors.OKCYAN + "Tests finished after: " + PrintColors.OKBLUE + f"{round((datetime.now() - start).total_seconds())}" + PrintColors.OKCYAN + " seconds" + PrintColors.ENDC)
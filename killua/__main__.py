import sys
from asyncio import run

from . import main

if __name__ == "__main__":
    code = run(main())
    sys.exit(code if isinstance(code, int) else 0)

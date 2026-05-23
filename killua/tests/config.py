"""Runtime toggles for the test harness (kept tiny to avoid import cycles)."""

# When True, assertion/other failures in @test methods skip traceback.print_tb to stderr.
SUPPRESS_TEST_TRACEBACKS: bool = False

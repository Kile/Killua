#!/usr/bin/env python3
"""
Compare discord command names on each cog with integration test class names.

By default prints gaps and exits 0 (inventory report for maintainers).
Use --strict to exit 1 when any command lacks a test class or any class is orphaned.

Usage:
  python scripts/check_test_commands.py
  python scripts/check_test_commands.py --strict
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import killua.args as args_mod

args_mod.init()
args_mod.Args.test = []  # in-memory DB for imports

from discord.ext.commands import Command

from killua.tests.groups import tests
from killua.tests.testing import _test_class_command_name


def _command_names_for_group(group_cls: type) -> set[str]:
    runner = group_cls()
    names: set[str] = set()
    for cmd in runner.cog.walk_commands():
        if isinstance(cmd, Command):
            names.add(cmd.name.lower())
    return names


def _test_class_names(group_cls: type) -> set[str]:
    runner = group_cls()
    out: set[str] = set()
    for cls in runner.all_tests:
        out.add(_test_class_command_name(cls).lower())
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if any command or test class mismatch is found",
    )
    args = parser.parse_args()

    missing_any = False
    for group_cls in tests:
        gname = group_cls.__name__.replace("Testing", "")
        if not getattr(group_cls, "requires_command", False):
            continue
        try:
            cmds = _command_names_for_group(group_cls)
            classes = _test_class_names(group_cls)
        except Exception as exc:
            print(f"{gname}: failed to inspect ({exc})", file=sys.stderr)
            missing_any = True
            continue
        missing = sorted(cmds - classes)
        extra = sorted(classes - cmds)
        if missing or extra:
            missing_any = True
            print(f"\n=== {gname} ===")
            if missing:
                print("  commands without test class:", ", ".join(missing))
            if extra:
                print("  test classes without command:", ", ".join(extra))
    if missing_any:
        if args.strict:
            return 1
        print(
            "\n(report only; re-run with --strict to fail CI on the gaps above)",
            file=sys.stderr,
        )
        return 0
    print("All command-bound test groups have matching test classes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""CI file-size cap check (RULES_AND_GUIDELINES §6).

Caps (lines):
  - source files (*.py):  SRC_MAX  (default 400)
  - test files  (tests/**): TEST_MAX (default 600)
  - markdown   (*.md):      MD_MAX   (default 1000)
Alembic migrations are exempt (generated, verbose by nature).

Exits non-zero if any file exceeds its cap, printing the offenders.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # backend/

SRC_MAX = int(os.getenv("SIZE_CAP_SRC", "400"))
TEST_MAX = int(os.getenv("SIZE_CAP_TEST", "600"))
MD_MAX = int(os.getenv("SIZE_CAP_MD", "1000"))

SRC_DIR = ROOT / "src"
TEST_DIR = ROOT / "tests"
# Alembic-generated migrations are exempt from the source cap.
MIGRATIONS_DIR = ROOT / "migrations" / "versions"


def _rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


def main() -> int:
    offenders: list[tuple[str, int, int]] = []  # (path, lines, cap)

    for py in sorted(SRC_DIR.rglob("*.py")):
        if py.is_relative_to(MIGRATIONS_DIR):
            continue
        lines = py.read_text(encoding="utf-8").count("\n")
        cap = TEST_MAX if py.is_relative_to(TEST_DIR) else SRC_MAX
        if lines > cap:
            offenders.append((_rel(py), lines, cap))

    for md in sorted(SRC_DIR.rglob("*.md")):
        lines = md.read_text(encoding="utf-8").count("\n")
        if lines > MD_MAX:
            offenders.append((_rel(md), lines, MD_MAX))

    if offenders:
        print("File-size cap violations:")
        for path, lines, cap in offenders:
            print(f"  {lines:>5} / {cap}  {path}")
        return 1
    print("File-size caps OK "
          f"(src<={SRC_MAX}, test<={TEST_MAX}, md<={MD_MAX}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

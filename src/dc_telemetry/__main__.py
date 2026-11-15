"""CLI entry. `gates` prints the not-run table and does not listen."""

from __future__ import annotations

import argparse
import json

from dc_telemetry.gates import report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", nargs="?", default="gates")
    args = parser.parse_args(argv)
    if args.command != "gates":
        print("unknown command")
        return 2
    print(json.dumps(report(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

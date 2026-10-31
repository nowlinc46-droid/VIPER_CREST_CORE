from __future__ import annotations

import argparse
import importlib
import sys


COMMANDS = {
    "online": "network_adapter",
    "matrix": "viper_matrix",
    "offline": "viper_core",
}

ALIASES = {
    "on": "online",
    "m": "matrix",
    "off": "offline",
}


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] in ALIASES:
        arguments[0] = ALIASES[arguments[0]]
    parser = argparse.ArgumentParser(
        description="ViperCrest: controlled HTTPS intake and signed F1-F9 fixture evaluation."
    )
    parser.add_argument("command", choices=COMMANDS)
    if not arguments or arguments[0] not in COMMANDS:
        parser.parse_args(arguments)
    component = importlib.import_module(COMMANDS[arguments[0]])
    return component.main(arguments[1:])


if __name__ == "__main__":
    raise SystemExit(main())

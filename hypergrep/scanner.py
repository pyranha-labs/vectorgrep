#! /usr/bin/env python3

"""Simple Intel Hyperscan file scanner."""

import argparse

import hypergrep


def on_match(matches: list, count: int) -> None:
    """Callback for C library to send results.

    Args:
        matches: Batch of results to regex patterns returned by C.
        count: How many entries are in the result batch.
    """
    for index in range(count):
        match = matches[index]
        line = match.line.decode(errors="ignore")
        print(f"{match.line_number}:{line.rstrip()}")


def parse_args() -> argparse.Namespace:
    """Parse user arguments.

    Returns:
        Namespace with all the user arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("pattern", help="Regular expression to use.")
    parser.add_argument("file", help="File to process. May be uncompressed or gzip compressed.")
    args = parser.parse_args()
    return args


def main() -> None:
    """Primary function to scan text file."""
    args = parse_args()
    hypergrep.scan(args.file, [args.pattern], on_match)


if __name__ == "__main__":
    main()

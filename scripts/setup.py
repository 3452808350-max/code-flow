#!/usr/bin/env python3
"""Bootstrap directories for the local Harness Lab workspace."""

from pathlib import Path


DIRECTORIES = [
    "backend/data/harness_lab",
    "backend/data/harness_lab/artifacts",
    "logs",
]


def main() -> None:
    for directory in DIRECTORIES:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"created {directory}")


if __name__ == "__main__":
    main()

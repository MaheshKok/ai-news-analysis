"""Backward-compatible wrapper for the primary pipeline entry point."""

import asyncio

from main import main


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

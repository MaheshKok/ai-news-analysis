"""Backward-compatible wrapper for the split fetch/analyze pipeline."""

import asyncio

import analyze_news
import fetch_news


async def main() -> int:
    """Fetch raw news, then analyze the newest raw output file."""
    fetch_result = await fetch_news.main()
    if fetch_result != 0:
        return fetch_result
    return analyze_news.main()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

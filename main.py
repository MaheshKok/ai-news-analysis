"""Primary entry point for the tech news fetch-and-analyze pipeline."""

import asyncio

import analyze_news
import fetch_news


async def main() -> int:
    """Fetch raw news first, then analyze that exact output file."""
    raw_news_path = await fetch_news.main()
    if not raw_news_path:
        return 1
    return analyze_news.main(raw_news_path)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

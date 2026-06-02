"""Fetch public tech news sources and save the raw results to a text file."""

import asyncio
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from html import unescape
from typing import List, Optional

import aiohttp
import feedparser


@dataclass
class NewsItem:
    """Individual raw news story fetched from a public source."""

    title: str
    source: str
    url: str
    published: str
    summary: str
    category: str = "general"
    relevance_score: float = 0.0


def clean_text(value: str) -> str:
    """Normalize scraped text before writing it to raw text output."""
    value = unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def build_raw_output_path(run_time: datetime, base_dir: str = "output") -> str:
    """Build the timestamped raw news text path for this run."""
    date_str = run_time.strftime("%Y-%m-%d")
    timestamp_str = run_time.strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = os.path.join(base_dir, date_str)
    return os.path.join(output_dir, f"tech_news_{timestamp_str}.txt")


def write_raw_news_txt(items: List[NewsItem], txt_path: str, run_time: datetime) -> None:
    """Write scraped news items to a plain text file for later analysis."""
    lines = [
        f"# Raw Tech News - {run_time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Total Stories: {len(items)}",
        "",
    ]

    for index, item in enumerate(items, 1):
        lines.extend(
            [
                f"--- STORY {index} ---",
                f"Title: {clean_text(item.title)}",
                f"Source: {clean_text(item.source)}",
                f"Published: {clean_text(item.published)}",
                f"Category: {clean_text(item.category)}",
                f"URL: {clean_text(item.url)}",
                f"Summary: {clean_text(item.summary)}",
                "",
            ]
        )

    with open(txt_path, "w", encoding="utf-8") as file:
        file.write("\n".join(lines))


class NewsScraper:
    """Scrapes tech news from public RSS feeds and public APIs."""

    RSS_FEEDS = {
        "TechCrunch": "https://techcrunch.com/feed/",
        "The Verge": "https://www.theverge.com/rss/partner/techmeme-full-article/rss.xml",
        "9to5Mac": "https://9to5mac.com/feed/",
        "9to5Google": "https://9to5google.com/feed/",
        "Ars Technica": "http://feeds.arstechnica.com/arstechnica/index",
        "Wired": "https://www.wired.com/feed/rss",
        "Engadget": "https://www.engadget.com/category/news/feed/",
        "MIT Technology Review": "https://www.technologyreview.com/feed/",
        "VentureBeat": "https://venturebeat.com/feed/",
        "The Register": "https://api.theregister.com/api/v1/article?orderBy=published&site_id=2&remapper=rss",
        "BBC Tech": "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "Bloomberg Tech": "https://feeds.bloomberg.com/technology/news.rss",
        "CNBC Tech": "https://www.cnbc.com/id/19854910/device/rss/rss.html",
        "Android Police": "https://www.androidpolice.com/feed/",
        "Windows Central": "https://www.windowscentral.com/feeds.xml",
        "MacRumors": "https://feeds.macrumors.com/MacRumors-All",
        "Tom's Hardware": "https://www.tomshardware.com/feeds.xml",
        "BleepingComputer": "https://www.bleepingcomputer.com/feed/",
        "Reuters Tech": "https://www.reutersagency.com/feed/?best-topics=tech&post_type=best",
    }

    def __init__(self, newsapi_key: Optional[str] = None):
        self.newsapi_key = newsapi_key
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"User-Agent": "TechNewsBot/1.0 (Research Purpose)"},
        )
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    async def fetch_rss_feed(self, source_name: str, feed_url: str) -> List[NewsItem]:
        """Fetch and parse an RSS feed."""
        items = []
        try:
            async with self.session.get(feed_url) as response:
                if response.status == 200:
                    content = await response.text()
                    feed = feedparser.parse(content)

                    for entry in feed.entries[:10]:
                        item = NewsItem(
                            title=entry.get("title", "").strip(),
                            source=source_name,
                            url=entry.get("link", ""),
                            published=entry.get("published", ""),
                            summary=entry.get("summary", "")[:500],
                            category=self._categorize_story(entry.get("title", "")),
                        )
                        items.append(item)
                else:
                    print(f"Skipping {source_name}: HTTP {response.status}")
        except Exception as error:
            print(f"Error fetching {source_name}: {error}")
        return items

    async def fetch_hackernews(self) -> List[NewsItem]:
        """Fetch top stories from Hacker News via Algolia API."""
        items = []
        try:
            url = "http://hn.algolia.com/api/v1/search"
            one_day_ago = int(time.time()) - (24 * 60 * 60)
            params = {
                "tags": "story",
                "numericFilters": f"created_at_i>{one_day_ago},points>30",
                "hitsPerPage": 20,
            }

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    for hit in data.get("hits", []):
                        item = NewsItem(
                            title=hit.get("title", "").strip(),
                            source="Hacker News",
                            url=hit.get("url", f"https://news.ycombinator.com/item?id={hit.get('objectID')}"),
                            published=hit.get("created_at", ""),
                            summary=f"Points: {hit.get('points', 0)}, Comments: {hit.get('num_comments', 0)}",
                            category=self._categorize_story(hit.get("title", "")),
                        )
                        items.append(item)
                else:
                    print(f"Skipping Hacker News: HTTP {response.status}")
        except Exception as error:
            print(f"Error fetching Hacker News: {error}")
        return items

    async def fetch_reddit_tech(self) -> List[NewsItem]:
        """Fetch from Reddit technology subreddit via the public JSON endpoint."""
        items = []
        try:
            url = "https://www.reddit.com/r/technology/hot.json?limit=15"
            headers = {"User-Agent": "TechNewsBot/1.0"}

            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    for post in data.get("data", {}).get("children", []):
                        raw_post = post["data"]
                        item = NewsItem(
                            title=raw_post.get("title", "").strip(),
                            source="Reddit r/technology",
                            url=f"https://reddit.com{raw_post.get('permalink', '')}",
                            published=datetime.fromtimestamp(raw_post.get("created_utc", 0)).isoformat(),
                            summary=f"Upvotes: {raw_post.get('score', 0)}, Comments: {raw_post.get('num_comments', 0)}",
                            category=self._categorize_story(raw_post.get("title", "")),
                        )
                        items.append(item)
                else:
                    print(f"Skipping Reddit: HTTP {response.status}")
        except Exception as error:
            print(f"Error fetching Reddit: {error}")
        return items

    async def fetch_newsapi(self) -> List[NewsItem]:
        """Fetch from NewsAPI.org when NEWSAPI_KEY is configured."""
        if not self.newsapi_key:
            return []

        items = []
        try:
            url = "https://newsapi.org/v2/top-headlines"
            params = {
                "apiKey": self.newsapi_key,
                "category": "technology",
                "language": "en",
                "pageSize": 20,
            }

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    for article in data.get("articles", []):
                        item = NewsItem(
                            title=article.get("title", "").strip(),
                            source=article.get("source", {}).get("name", "NewsAPI"),
                            url=article.get("url", ""),
                            published=article.get("publishedAt", ""),
                            summary=article.get("description", "") or "",
                            category=self._categorize_story(article.get("title", "")),
                        )
                        items.append(item)
                else:
                    print(f"Skipping NewsAPI: HTTP {response.status}")
        except Exception as error:
            print(f"Error fetching NewsAPI: {error}")
        return items

    def _categorize_story(self, title: str) -> str:
        """Categorize a news story based on keywords."""
        title_lower = title.lower()
        categories = {
            "AI Models": ["gpt", "claude", "gemini", "llama", "grok", "deepseek", "kimi", "qwen", "opus", "sonnet", "anthropic", "openai model", "llm"],
            "Apple": ["apple", "iphone", "ipad", "mac", "ios", "siri", "vision pro", "apple intelligence"],
            "Google": ["google", "android", "pixel", "chrome", "gemini", "alphabet", "search"],
            "Meta": ["meta", "facebook", "instagram", "whatsapp", "oculus", "quest"],
            "Microsoft": ["microsoft", "windows", "xbox", "azure", "copilot", "bing"],
            "India Tech": ["india", "tcs", "infosys", "jio", "isro", "sarvam", "krutrim", "indian"],
            "China Tech": ["china", "huawei", "tiktok", "bytedance", "banned", "deepseek china"],
            "Hardware": ["nvidia", "chip", "gpu", "cpu", "processor", "robot", "drone", "tesla", "ev", "iphone", "samsung"],
            "Cybersecurity": ["hack", "breach", "cyber", "security", "ransomware", "malware", "vulnerability"],
            "Business": ["ipo", "acquisition", "merger", "funding", "valuation", "revenue", "profit", "layoff"],
            "Regulation": ["regulation", "law", "bill", "eu", "antitrust", "fine", "lawsuit", "court"],
        }

        for category, keywords in categories.items():
            if any(keyword in title_lower for keyword in keywords):
                return category
        return "General Tech"

    async def fetch_all(self) -> List[NewsItem]:
        """Fetch news from all configured sources concurrently."""
        tasks = [self.fetch_rss_feed(source, url) for source, url in self.RSS_FEEDS.items()]
        tasks.append(self.fetch_hackernews())
        tasks.append(self.fetch_reddit_tech())
        if self.newsapi_key:
            tasks.append(self.fetch_newsapi())

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_items = []
        for result in results:
            if isinstance(result, list):
                all_items.extend(result)

        all_items = self._deduplicate(all_items)
        print(f"Total unique stories fetched: {len(all_items)}")
        return all_items

    def _deduplicate(self, items: List[NewsItem]) -> List[NewsItem]:
        """Remove duplicate stories based on normalized titles."""
        seen_titles = set()
        unique = []

        for item in items:
            normalized = item.title.lower().strip()
            if normalized not in seen_titles and len(normalized) > 15:
                seen_titles.add(normalized)
                unique.append(item)

        return unique


async def main() -> int:
    """Fetch news and write a raw text output file."""
    print("=" * 60)
    print("Tech News Fetcher")
    print("Public Sources -> Raw TXT")
    print("=" * 60)

    run_time = datetime.now()
    txt_path = build_raw_output_path(run_time)
    os.makedirs(os.path.dirname(txt_path), exist_ok=True)

    print("\n[1/2] Fetching news from public sources...")
    async with NewsScraper(newsapi_key=os.getenv("NEWSAPI_KEY")) as scraper:
        all_news = await scraper.fetch_all()

    if not all_news:
        print("No news fetched. Check internet access from the runtime environment.")
        return 1

    print(f"Total stories collected: {len(all_news)}")
    print("\n[2/2] Writing raw news text file...")
    write_raw_news_txt(all_news, txt_path, run_time)
    print(f"Saved raw text: {txt_path}")
    print(f"RAW_NEWS_PATH={txt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

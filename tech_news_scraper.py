"""
Tech News Scraper + AI Summarizer Pipeline
Replicates Lapaas Tech's news format for YouTube + LinkedIn content
"""

import os
import json
import time
import asyncio
import aiohttp
import feedparser
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Optional

# OpenAI for structured summarization
from openai import OpenAI


def build_output_paths(run_time: datetime, base_dir: str = "output") -> tuple[str, str]:
    """Build per-run output paths using a date folder and timestamped filenames."""
    date_str = run_time.strftime("%Y-%m-%d")
    timestamp_str = run_time.strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = os.path.join(base_dir, date_str)
    filename_base = f"tech_news_{timestamp_str}"
    return (
        os.path.join(output_dir, f"{filename_base}.md"),
        os.path.join(output_dir, f"{filename_base}.json"),
    )


@dataclass
class NewsItem:
    """Individual news story"""
    title: str
    source: str
    url: str
    published: str
    summary: str
    category: str = "general"
    relevance_score: float = 0.0


@dataclass  
class TechNewsEpisode:
    """A complete tech news episode matching Lapaas Tech format"""
    episode_date: str
    stories: List[Dict]
    intro_summary: str
    youtube_title: str
    linkedin_post: str
    topics_covered: List[str]
    
    def to_markdown(self) -> str:
        """Generate structured markdown output"""
        md = f"""# Tech News - {self.episode_date}

## YouTube Video Title
{self.youtube_title}

## Episode Intro
{self.intro_summary}

## Stories Covered

"""
        for i, story in enumerate(self.stories, 1):
            md += f"""### {i}. {story['headline']}
**Source:** {story.get('source', 'Multiple')} | **Category:** {story.get('category', 'Tech')}

{story['summary']}

**Key Points:**
"""
            for point in story.get('key_points', []):
                md += f"- {point}\n"
            md += f"\n**Impact:** {story.get('impact', 'Medium')}\n\n---\n\n"
        
        md += f"""## LinkedIn Post

{self.linkedin_post}

## Topics Covered This Episode
"""
        for topic in self.topics_covered:
            md += f"- {topic}\n"
            
        return md


class NewsScraper:
    """Scrapes tech news from multiple sources"""
    
    # RSS Feeds for tech news
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
            headers={"User-Agent": "TechNewsBot/1.0 (Research Purpose)"}
        )
        return self
        
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    async def fetch_rss_feed(self, source_name: str, feed_url: str) -> List[NewsItem]:
        """Fetch and parse an RSS feed"""
        items = []
        try:
            async with self.session.get(feed_url) as response:
                if response.status == 200:
                    content = await response.text()
                    feed = feedparser.parse(content)
                    
                    for entry in feed.entries[:10]:  # Top 10 stories
                        published = entry.get("published", "")
                        # Check if published in last 48 hours
                        item = NewsItem(
                            title=entry.get("title", "").strip(),
                            source=source_name,
                            url=entry.get("link", ""),
                            published=published,
                            summary=entry.get("summary", "")[:500],
                            category=self._categorize_story(entry.get("title", ""))
                        )
                        items.append(item)
        except Exception as e:
            print(f"Error fetching {source_name}: {e}")
        return items
    
    async def fetch_hackernews(self) -> List[NewsItem]:
        """Fetch top stories from Hacker News via Algolia API"""
        items = []
        try:
            # Get top stories from last 24 hours with decent engagement
            url = "http://hn.algolia.com/api/v1/search"
            one_day_ago = int(time.time()) - (24 * 60 * 60)
            params = {
                "tags": "story",
                "numericFilters": f"created_at_i>{one_day_ago},points>30",
                "hitsPerPage": 20
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
                            category=self._categorize_story(hit.get("title", ""))
                        )
                        items.append(item)
        except Exception as e:
            print(f"Error fetching Hacker News: {e}")
        return items
    
    async def fetch_reddit_tech(self) -> List[NewsItem]:
        """Fetch from Reddit technology subreddit via RSS"""
        items = []
        try:
            # Use Reddit's JSON API (no auth needed for read-only)
            url = "https://www.reddit.com/r/technology/hot.json?limit=15"
            headers = {"User-Agent": "TechNewsBot/1.0"}
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    for post in data.get("data", {}).get("children", []):
                        p = post["data"]
                        item = NewsItem(
                            title=p.get("title", "").strip(),
                            source=f"Reddit r/technology",
                            url=f"https://reddit.com{p.get('permalink', '')}",
                            published=datetime.fromtimestamp(p.get("created_utc", 0)).isoformat(),
                            summary=f"Upvotes: {p.get('score', 0)}, Comments: {p.get('num_comments', 0)}",
                            category=self._categorize_story(p.get("title", ""))
                        )
                        items.append(item)
        except Exception as e:
            print(f"Error fetching Reddit: {e}")
        return items
    
    async def fetch_newsapi(self) -> List[NewsItem]:
        """Fetch from NewsAPI.org (requires API key)"""
        if not self.newsapi_key:
            return []
            
        items = []
        try:
            url = "https://newsapi.org/v2/top-headlines"
            params = {
                "apiKey": self.newsapi_key,
                "category": "technology",
                "language": "en",
                "pageSize": 20
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
                            category=self._categorize_story(article.get("title", ""))
                        )
                        items.append(item)
        except Exception as e:
            print(f"Error fetching NewsAPI: {e}")
        return items
    
    def _categorize_story(self, title: str) -> str:
        """Categorize a news story based on keywords"""
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
            "Regulation": ["regulation", "law", "bill", "eu", "antitrust", "fine", "lawsuit", "court"]
        }
        
        for category, keywords in categories.items():
            if any(kw in title_lower for kw in keywords):
                return category
        return "General Tech"
    
    async def fetch_all(self) -> List[NewsItem]:
        """Fetch news from all sources concurrently"""
        tasks = []
        
        # RSS feeds
        for source, url in self.RSS_FEEDS.items():
            tasks.append(self.fetch_rss_feed(source, url))
        
        # APIs
        tasks.append(self.fetch_hackernews())
        tasks.append(self.fetch_reddit_tech())
        if self.newsapi_key:
            tasks.append(self.fetch_newsapi())
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_items = []
        for result in results:
            if isinstance(result, list):
                all_items.extend(result)
        
        # Deduplicate by title similarity
        all_items = self._deduplicate(all_items)
        
        print(f"Total unique stories fetched: {len(all_items)}")
        return all_items
    
    def _deduplicate(self, items: List[NewsItem]) -> List[NewsItem]:
        """Remove duplicate stories based on title similarity"""
        seen_titles = set()
        unique = []
        
        for item in items:
            # Normalize title for deduplication
            normalized = item.title.lower().strip()
            # Skip if very similar title already seen
            if normalized not in seen_titles and len(normalized) > 15:
                seen_titles.add(normalized)
                unique.append(item)
        
        return unique


class AISummarizer:
    """Uses OpenAI to summarize and structure news in Lapaas Tech format"""
    
    # Keywords that match Lapaas Tech's coverage focus
    PRIORITY_KEYWORDS = [
        "ai", "artificial intelligence", "gpt", "claude", "gemini", "grok", "llm",
        "openai", "anthropic", "google", "microsoft", "meta", "apple", "nvidia",
        "india", "startup", "funding", "ipo", "robot", "autonomous", "chip",
        "deepseek", "china", "security", "hack", "breach", "agent"
    ]
    
    def __init__(self, api_key: Optional[str] = None):
        self.client = OpenAI(api_key=api_key) if api_key else None
    
    def filter_relevant_stories(self, items: List[NewsItem], max_stories: int = 12) -> List[NewsItem]:
        """Filter stories that match Lapaas Tech's coverage area"""
        scored = []
        
        for item in items:
            title_lower = item.title.lower()
            score = 0
            
            # Score based on priority keywords
            for keyword in self.PRIORITY_KEYWORDS:
                if keyword in title_lower:
                    score += 2
            
            # Boost for specific high-value topics
            if any(t in title_lower for t in ["gpt", "claude", "gemini", "openai"]):
                score += 5
            if "india" in title_lower:
                score += 4
            if any(t in title_lower for t in ["nvidia", "chip", "robot", "agent"]):
                score += 3
            
            # Boost for newer stories (within 24 hours)
            try:
                if item.published:
                    pub_time = datetime.fromisoformat(item.published.replace('Z', '+00:00'))
                    hours_old = (datetime.now(pub_time.tzinfo) - pub_time).total_seconds() / 3600
                    if hours_old < 24:
                        score += 3
                    elif hours_old < 48:
                        score += 1
            except:
                pass
            
            item.relevance_score = score
            if score >= 2:  # Minimum relevance threshold
                scored.append(item)
        
        # Sort by relevance and return top N
        scored.sort(key=lambda x: x.relevance_score, reverse=True)
        return scored[:max_stories]
    
    def generate_episode(self, items: List[NewsItem]) -> TechNewsEpisode:
        """Generate a complete tech news episode"""
        if not self.client:
            # Fallback without AI - use basic formatting
            return self._generate_basic_episode(items)
        
        # Prepare input for AI
        stories_text = "\n\n".join([
            f"Story {i+1}: {item.title}\nSource: {item.source}\nCategory: {item.category}\nURL: {item.url}\nSummary: {item.summary}"
            for i, item in enumerate(items)
        ])
        
        prompt = f"""You are a tech news curator creating content in the style of Lapaas Tech (Sahil Khanna's YouTube channel). 
Create a structured tech news episode from the following stories.

Format each story with:
1. A catchy headline (like Lapaas Tech uses: short, punchy, sometimes with question marks or exclamation)
2. A 2-3 paragraph summary in conversational Indian English style
3. 3-5 key bullet points
4. Business/Indian context impact

Stories to cover:
{stories_text}

Generate output as JSON with this structure:
{{
    "youtube_title": "Catchy title for YouTube video with 5-8 key topics separated by |",
    "intro_summary": "2-3 sentence intro hook",
    "stories": [
        {{
            "headline": "Punchy headline",
            "source": "Source name",
            "category": "Category",
            "summary": "Detailed 2-3 paragraph summary",
            "key_points": ["point 1", "point 2", "point 3"],
            "impact": "Why this matters for Indian audience/tech professionals"
        }}
    ],
    "linkedin_post": "Formatted LinkedIn post with emojis and hashtags",
    "topics_covered": ["topic 1", "topic 2"]
}}
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "You are a tech news expert who creates content in the style of Indian tech YouTuber Sahil Khanna (Lapaas Tech). Use conversational English with Indian context. Focus on AI, big tech, India tech, and global tech trends."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            
            data = json.loads(response.choices[0].message.content)
            
            return TechNewsEpisode(
                episode_date=datetime.now().strftime("%Y-%m-%d"),
                stories=data.get("stories", []),
                intro_summary=data.get("intro_summary", ""),
                youtube_title=data.get("youtube_title", "Tech News"),
                linkedin_post=data.get("linkedin_post", ""),
                topics_covered=data.get("topics_covered", [])
            )
            
        except Exception as e:
            print(f"AI summarization failed: {e}")
            return self._generate_basic_episode(items)
    
    def _generate_basic_episode(self, items: List[NewsItem]) -> TechNewsEpisode:
        """Generate episode without AI (fallback)"""
        stories = []
        topics = []
        
        for item in items:
            story = {
                "headline": item.title,
                "source": item.source,
                "category": item.category,
                "summary": item.summary[:300] if item.summary else "Details available at source.",
                "key_points": [f"Source: {item.source}", f"Category: {item.category}"],
                "impact": "Follow for updates on this developing story."
            }
            stories.append(story)
            topics.append(item.category)
        
        # Build YouTube title
        top_topics = [items[i].title for i in range(min(5, len(items)))]
        youtube_title = " | ".join(top_topics[:3]) + " : Tech News"
        
        # Build LinkedIn post
        linkedin = f"🔥 Latest Tech News Roundup 🔥\n\n"
        for i, item in enumerate(items[:5], 1):
            linkedin += f"{i}. {item.title}\n"
        linkedin += "\n#TechNews #AI #Technology #Innovation #IndiaTech"
        
        return TechNewsEpisode(
            episode_date=datetime.now().strftime("%Y-%m-%d"),
            stories=stories,
            intro_summary=f"Latest tech news from {datetime.now().strftime('%B %d, %Y')}. Covering AI, big tech, and India tech updates.",
            youtube_title=youtube_title,
            linkedin_post=linkedin,
            topics_covered=list(set(topics))
        )


async def main():
    """Main execution function"""
    print("=" * 60)
    print("Tech News Scraper + AI Summarizer")
    print("Lapaas Tech Format Replication")
    print("=" * 60)
    
    # Get API keys from environment
    newsapi_key = os.getenv("NEWSAPI_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    # Fetch news
    print("\n[1/3] Fetching news from multiple sources...")
    async with NewsScraper(newsapi_key=newsapi_key) as scraper:
        all_news = await scraper.fetch_all()
    
    if not all_news:
        print("No news fetched. Check your internet connection.")
        return
    
    print(f"Total stories collected: {len(all_news)}")
    
    # Summarize with AI
    print("\n[2/3] Filtering and summarizing stories...")
    summarizer = AISummarizer(api_key=openai_key)
    relevant = summarizer.filter_relevant_stories(all_news, max_stories=12)
    print(f"Relevant stories selected: {len(relevant)}")
    
    for item in relevant[:5]:
        print(f"  - [{item.category}] {item.title[:60]}... (score: {item.relevance_score})")
    
    # Generate episode
    print("\n[3/3] Generating episode content...")
    episode = summarizer.generate_episode(relevant)
    
    # Save output
    run_time = datetime.now()
    md_path, json_path = build_output_paths(run_time)
    os.makedirs(os.path.dirname(md_path), exist_ok=True)
    
    # Save as markdown
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(episode.to_markdown())
    print(f"\nSaved markdown: {md_path}")
    
    # Save as JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "episode_date": episode.episode_date,
            "youtube_title": episode.youtube_title,
            "intro_summary": episode.intro_summary,
            "stories": episode.stories,
            "linkedin_post": episode.linkedin_post,
            "topics_covered": episode.topics_covered
        }, f, indent=2, ensure_ascii=False)
    print(f"Saved JSON: {json_path}")
    
    # Print preview
    print("\n" + "=" * 60)
    print("EPISODE PREVIEW")
    print("=" * 60)
    print(f"\nYouTube Title: {episode.youtube_title}")
    print(f"\nIntro: {episode.intro_summary[:150]}...")
    print(f"\nStories: {len(episode.stories)}")
    for i, story in enumerate(episode.stories, 1):
        print(f"  {i}. {story['headline']}")
    print(f"\nTopics: {', '.join(episode.topics_covered[:5])}")
    
    return episode


if __name__ == "__main__":
    asyncio.run(main())

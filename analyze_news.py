"""Analyze a raw tech-news text file and generate a structured Markdown report."""

import glob
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
from typing import Dict, List, Optional

from fetch_news import NewsItem


@dataclass
class TechNewsEpisode:
    """A complete tech news episode matching Lapaas Tech format."""

    episode_date: str
    stories: List[Dict]
    intro_summary: str
    youtube_title: str
    linkedin_post: str
    topics_covered: List[str]

    def to_markdown(self) -> str:
        """Generate structured markdown output."""
        markdown = f"""# Tech News - {self.episode_date}

## YouTube Video Title
{self.youtube_title}

## Episode Intro
{self.intro_summary}

## Stories Covered

"""
        for index, story in enumerate(self.stories, 1):
            markdown += f"""### {index}. {story['headline']}
**Source:** {story.get('source', 'Multiple')} | **Category:** {story.get('category', 'Tech')}

{story['summary']}

**Key Points:**
"""
            for point in story.get("key_points", []):
                markdown += f"- {point}\n"
            markdown += f"\n**Impact:** {story.get('impact', 'Medium')}\n\n---\n\n"

        markdown += f"""## LinkedIn Post

{self.linkedin_post}

## Topics Covered This Episode
"""
        for topic in self.topics_covered:
            markdown += f"- {topic}\n"

        return markdown


def clean_text(value: str) -> str:
    """Normalize text parsed from raw output."""
    value = unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def build_markdown_output_path(txt_path: str) -> str:
    """Build the markdown path that pairs with a raw text output file."""
    root, _extension = os.path.splitext(txt_path)
    return f"{root}.md"


def find_latest_raw_news_file(base_dir: str = "output") -> str:
    """Find the newest raw news text file in the output tree."""
    candidates = glob.glob(os.path.join(base_dir, "**", "tech_news_*.txt"), recursive=True)
    if not candidates:
        raise FileNotFoundError(f"No raw news .txt files found under {base_dir}/")
    return max(candidates, key=os.path.getmtime)


def read_raw_news_txt(txt_path: str) -> List[NewsItem]:
    """Parse the raw text output back into NewsItem objects for analysis."""
    with open(txt_path, "r", encoding="utf-8") as file:
        content = file.read()

    items: List[NewsItem] = []
    for block in re.split(r"^--- STORY \d+ ---$", content, flags=re.MULTILINE):
        if "Title:" not in block:
            continue

        fields: Dict[str, str] = {}
        current_key: Optional[str] = None
        for line in block.strip().splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip().lower()
                if key in {"title", "source", "published", "category", "url", "summary"}:
                    current_key = key
                    fields[current_key] = value.strip()
                    continue
            if current_key:
                fields[current_key] = f"{fields[current_key]} {line.strip()}".strip()

        title = fields.get("title", "").strip()
        if not title:
            continue

        items.append(
            NewsItem(
                title=title,
                source=fields.get("source", "Unknown"),
                url=fields.get("url", ""),
                published=fields.get("published", ""),
                summary=fields.get("summary", ""),
                category=fields.get("category", "General Tech"),
            )
        )

    return items


class LocalNewsAnalyzer:
    """Analyzes raw scraped news locally without OpenAI or any other LLM API."""

    PRIORITY_KEYWORDS = [
        "ai", "artificial intelligence", "gpt", "claude", "gemini", "grok", "llm",
        "openai", "anthropic", "google", "microsoft", "meta", "apple", "nvidia",
        "india", "startup", "funding", "ipo", "robot", "autonomous", "chip",
        "deepseek", "china", "security", "hack", "breach", "agent",
    ]

    IMPACT_BY_CATEGORY = {
        "AI Models": "High creator and business impact: model releases can change workflows, automation costs, and product roadmaps quickly.",
        "India Tech": "High India relevance: useful for Indian founders, students, job seekers, and tech teams tracking domestic opportunities.",
        "China Tech": "Strategic global impact: worth tracking for AI competition, hardware supply chains, and geopolitics.",
        "Hardware": "Practical industry impact: chips, devices, and robotics updates can affect pricing, capability, and adoption timelines.",
        "Cybersecurity": "Operational impact: security stories may require immediate attention from businesses and individuals.",
        "Business": "Market impact: funding, IPO, acquisition, and layoff stories can signal where tech money and hiring are moving.",
        "Regulation": "Policy impact: regulation can change what platforms, AI companies, and users are allowed to do.",
    }

    def filter_relevant_stories(self, items: List[NewsItem], max_stories: int = 12) -> List[NewsItem]:
        """Score and select stories that match the channel's AI-heavy tech focus."""
        scored = []

        for item in items:
            text = f"{item.title} {item.summary} {item.category}".lower()
            score = 0

            for keyword in self.PRIORITY_KEYWORDS:
                if keyword in text:
                    score += 2

            if any(topic in text for topic in ["gpt", "claude", "gemini", "openai", "anthropic"]):
                score += 5
            if any(topic in text for topic in ["india", "indian", "jio", "isro", "sarvam", "krutrim"]):
                score += 4
            if any(topic in text for topic in ["nvidia", "chip", "robot", "agent"]):
                score += 3

            try:
                if item.published:
                    pub_time = datetime.fromisoformat(item.published.replace("Z", "+00:00"))
                    if pub_time.tzinfo is None:
                        pub_time = pub_time.replace(tzinfo=timezone.utc)
                    else:
                        pub_time = pub_time.astimezone(timezone.utc)
                    hours_old = (datetime.now(timezone.utc) - pub_time).total_seconds() / 3600
                    if hours_old < 24:
                        score += 3
                    elif hours_old < 48:
                        score += 1
            except (TypeError, ValueError):
                pass

            item.relevance_score = score
            if score >= 2:
                scored.append(item)

        if not scored:
            scored = items[:]

        scored.sort(key=lambda news: news.relevance_score, reverse=True)
        return scored[:max_stories]

    def generate_episode_from_txt(self, txt_path: str, max_stories: int = 12) -> TechNewsEpisode:
        """Create a structured markdown-ready episode by analyzing the raw text file."""
        items = read_raw_news_txt(txt_path)
        relevant = self.filter_relevant_stories(items, max_stories=max_stories)
        return self.generate_episode(relevant, total_raw_stories=len(items))

    def generate_episode(self, items: List[NewsItem], total_raw_stories: int = 0) -> TechNewsEpisode:
        """Generate a deterministic, structured episode without external AI calls."""
        stories = []
        topics = []

        for item in items:
            summary = clean_text(item.summary) or "Details available at the source link."
            story = {
                "headline": item.title,
                "source": item.source,
                "category": item.category,
                "summary": self._build_story_summary(item, summary),
                "key_points": self._build_key_points(item),
                "impact": self.IMPACT_BY_CATEGORY.get(
                    item.category,
                    "General tech impact: useful story to track for product, platform, and industry trend updates.",
                ),
            }
            stories.append(story)
            topics.append(item.category)

        unique_topics = list(dict.fromkeys(topics))
        youtube_title = self._build_youtube_title(items)
        intro_summary = self._build_intro_summary(items, unique_topics, total_raw_stories)
        linkedin_post = self._build_linkedin_post(items, unique_topics)

        return TechNewsEpisode(
            episode_date=datetime.now().strftime("%Y-%m-%d"),
            stories=stories,
            intro_summary=intro_summary,
            youtube_title=youtube_title,
            linkedin_post=linkedin_post,
            topics_covered=unique_topics,
        )

    def _build_story_summary(self, item: NewsItem, summary: str) -> str:
        return (
            f"{summary}\n\n"
            f"This story is tagged under **{item.category}** and was selected from {item.source} "
            f"with a local relevance score of {item.relevance_score:.0f}. "
            "The score is based on AI, big-tech, India-tech, hardware, business, and security keywords, "
            "so the roundup can be generated without an OpenAI API key."
        )

    def _build_key_points(self, item: NewsItem) -> List[str]:
        points = [
            f"Source: {item.source}",
            f"Category: {item.category}",
            f"Local relevance score: {item.relevance_score:.0f}",
        ]
        if item.published:
            points.append(f"Published: {item.published}")
        if item.url:
            points.append(f"Read more: {item.url}")
        return points

    def _build_youtube_title(self, items: List[NewsItem]) -> str:
        if not items:
            return "Tech News Roundup"

        title_parts = [item.title for item in items[:3]]
        title = " | ".join(title_parts)
        return f"{title} : Tech News"[:180]

    def _build_intro_summary(self, items: List[NewsItem], topics: List[str], total_raw_stories: int) -> str:
        if not items:
            return "No relevant tech stories were available for this run."

        topic_text = ", ".join(topics[:5]) or "technology"
        return (
            f"Today's automated roundup analyzed {total_raw_stories or len(items)} scraped stories and selected "
            f"{len(items)} high-signal updates across {topic_text}. "
            "The analysis is fully local and rule-based, so it does not require an OpenAI API key."
        )

    def _build_linkedin_post(self, items: List[NewsItem], topics: List[str]) -> str:
        linkedin = "🔥 Latest Tech News Roundup 🔥\n\n"
        linkedin += "Generated from raw scraped news and analyzed locally without an OpenAI API key.\n\n"
        for index, item in enumerate(items[:5], 1):
            linkedin += f"{index}. {item.title} ({item.source})\n"
        hashtag_topics = " ".join(f"#{topic.replace(' ', '')}" for topic in topics[:4])
        linkedin += f"\n#TechNews #AI #Technology #Innovation {hashtag_topics}".strip()
        return linkedin


def analyze_raw_news_file(txt_path: str) -> str:
    """Analyze one raw text file and return the generated markdown path."""
    md_path = build_markdown_output_path(txt_path)
    analyzer = LocalNewsAnalyzer()
    episode = analyzer.generate_episode_from_txt(txt_path, max_stories=12)

    with open(md_path, "w", encoding="utf-8") as file:
        file.write(episode.to_markdown())

    return md_path


def main(txt_path: Optional[str] = None) -> int:
    """Analyze an explicit raw text file, or fall back to the latest raw file."""
    print("=" * 60)
    print("Tech News Analyzer")
    print("Raw TXT -> Structured Markdown")
    print("=" * 60)

    txt_path = txt_path or find_latest_raw_news_file()
    print(f"Analyzing raw text: {txt_path}")

    md_path = analyze_raw_news_file(txt_path)
    print(f"Saved markdown: {md_path}")
    print(f"MARKDOWN_PATH={md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else None))

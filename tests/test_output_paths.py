import os
import tempfile
import unittest
from datetime import datetime

from analyze_news import (
    LocalNewsAnalyzer,
    build_markdown_output_path,
    read_raw_news_txt,
)
from fetch_news import NewsItem, build_raw_output_path, write_raw_news_txt


class OutputPathTests(unittest.TestCase):
    def test_build_raw_and_markdown_paths_use_date_folder_and_timestamped_filenames(self):
        txt_path = build_raw_output_path(datetime(2026, 6, 2, 14, 5, 9))
        md_path = build_markdown_output_path(txt_path)

        self.assertEqual(
            txt_path,
            os.path.join("output", "2026-06-02", "tech_news_2026-06-02_14-05-09.txt"),
        )
        self.assertEqual(
            md_path,
            os.path.join("output", "2026-06-02", "tech_news_2026-06-02_14-05-09.md"),
        )
        self.assertEqual(os.path.dirname(txt_path), os.path.dirname(md_path))

    def test_raw_txt_roundtrip_and_local_markdown_analysis(self):
        items = [
            NewsItem(
                title="OpenAI launches new agent tools in India",
                source="Example Tech",
                url="https://example.com/openai-agent-india",
                published="2026-06-02T12:00:00+00:00",
                summary="A new AI agent update targets business automation workflows.",
                category="AI Models",
            )
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            txt_path = os.path.join(temp_dir, "raw.txt")
            write_raw_news_txt(items, txt_path, datetime(2026, 6, 2, 14, 5, 9))

            parsed = read_raw_news_txt(txt_path)
            self.assertEqual(len(parsed), 1)
            self.assertEqual(parsed[0].title, items[0].title)
            self.assertEqual(parsed[0].source, items[0].source)
            self.assertEqual(parsed[0].url, items[0].url)
            self.assertEqual(parsed[0].published, items[0].published)
            self.assertEqual(parsed[0].summary, items[0].summary)
            self.assertEqual(parsed[0].category, items[0].category)

            episode = LocalNewsAnalyzer().generate_episode_from_txt(txt_path)
            markdown = episode.to_markdown()

            self.assertIn("## Stories Covered", markdown)
            self.assertIn("OpenAI launches new agent tools in India", markdown)
            self.assertIn("without an OpenAI API key", markdown)

    def test_local_analyzer_accepts_naive_published_timestamp(self):
        item = NewsItem(
            title="AI chip",
            source="Example Tech",
            url="https://example.com/ai-chip",
            published=datetime.now().replace(microsecond=0).isoformat(),
            summary="A new AI chip story.",
            category="Hardware",
        )

        relevant = LocalNewsAnalyzer().filter_relevant_stories([item])

        self.assertEqual(len(relevant), 1)
        self.assertEqual(relevant[0].title, item.title)

    def test_deduplicate_keeps_short_valid_titles(self):
        from fetch_news import NewsScraper

        item = NewsItem(
            title="AI chip",
            source="Example Tech",
            url="https://example.com/ai-chip",
            published="",
            summary="Short but valid title.",
            category="Hardware",
        )

        unique = NewsScraper()._deduplicate([item])

        self.assertEqual(unique, [item])


if __name__ == "__main__":
    unittest.main()

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

            episode = LocalNewsAnalyzer().generate_episode_from_txt(txt_path)
            markdown = episode.to_markdown()

            self.assertIn("## Stories Covered", markdown)
            self.assertIn("OpenAI launches new agent tools in India", markdown)
            self.assertIn("without an OpenAI API key", markdown)


if __name__ == "__main__":
    unittest.main()

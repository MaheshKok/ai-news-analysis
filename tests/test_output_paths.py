import os
import unittest
from datetime import datetime

from tech_news_scraper import build_output_paths


class OutputPathTests(unittest.TestCase):
    def test_build_output_paths_uses_date_folder_and_timestamped_filenames(self):
        md_path, json_path = build_output_paths(datetime(2026, 6, 2, 14, 5, 9))

        self.assertEqual(
            md_path,
            os.path.join("output", "2026-06-02", "tech_news_2026-06-02_14-05-09.md"),
        )
        self.assertEqual(
            json_path,
            os.path.join("output", "2026-06-02", "tech_news_2026-06-02_14-05-09.json"),
        )
        self.assertEqual(os.path.dirname(md_path), os.path.dirname(json_path))


if __name__ == "__main__":
    unittest.main()

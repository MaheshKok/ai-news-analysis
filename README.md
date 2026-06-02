# Tech News Automation Pipeline
## Replicate Lapaas Tech Format for YouTube + LinkedIn

---

## What This Project Does

This is a **complete automation pipeline** that scrapes tech news from 20+ sources, filters for stories matching Lapaas Tech's coverage style, and generates structured output ready for:
- **YouTube video scripts** (with timestamps/chapters)
- **LinkedIn posts** (with emojis and hashtags)
- **Markdown reports** (for your reference)

### Lapaas Tech Coverage Analysis (Last 90 Days)

After analyzing **~30 videos** from Lapaas Tech, here's what Sahil Khanna covers:

| **Category** | **% of Coverage** | **Example Topics** |
|---|---|---|
| **AI Model Releases** | ~30% | GPT-5.x, Claude Opus, Gemini 3.x, Grok, DeepSeek, Kimi, Qwen |
| **Big Tech Moves** | ~25% | Google, OpenAI, Meta, Apple, Microsoft announcements |
| **India Tech** | ~15% | TCS/Infosys AI adoption, ISRO, Sarvam AI, Krutrim, Jio |
| **China Tech** | ~10% | Chinese AI models, Huawei, chip developments |
| **Hardware & Robotics** | ~10% | Nvidia chips, humanoid robots, Apple devices |
| **Business & Jobs** | ~5% | AI impact on jobs, enterprise adoption, funding |
| **Geopolitics** | ~5% | AI regulation, US-China tech race, India policies |

### Video Format Pattern
- **8-12 stories per episode**
- **18-32 minutes total runtime**
- Each story gets **2-3 minutes** of coverage
- Conversational Indian English style
- Mix of Indian and global context

---

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  NEWS SOURCES   │────▶│  FILTER & SCORE  │────▶│  AI SUMMARIZER  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                                               │
    ┌────┴────┐                                    ┌────┴────┐
    ▼         ▼                                    ▼         ▼
┌───────┐ ┌───────┐                         ┌────────┐ ┌────────┐
│RSS    │ │Hacker │                         │YouTube │ │LinkedIn│
│Feeds  │ │News   │                         │Script  │ │Post    │
│(19)   │ │API    │                         │(.md)   │ │(.md)   │
└───────┘ └───────┘                         └────────┘ └────────┘
┌───────┐ ┌───────┐
│Reddit │ │NewsAPI│
│API    │ │(opt)  │
└───────┘ └───────┘
```

---

## Setup Instructions

### Step 1: Fork/Clone This Repository

```bash
git clone https://github.com/YOUR_USERNAME/tech-news-automation.git
cd tech-news-automation
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

Required packages:
- `aiohttp` — Async HTTP client for fetching feeds
- `feedparser` — RSS feed parsing
- `openai` — AI summarization (optional but recommended)
- `python-dotenv` — Environment variable management

### Step 3: Configure API Keys (Optional but Recommended)

Create a `.env` file in the root directory:

```bash
# Required for AI-powered summaries (much better output)
OPENAI_API_KEY=sk-your-openai-key-here

# Optional - adds more news sources
NEWSAPI_KEY=your-newsapi-key-here
```

**Where to get API keys:**
- **OpenAI API Key**: https://platform.openai.com/api-keys (Cost: ~$0.05-0.10 per episode)
- **NewsAPI Key**: https://newsapi.org/register (Free tier: 100 requests/day)

### Step 4: Run Locally

```bash
# Run the scraper
python tech_news_scraper.py

# Output will be saved to:
# - output/tech_news_YYYY-MM-DD.md (markdown report)
# - output/tech_news_YYYY-MM-DD.json (structured data)
```

---

## GitHub Actions Automation (Run Every Hour)

The repository includes a GitHub Actions workflow that runs automatically every hour.

### Setup GitHub Actions:

1. **Push code to GitHub:**
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/tech-news-automation.git
git push -u origin main
```

2. **Add secrets to GitHub:**
   - Go to **Settings → Secrets and variables → Actions**
   - Add `OPENAI_API_KEY` (required for AI summaries)
   - Add `NEWSAPI_KEY` (optional)

3. **The workflow will:**
   - Run every hour (`0 * * * *`)
   - Scrape all news sources
   - Generate AI-powered summaries
   - Commit results to `output/` folder
   - You can also trigger manually from Actions tab

### Workflow File: `.github/workflows/scraper.yml`

```yaml
name: Tech News Scraper - Hourly
on:
  schedule:
    - cron: '0 * * * *'  # Every hour
  workflow_dispatch:       # Manual trigger
jobs:
  scrape-and-summarize:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python tech_news_scraper.py
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          NEWSAPI_KEY: ${{ secrets.NEWSAPI_KEY }}
      - run: |
          git config user.name 'GitHub Actions'
          git config user.email 'actions@github.com'
          git add output/
          git diff --staged --quiet || git commit -m "📰 Tech News $(date -u +%Y-%m-%d)"
          git push
```

---

## News Sources (20+ Sources)

### RSS Feeds (19 sources)
| Source | URL | Category Focus |
|--------|-----|---------------|
| TechCrunch | techcrunch.com/feed | Startups, Funding |
| The Verge | theverge.com/rss | General Tech |
| 9to5Mac | 9to5mac.com/feed | Apple |
| 9to5Google | 9to5google.com/feed | Google, Android |
| Ars Technica | arstechnica.com | Deep Tech |
| Wired | wired.com/feed | Tech Culture |
| Engadget | engadget.com | Consumer Tech |
| MIT Tech Review | technologyreview.com | Research |
| VentureBeat | venturebeat.com | Enterprise AI |
| The Register | theregister.com | IT News |
| BBC Tech | bbc.co.uk/news/technology | General |
| Bloomberg Tech | bloomberg.com/technology | Business |
| CNBC Tech | cnbc.com/technology | Finance Tech |
| Android Police | androidpolice.com | Android |
| Windows Central | windowscentral.com | Microsoft |
| MacRumors | macrumors.com | Apple |
| Tom's Hardware | tomshardware.com | Hardware |
| BleepingComputer | bleepingcomputer.com | Security |
| Reuters Tech | reuters.com/technology | Global |

### APIs (3 sources)
| Source | Type | Authentication |
|--------|------|---------------|
| Hacker News | Algolia Search API | None (free) |
| Reddit r/technology | JSON API | None (read-only) |
| NewsAPI.org | REST API | API Key (free tier) |

---

## How the Scoring Works

Stories are scored based on relevance to Lapaas Tech's coverage:

```python
Scoring Rules:
+5 points: Contains "GPT", "Claude", "Gemini", "OpenAI"
+4 points: Contains "India", Indian company names
+3 points: Contains "Nvidia", "Chip", "Robot", "Agent"
+2 points: Contains general AI/tech keywords
+3 points: Published within last 24 hours
+1 point: Published within last 48 hours

Minimum threshold: 2 points to be included
```

This ensures you get stories that match the Lapaas Tech style — AI-heavy, India-relevant, and timely.

---

## Output Format

### YouTube Script (Markdown)

```markdown
# Tech News - 2026-06-01

## YouTube Video Title
Gemini Spark Goes LIVE, OpenAI Making a Phone?, Military Robots | Tech News

## Episode Intro
AI is moving faster than ever and this week we have some massive updates...

## Stories Covered

### 1. Gemini Spark Rolls Out to Google AI Ultra
**Source:** 9to5Google | **Category:** AI Models

[2-3 paragraph conversational summary]

**Key Points:**
- Point 1
- Point 2
- Point 3

**Impact:** Why this matters for Indian audience

---

[More stories...]

## LinkedIn Post
[Formatted post with emojis]

## Topics Covered
- AI Models
- Hardware
- India Tech
```

### JSON Output

```json
{
  "episode_date": "2026-06-01",
  "youtube_title": "...",
  "intro_summary": "...",
  "stories": [
    {
      "headline": "...",
      "source": "...",
      "category": "...",
      "summary": "...",
      "key_points": ["..."],
      "impact": "..."
    }
  ],
  "linkedin_post": "...",
  "topics_covered": ["..."]
}
```

---

## Customization

### Adding More Sources

Edit the `RSS_FEEDS` dictionary in `tech_news_scraper.py`:

```python
RSS_FEEDS = {
    "Your Source": "https://example.com/feed/",
    # Add more...
}
```

### Adjusting Story Count

Change the `max_stories` parameter:

```python
relevant = summarizer.filter_relevant_stories(all_news, max_stories=15)
```

### Changing Scoring Weights

Edit the `PRIORITY_KEYWORDS` and scoring logic in `AISummarizer` class.

### Modifying Output Format

Edit the `TechNewsEpisode.to_markdown()` method to customize the output template.

---

## Cost Analysis

### Without AI (Basic Mode)
- **Cost:** FREE
- **Output:** Basic summaries, no AI enhancement
- **Quality:** Usable but not as polished

### With OpenAI (Recommended)
- **Cost per episode:** ~$0.05 - $0.15
- **Monthly cost (24 episodes):** ~$1.20 - $3.60
- **Output:** Professional, Lapaas Tech-style summaries
- **Quality:** High, ready to use for videos

### API Costs (Optional)
- **NewsAPI Free Tier:** 100 requests/day (sufficient)
- **Hacker News API:** Free
- **Reddit API:** Free for read-only

---

## Alternative: Using n8n Instead of GitHub Actions

If you prefer n8n over GitHub Actions, here's the equivalent workflow:

### n8n Workflow Structure:

```
1. Schedule Trigger (Every hour)
   ↓
2. HTTP Request nodes (fetch RSS feeds)
   ↓
3. Function node (parse and deduplicate)
   ↓
4. OpenAI node (summarize with custom prompt)
   ↓
5. Google Sheets / Notion (store output)
   ↓
6. Slack / Telegram (notify when ready)
```

### n8n Advantages:
- Visual workflow builder
- Easy integration with 400+ apps
- Built-in error handling and retries
- Can post directly to LinkedIn via API

### n8n Disadvantages:
- Self-hosted n8n requires a server (~$5/month)
- n8n Cloud has execution limits on free tier
- More complex to set up initially

---

## Using the Output for Content Creation

### For YouTube Videos:
1. Open the generated `.md` file
2. Use the "YouTube Video Title" as your video title
3. Record using the "Stories Covered" section as your script
4. Add timestamps in description using story breakdown
5. The "Episode Intro" is your hook (first 30 seconds)

### For LinkedIn:
1. Copy the "LinkedIn Post" section
2. Add relevant hashtags (already included)
3. Post with a relevant image/ graphic
4. Engage with comments for 30 minutes after posting

### Publishing Schedule Recommendation:
- **YouTube:** Daily at 9 PM IST (like Lapaas Tech)
- **LinkedIn:** Daily at 8-9 AM IST (morning commute)
- **Shorts:** Extract individual stories as 60-second shorts

---

## Troubleshooting

### Issue: No stories fetched
- Check internet connection
- Some RSS feeds may be temporarily down
- Try running again in a few minutes

### Issue: API rate limits
- NewsAPI free tier: 100 requests/day
- Reddit: 60 requests/minute
- Add delays between requests if needed

### Issue: AI summaries not generating
- Check that `OPENAI_API_KEY` is set correctly
- Verify API key has billing enabled
- Fallback to basic mode works without API key

### Issue: GitHub Actions not running
- Check that workflow file is in `.github/workflows/`
- Verify secrets are set in repository settings
- Check Actions tab for error logs

---

## File Structure

```
tech-news-automation/
├── tech_news_scraper.py      # Main scraper + AI pipeline
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variables template
├── .github/
│   └── workflows/
│       └── scraper.yml       # GitHub Actions workflow
├── output/                   # Generated content (auto-created)
│   ├── tech_news_2026-06-01.md
│   └── tech_news_2026-06-01.json
└── README.md                 # This file
```

---

## Next Steps

1. **Set up the repository** on GitHub
2. **Add your API keys** as repository secrets
3. **Run manually first** to verify everything works
4. **Let GitHub Actions run automatically** every hour
5. **Check output folder** for generated content
6. **Use the markdown files** as scripts for your videos
7. **Post LinkedIn content** using the generated posts

---

## Legal & Ethical Notes

- All RSS feeds used are publicly available
- Hacker News API is free and open
- Reddit API is used in read-only mode
- Content is summarized/transformed (fair use)
- Always cite original sources in videos
- Follow YouTube and LinkedIn community guidelines

---

## Support

For issues, questions, or feature requests:
- Open an issue on GitHub
- The code is fully commented for easy modification
- Customize the scoring, sources, and output format as needed

---

**Happy content creation!** 🚀

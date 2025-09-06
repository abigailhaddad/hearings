# YouTube-Congress Matcher

Matches YouTube videos from the House Energy & Commerce Committee with Congress.gov hearing records.

## Workflow

### 1. Data Collection

**YouTube Data:**
1. Manually save the Energy & Commerce YouTube channel page HTML
2. Run `parse_ec_html_complete.py` to extract video metadata
3. Run `update_all_video_dates.py` to convert relative dates to exact dates

**Congressional Data:**
1. Get Congress.gov API key from https://api.data.gov
2. Run `scripts/build_ec_index_filtered.py` to fetch Energy & Commerce hearing data from Congress API

### 2. Matching Process

Run `match_all_youtube_videos.py` to match videos with hearings based on:
- Date matching (same day gets highest score)
- Title similarity using fuzzy string matching
- Event type (hearing, markup, etc.)

### 3. View Results

Open `viewer-simple.html` in a browser to see the matched videos with links to both YouTube and Congress.gov.

## File Structure

**Data files:**
- `ec_youtube_complete_dataset.json` - All extracted YouTube videos
- `ec_youtube_videos_with_exact_dates.json` - YouTube videos with dates converted
- `outputs/ec_filtered_index.json` - Energy & Commerce hearings from Congress API
- `youtube_congress_matches.json` - Final matching results

**Scripts:**
- `parse_ec_html_complete.py` - Extract videos from saved YouTube HTML
- `update_all_video_dates.py` - Convert relative dates to exact dates
- `scripts/build_ec_index_filtered.py` - Fetch congressional hearing data
- `match_all_youtube_videos.py` - Match YouTube videos to hearings
- `scripts/generate_static_viewer.py` - Generate static HTML viewer

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Add Congress.gov API key to .env file:
echo "CONGRESS_API_KEY=your_key_here" > .env
```

## Current Status

- 919 YouTube videos extracted from Energy & Commerce channel
- 406 congressional hearings fetched (2013-2018)
- 192 videos matched (24.3% match rate)
- Missing data for Congress 117 (2021-2022) due to API issues
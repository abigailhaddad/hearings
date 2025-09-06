# YouTube-Congress Matcher

Automatically matches YouTube videos from congressional committee channels with official Congress.gov hearing records.

## Features

- 🎯 **Multi-committee support** - Process multiple committees in one run
- 📅 **Accurate date extraction** - Uses yt-dlp to get exact upload dates
- 🤖 **Smart matching** - Combines algorithmic scoring with LLM assistance
- 🔄 **Incremental processing** - Only processes new/changed data
- 📊 **Interactive viewer** - Browse matches and unmatched videos

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set up API key for Congress.gov
echo "CONGRESS_API_KEY=your_key_here" > .env

# Download YouTube HTML (see instructions below)

# Run the complete pipeline
./rebuild_all.sh
```

## Configuration

### Setting Active Committees

Edit `committees_config.yaml` to choose which committees to process:

```yaml
active_committees:
  - energy_commerce
  # Uncomment to add more:
  # - judiciary
  # - ways_means
  # - foreign_affairs
```

Available committees include all 21 major House committees plus select committees.

### Downloading YouTube Data

For each active committee:

1. Go to the committee's YouTube channel videos page
2. Scroll down to load all videos you want to capture
3. Save the page: **File → Save Page As → "Webpage, Complete"**
4. Use the exact filename specified in `committees_config.yaml`
   - Example: `House Committee on Energy and Commerce - YouTube.html`

## Pipeline Steps

The `rebuild_all.sh` script runs these steps automatically:

### 1. Fetch Congressional Data (One-time)
```bash
python scripts/fetch_all_congress_meetings.py
```
Downloads ALL House committee meetings from Congress.gov (takes ~10-15 minutes first time).

### 2. Filter Committee Data
```bash
python scripts/filter_committee_from_master.py
```
Quickly extracts data for active committees from the master dataset.

### 3. Parse YouTube HTML
```bash
python scripts/parse_youtube_html_multi.py
```
Extracts video IDs and titles from saved YouTube HTML files.

### 4. Get Exact Dates
```bash
python scripts/update_video_dates_ytdlp.py
```
Uses yt-dlp to fetch exact upload dates for each video (replaces approximate "2 months ago" dates).

### 5. Match Videos to Hearings
```bash
python scripts/match_with_llm.py
```
Matches videos with congressional hearings using:
- Date similarity (exact matches score highest)
- Title matching with fuzzy string comparison
- Event type detection (hearing, markup, etc.)
- LLM assistance for uncertain matches

### 6. Generate Viewer
```bash
python scripts/generate_static_viewer.py
```
Creates an interactive HTML viewer to browse results.

## File Structure

```
├── committees_config.yaml       # Committee configuration
├── rebuild_all.sh              # Main pipeline script
├── data/                       # YouTube video data
│   ├── energy_commerce_youtube_complete_dataset.json
│   ├── energy_commerce_youtube_videos_for_matching.json
│   └── youtube_congress_matches.json
├── outputs/                    # Congressional data
│   ├── all_house_meetings_master.json  # Master dataset (all committees)
│   ├── energy_commerce_filtered_index.json
│   └── .checkpoint_*           # Resume files for interrupted fetches
├── scripts/                    # Processing scripts
│   ├── fetch_all_congress_meetings.py
│   ├── filter_committee_from_master.py
│   ├── parse_youtube_html_multi.py
│   ├── update_video_dates_ytdlp.py
│   ├── match_with_llm.py
│   └── generate_static_viewer.py
├── index.html                  # Static viewer (generated)
└── viewer-simple.html          # Dynamic viewer template
```

## Adding New Committees

1. Edit `committees_config.yaml` and add the committee ID to `active_committees`
2. Download the committee's YouTube HTML with the exact filename from the config
3. Run `./rebuild_all.sh` - it will only process the new committee's data

## Requirements

- Python 3.7+
- Congress.gov API key (free from https://api.data.gov)
- OpenAI API key (or other LLM provider supported by litellm)

### LLM Configuration

Add your API key to `.env`:
```bash
OPENAI_API_KEY=your_key_here
# or for other providers:
ANTHROPIC_API_KEY=your_key_here
```

## Troubleshooting

### No matches found
- Check that yt-dlp is getting dates: `cd scripts && python update_video_dates_ytdlp.py`
- Verify your LLM API key is set correctly in `.env`

### Master dataset is old
- Re-fetch congressional data: `cd scripts && python fetch_all_congress_meetings.py --clean`

### Rate limiting
- The scripts include delays to avoid rate limits
- If you hit limits, wait a bit and the scripts will resume from checkpoints

## Current Coverage

- **Energy & Commerce**: 900+ videos matched
- **Data range**: Congress 113-119 (2013-2026)
- **Known limitations**: Some live streams may have incorrect dates

## License

MIT
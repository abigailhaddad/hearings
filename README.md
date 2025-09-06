# YouTube-Congress Matcher

Matches YouTube videos from congressional committee channels with Congress.gov hearing records.

## Quick Start

```bash
# Clean rebuild of all data (after downloading YouTube HTML)
./rebuild_all.sh
```

## Workflow

### 1. Data Collection

**YouTube Data:**
1. Go to committee YouTube channel (e.g., https://www.youtube.com/@HouseCommitteeEC/videos)
2. Save complete webpage: File → Save Page As → "Webpage, Complete"
3. Run `cd scripts && python parse_youtube_html.py <committee_name> <html_file>`
   - Example: `python parse_youtube_html.py energy_commerce "../House Committee on Energy and Commerce - YouTube.html"`

**Congressional Data:**
1. Get Congress.gov API key from https://api.data.gov
2. Add to `.env` file: `CONGRESS_API_KEY=your_key_here`
3. Run `cd scripts && python build_ec_index_filtered.py` to fetch hearing data

### 2. Matching Process

Run `cd scripts && python match_with_llm.py` to match videos with hearings using:
- Date matching (same day gets highest score)
- Title similarity using fuzzy string matching
- Event type detection (hearing, markup, etc.)
- LLM assistance for ambiguous matches

### 3. View Results

1. Generate static viewer: `cd scripts && python generate_static_viewer.py`
2. Open `index.html` in a browser to see matched videos with links

## File Structure

**Data files (in `data/`):**
- `<committee>_youtube_complete_dataset.json` - All extracted YouTube videos
- `<committee>_youtube_videos_for_matching.json` - Simplified dataset for matching
- `youtube_congress_matches.json` - Final matching results

**Output files (in `outputs/`):**
- `ec_filtered_index.json` - Congressional hearings from Congress.gov API

**Scripts (in `scripts/`):**
- `parse_youtube_html.py` - Extract videos from saved YouTube HTML (parameterized)
- `parse_ec_html_complete.py` - Legacy E&C-specific parser
- `build_ec_index_filtered.py` - Fetch congressional hearing data
- `match_with_llm.py` - Match YouTube videos to hearings with LLM assist
- `generate_static_viewer.py` - Generate static HTML viewer
- `export_matches.py` - Export results to CSV

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Add Congress.gov API key to .env file:
echo "CONGRESS_API_KEY=your_key_here" > .env
```

## Expanding to Other Committees

To process other committees:

1. Download their YouTube channel HTML
2. Update the committee name when running scripts:
   ```bash
   cd scripts
   python parse_youtube_html.py judiciary "../House Judiciary Committee - YouTube.html"
   ```
3. For congressional data, you'll need to modify `build_ec_index_filtered.py` to use different committee codes

## Requirements

- Python 3.7+
- Congress.gov API key
- litellm (for LLM-assisted matching)

## Current Status

- Energy & Commerce: ~900+ videos, ~700+ hearings indexed
- Known issue: Congress 117 (2021-2022) data unavailable due to API errors
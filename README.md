# YouTube-Congress Video Matcher

A tool for matching YouTube livestreams from congressional committees with official Congress.gov event records.

## Overview

This project matches YouTube videos from House committee channels with official congressional meeting data from the Congress.gov API. It currently focuses on the House Energy & Commerce Committee as a proof of concept.

**Status: Work in Progress** 🚧

## What It Does

- Fetches committee meeting data from the Congress.gov API
- Retrieves YouTube livestream videos from committee channels
- Matches videos to official events using:
  - Date matching (exact and fuzzy within a few days)
  - Title similarity analysis
  - Committee and event type matching
- Provides links to both YouTube videos and Congress.gov event pages

## Quick Start

1. Set up environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Set your Congress API key:
```bash
export CONGRESS_API_KEY="your_api_key_here"
```

3. Run the matching process:
```bash
cd scripts
python match_with_expanded_index.py
```

4. View results:
   - **Online**: Visit https://abigailhaddad.github.io/hearings/ (static viewer)
   - **Local** (with dynamic features): 
     ```bash
     cd ..
     python3 -m http.server 8000
     # Open http://localhost:8000/viewer-dynamic.html
     ```

5. Regenerate static viewer after updates:
```bash
cd scripts
python3 generate_static_viewer.py
```

## Project Structure

- `index.html` - Static web viewer with embedded data (works on GitHub Pages)
- `viewer-dynamic.html` - Dynamic viewer that loads JSON files (requires local server)
- `scripts/` - Python scripts for data fetching and matching
- `outputs/` - Generated JSON data files
- `data/` - Raw Congress API data

## Current Results

- Successfully matching ~100% of fetched Energy & Commerce YouTube livestreams (92 videos)
- Provides direct links to both YouTube videos and Congress.gov event pages
- **Note:** Currently fetching only recent videos (~220 total), not the full channel history. Working on expanding coverage.

## Next Steps

- Extend to other House and Senate committees
- Improve matching algorithms
- Add more metadata extraction
- Create automated update system
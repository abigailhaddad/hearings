# YouTube-Congress Matching Workflow

This workflow extracts congressional committee videos from YouTube and matches them with Congress API data without hitting YouTube API rate limits.

## Overview

1. **Download YouTube Channel HTML** - Save the complete page with all videos
2. **Extract Video Metadata** - Parse HTML to get video IDs, titles, and dates
3. **Get Exact Dates** - Fetch precise upload dates for each video
4. **Match with Congress Data** - Find corresponding events in Congress API
5. **Display Results** - Show matched videos in web viewer

## Step-by-Step Process

### 1. Download YouTube Channel Page

1. Go to the committee's YouTube channel (e.g., https://www.youtube.com/@energyandcommerce/streams)
2. Scroll down to load ALL videos (YouTube loads ~30 at a time)
3. Keep scrolling until you see all historical videos
4. Save the complete page as HTML (File → Save Page As → Complete Web Page)
5. Save as `House Committee on Energy and Commerce - YouTube.html`

### 2. Extract Video Data

Run the parser to extract all video information:

```bash
./venv/bin/python parse_ec_html_complete.py
```

This creates:
- `ec_youtube_complete_dataset.json` - Full dataset with all metadata
- `ec_youtube_videos_for_matching.json` - Simplified format for matching

### 3. Get Exact Dates

YouTube shows relative dates ("1 month ago") in the HTML. To get exact dates:

```bash
./venv/bin/python update_all_video_dates.py
```

This fetches exact dates (e.g., "2025-07-22") for all videos and saves to:
- `ec_youtube_videos_with_exact_dates.json`

### 4. Match with Congress Data

Run the matching script to find corresponding Congress events:

```bash
./venv/bin/python match_all_youtube_videos.py
```

This creates:
- `youtube_congress_matches.json` - Contains matched and unmatched videos

### 5. View Results

Open the viewer in your browser:

```bash
python3 -m http.server 8001
# Then visit http://localhost:8001/viewer-dynamic.html
```

## Key Files

- **parse_ec_html_complete.py** - Extracts video data from saved HTML
- **update_all_video_dates.py** - Gets exact dates using simple HTTP requests
- **match_all_youtube_videos.py** - Matches YouTube videos with Congress events
- **viewer-dynamic.html** - Web interface to view matches

## Results

For the Energy & Commerce Committee:
- 919 total videos extracted
- 754 successfully matched with Congress data (82% match rate)
- Includes the FTC privacy hearing and other key events

## Notes

- No YouTube API key required
- Works around rate limits by using HTML parsing and simple requests
- Matching uses title similarity and date proximity
- Can be adapted for other committees by changing the channel URL
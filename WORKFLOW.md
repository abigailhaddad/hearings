# Congressional YouTube Video Matching Workflow

## Overview
This workflow matches YouTube livestreams from congressional committees to official Congress API meeting data.

## Workflow Steps

### 1. Fetch Congress API Data
```bash
# Build comprehensive index of Energy & Commerce meetings
python build_ec_index_filtered.py

# Output: ec_filtered_index.json (232 E&C events)
```

### 2. Fetch YouTube Livestreams  
```bash
# Fetch livestreams from all congressional committee channels
python fetch_committee_livestreams.py

# Output: all_committee_livestreams.json
```

### 3. Match Videos to Congress Events
```bash
# Match YouTube videos to Congress events
python match_with_expanded_index.py

# Output: youtube_congress_expanded_matches.json
```

## Results
- Match rate improved from 7.6% to 95.7%
- 88 out of 92 E&C videos successfully matched

## Key Files
- `build_ec_index_filtered.py` - Fetches E&C meetings from Congress API
- `fetch_committee_livestreams.py` - Gets YouTube livestreams from committee channels
- `match_with_expanded_index.py` - Matches YouTube videos to Congress events
- `find_committee_channels.py` - Finds YouTube channels for committees

## Committee System Codes
Energy & Commerce committee codes used:
- `hsif00` - Main committee
- `hsif02` - Oversight and Investigations 
- `hsif03` - Energy
- `hsif14` - Health
- `hsif16` - Communications and Technology
- `hsif17` - Commerce, Manufacturing, and Trade
- `hsif18` - Environment
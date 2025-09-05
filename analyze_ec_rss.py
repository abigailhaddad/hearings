#!/usr/bin/env python3
"""Analyze House Energy & Commerce Committee RSS data"""

import json
from collections import Counter
from datetime import datetime

# Load the RSS data
with open('rss_committee_videos.json', 'r') as f:
    data = json.load(f)

print('HOUSE ENERGY & COMMERCE COMMITTEE - RSS DATA ANALYSIS')
print('=' * 70)
print(f"Total videos fetched: {data['metadata']['total_videos']}")
print(f"Potential livestreams: {data['metadata']['potential_livestreams']}")
print(f"Channel ID: UC5s1kIfkfWbap31d5ef-VtQ")
print(f"RSS URL: https://www.youtube.com/feeds/videos.xml?channel_id=UC5s1kIfkfWbap31d5ef-VtQ")

# Analyze video types
print('\n\nVIDEO ANALYSIS:')
print('-' * 70)

# Count video types
video_types = Counter()
for video in data['videos']:
    if 'shorts' in video['url']:
        video_types['shorts'] += 1
    elif video.get('livestream_confidence'):
        video_types['likely_livestream'] += 1
    else:
        video_types['regular'] += 1

print(f"Shorts: {video_types['shorts']}")
print(f"Likely livestreams: {video_types['likely_livestream']}")
print(f"Regular videos: {video_types['regular']}")

# Show all videos
print('\n\nALL VIDEOS:')
print('-' * 70)
for i, video in enumerate(data['videos']):
    confidence = video.get('livestream_confidence', '')
    video_type = 'SHORT' if 'shorts' in video['url'] else 'LIVESTREAM' if confidence else 'VIDEO'
    
    print(f"\n[{video_type}] {video['title']}")
    print(f"   Published: {video['publishedAt'][:16]}")
    print(f"   Views: {video['viewCount']}")
    print(f"   URL: {video['url']}")
    if confidence:
        print(f"   Livestream confidence: {confidence}")

# Extract patterns
print('\n\nCOMMON TITLE PATTERNS:')
print('-' * 70)
patterns = {
    'Hearing': 0,
    'Markup': 0,
    'Opening Statement': 0,
    'Subcommittee': 0,
    'Full Committee': 0,
    'Briefing': 0
}

for video in data['videos']:
    title = video['title']
    for pattern in patterns:
        if pattern.lower() in title.lower():
            patterns[pattern] += 1

for pattern, count in sorted(patterns.items(), key=lambda x: x[1], reverse=True):
    if count > 0:
        print(f"{pattern}: {count} videos")
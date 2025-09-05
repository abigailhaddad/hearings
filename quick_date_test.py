#!/usr/bin/env python3
"""
Quick test to see if we can get dates efficiently
"""

import json
import subprocess

# Test with just a few videos
with open('ec_youtube_videos_for_matching.json', 'r') as f:
    videos = json.load(f)

# Test first video without a date
for video in videos[:10]:
    if not video.get('approximate_date'):
        print(f"\nChecking: {video['title'][:50]}...")
        print(f"Video ID: {video['video_id']}")
        
        # Try to get just the upload date quickly
        cmd = [
            './venv/bin/yt-dlp',
            '--print', 'upload_date,release_date,was_live',
            '--no-download',
            f'https://www.youtube.com/watch?v={video["video_id"]}'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"Result: {result.stdout.strip()}")
        else:
            print(f"Error: {result.stderr}")
        
        break
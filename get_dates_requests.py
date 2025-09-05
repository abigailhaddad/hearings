#!/usr/bin/env python3
"""
Get exact dates from YouTube videos using requests (no browser needed)
"""

import json
import requests
import re
from bs4 import BeautifulSoup

def get_video_date_from_page(video_id):
    """Extract date from YouTube video page HTML"""
    
    url = f'https://www.youtube.com/watch?v={video_id}'
    
    try:
        # Simple request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            # Look for date patterns in the HTML
            
            # Method 1: Look for uploadDate in JSON-LD
            upload_date_match = re.search(r'"uploadDate"\s*:\s*"([^"]+)"', response.text)
            if upload_date_match:
                return upload_date_match.group(1)[:10]  # Get YYYY-MM-DD
            
            # Method 2: Look for publishDate
            publish_date_match = re.search(r'"publishDate"\s*:\s*"([^"]+)"', response.text)
            if publish_date_match:
                return publish_date_match.group(1)[:10]
            
            # Method 3: Look for datePublished
            date_published_match = re.search(r'"datePublished"\s*:\s*"([^"]+)"', response.text)
            if date_published_match:
                return date_published_match.group(1)[:10]
            
            # Method 4: Look in ytInitialData
            initial_data_match = re.search(r'ytInitialData\s*=\s*({.*?});', response.text)
            if initial_data_match:
                try:
                    data = json.loads(initial_data_match.group(1))
                    # Navigate to find date - this path may vary
                    # Look for microformat data
                    microformat = data.get('microformat', {}).get('playerMicroformatRenderer', {})
                    if microformat:
                        upload_date = microformat.get('uploadDate', '')
                        publish_date = microformat.get('publishDate', '')
                        return upload_date[:10] if upload_date else publish_date[:10] if publish_date else None
                except:
                    pass
            
    except Exception as e:
        print(f"Error fetching {video_id}: {e}")
    
    return None

# Test with a few videos
if __name__ == "__main__":
    print("🧪 Testing date extraction with requests...\n")
    
    # Load videos
    with open('ec_youtube_videos_for_matching.json', 'r') as f:
        videos = json.load(f)
    
    # Test first 5 videos
    test_videos = [v for v in videos if not v.get('approximate_date')][:5]
    
    for video in test_videos:
        print(f"Video: {video['title'][:50]}...")
        print(f"ID: {video['video_id']}")
        
        date = get_video_date_from_page(video['video_id'])
        if date:
            print(f"✓ Date found: {date}")
        else:
            print(f"✗ No date found")
        print()
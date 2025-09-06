#!/usr/bin/env python3
"""
Update all YouTube videos with exact dates using requests
"""

import json
import requests
import re
from tqdm import tqdm
import time

def get_video_date_from_page(video_id):
    """Extract date from YouTube video page HTML"""
    
    url = f'https://www.youtube.com/watch?v={video_id}'
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            # Look for uploadDate in JSON-LD
            upload_date_match = re.search(r'"uploadDate"\s*:\s*"([^"]+)"', response.text)
            if upload_date_match:
                return upload_date_match.group(1)[:10]
            
            # Look for publishDate  
            publish_date_match = re.search(r'"publishDate"\s*:\s*"([^"]+)"', response.text)
            if publish_date_match:
                return publish_date_match.group(1)[:10]
                
            # Look for datePublished
            date_published_match = re.search(r'"datePublished"\s*:\s*"([^"]+)"', response.text)
            if date_published_match:
                return date_published_match.group(1)[:10]
            
    except Exception as e:
        return None
    
    return None

def update_all_videos():
    """Update all videos with exact dates"""
    
    print("📂 Loading video data...")
    with open('../data/ec_youtube_videos_for_matching.json', 'r') as f:
        videos = json.load(f)
    
    print(f"📹 Found {len(videos)} total videos")
    
    # Count how many need dates
    videos_needing_exact_dates = [v for v in videos if not v.get('exact_date')]
    print(f"🔍 {len(videos_needing_exact_dates)} videos need exact dates")
    
    # Update videos
    updated_count = 0
    failed_count = 0
    save_interval = 50  # Save every 50 videos
    
    for i, video in enumerate(tqdm(videos, desc="Getting dates")):
        # Skip if we already have an exact date
        if not video.get('exact_date'):
            # Need to fetch date
            date = get_video_date_from_page(video['video_id'])
            
            if date:
                video['exact_date'] = date
                video['approximate_date'] = date  # Update to exact date
                updated_count += 1
            else:
                failed_count += 1
            
            # Small delay to avoid rate limiting
            time.sleep(0.5)
        
        # Save periodically
        if (i + 1) % save_interval == 0:
            with open('../data/ec_youtube_videos_with_exact_dates.json', 'w') as f:
                json.dump(videos, f, indent=2)
            print(f"\n💾 Progress saved: {updated_count} dates found so far...")
    
    # Final save
    with open('../data/ec_youtube_videos_with_exact_dates.json', 'w') as f:
        json.dump(videos, f, indent=2)
    
    print(f"\n✅ Successfully updated {updated_count} videos with exact dates")
    print(f"❌ Failed to get dates for {failed_count} videos")
    print(f"💾 Saved to: ../data/ec_youtube_videos_with_exact_dates.json")
    
    # Show some examples
    print("\n📋 Sample videos with dates:")
    videos_with_dates = [v for v in videos if v.get('exact_date')]
    for v in videos_with_dates[:5]:
        print(f"\n  {v['title'][:60]}...")
        print(f"  Date: {v['exact_date']}")

if __name__ == "__main__":
    update_all_videos()
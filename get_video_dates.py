#!/usr/bin/env python3
"""
Get dates for YouTube videos using yt-dlp (no API needed)
"""

import json
import subprocess
from datetime import datetime
from tqdm import tqdm

def get_video_info_ytdlp(video_id):
    """Get video metadata using yt-dlp"""
    try:
        # Use yt-dlp to get video info without downloading
        cmd = [
            './venv/bin/yt-dlp',
            '--dump-json',
            '--no-download',
            f'https://www.youtube.com/watch?v={video_id}'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            
            # Extract relevant fields
            upload_date = data.get('upload_date', '')  # Format: YYYYMMDD
            if upload_date:
                # Convert to YYYY-MM-DD
                upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
            
            # For live streams, check for release_date or timestamp
            release_date = data.get('release_date', '')
            if release_date:
                release_date = f"{release_date[:4]}-{release_date[4:6]}-{release_date[6:8]}"
            
            # Use release_date if available (for livestreams), otherwise upload_date
            actual_date = release_date or upload_date
            
            return {
                'upload_date': upload_date,
                'release_date': release_date,
                'actual_date': actual_date,
                'title': data.get('title', ''),
                'duration': data.get('duration', 0),
                'view_count': data.get('view_count', 0),
                'was_live': data.get('was_live', False)
            }
    except Exception as e:
        print(f"Error getting info for {video_id}: {e}")
    
    return None

def update_videos_with_dates():
    """Update all videos with date information"""
    
    # Check if yt-dlp is installed
    try:
        subprocess.run(['./venv/bin/yt-dlp', '--version'], capture_output=True, check=True)
    except:
        print("❌ yt-dlp is not installed!")
        print("Install with: pip install yt-dlp")
        return
    
    # Load existing video data
    print("📂 Loading video data...")
    with open('ec_youtube_videos_for_matching.json', 'r') as f:
        videos = json.load(f)
    
    print(f"📹 Found {len(videos)} videos to update")
    
    # Update videos with dates
    updated_videos = []
    videos_without_dates = [v for v in videos if not v.get('approximate_date')]
    
    print(f"🔍 Need to fetch dates for {len(videos_without_dates)} videos")
    
    # Process in batches to show progress
    for video in tqdm(videos, desc="Fetching dates"):
        if video.get('approximate_date'):
            # Already has a date
            updated_videos.append(video)
        else:
            # Fetch date info
            info = get_video_info_ytdlp(video['video_id'])
            
            if info:
                video['upload_date'] = info['upload_date']
                video['actual_date'] = info['actual_date']
                video['approximate_date'] = info['actual_date']  # For compatibility
                video['was_live'] = info['was_live']
                video['duration_seconds'] = info['duration']
                video['view_count'] = info['view_count']
            
            updated_videos.append(video)
    
    # Save updated data
    with open('ec_youtube_videos_with_all_dates.json', 'w') as f:
        json.dump(updated_videos, f, indent=2)
    
    # Count results
    videos_with_dates = len([v for v in updated_videos if v.get('actual_date')])
    
    print(f"\n✅ Updated {videos_with_dates} videos with dates ({videos_with_dates/len(updated_videos)*100:.1f}%)")
    print(f"💾 Saved to: ec_youtube_videos_with_all_dates.json")
    
    # Show sample
    print("\n📋 Sample videos with dates:")
    for v in [v for v in updated_videos if v.get('actual_date')][:5]:
        print(f"\n  {v['title'][:60]}...")
        print(f"  Date: {v['actual_date']}")
        print(f"  Live: {'Yes' if v.get('was_live') else 'No'}")

if __name__ == "__main__":
    # For testing, just get a few videos first
    print("🧪 Testing with first 3 videos without dates...")
    
    with open('ec_youtube_videos_for_matching.json', 'r') as f:
        videos = json.load(f)
    
    test_count = 0
    for video in videos:
        if not video.get('approximate_date'):
            print(f"\nTesting: {video['title'][:50]}...")
            info = get_video_info_ytdlp(video['video_id'])
            if info:
                print(f"  Date: {info['actual_date']}")
                print(f"  Was Live: {info['was_live']}")
            test_count += 1
            if test_count >= 3:
                break
    
    print("\n" + "="*70)
    print("Starting full update...")
    update_videos_with_dates()
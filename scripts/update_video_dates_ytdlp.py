#!/usr/bin/env python3
"""
Update YouTube videos with exact dates using yt-dlp
Works with the multi-committee YAML configuration
"""

import json
import subprocess
import os
import yaml
from datetime import datetime
from tqdm import tqdm
import sys
import time

def load_committee_config():
    """Load committee configuration from YAML file"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'committees_config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def get_video_info_ytdlp(video_id, yt_dlp_path='yt-dlp'):
    """Get video metadata using yt-dlp"""
    try:
        # Use yt-dlp to get video info without downloading
        cmd = [
            yt_dlp_path,
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

def find_yt_dlp():
    """Find yt-dlp executable"""
    # Try various paths
    paths_to_try = [
        './venv/bin/yt-dlp',
        'yt-dlp',
        'youtube-dl',  # Fallback to youtube-dl if available
        './venv/bin/youtube-dl'
    ]
    
    for path in paths_to_try:
        try:
            result = subprocess.run([path, '--version'], capture_output=True)
            if result.returncode == 0:
                return path
        except:
            continue
    
    return None

def update_committee_videos(committee_id, root_dir, yt_dlp_path, force=False):
    """Update videos for a specific committee with exact dates"""
    
    # Input file
    input_file = os.path.join(root_dir, 'data', f'{committee_id}_youtube_videos_for_matching.json')
    
    if not os.path.exists(input_file):
        print(f"  ❌ No video data found for {committee_id}")
        return False
    
    # Check if we already have dates
    with open(input_file, 'r') as f:
        videos = json.load(f)
    
    # Count videos needing dates
    videos_needing_dates = [v for v in videos if not v.get('exact_date') and not v.get('actual_date')]
    
    if not videos_needing_dates and not force:
        print(f"  ✓ All {len(videos)} videos already have dates")
        return True
    
    print(f"  📹 Found {len(videos)} videos, {len(videos_needing_dates)} need dates")
    
    # Process videos
    updated_count = 0
    failed_count = 0
    
    for video in tqdm(videos, desc=f"  Getting dates for {committee_id}", disable=len(videos_needing_dates) == 0):
        # Skip if we already have exact date (unless forced)
        if (video.get('exact_date') or video.get('actual_date')) and not force:
            continue
        
        # Fetch date info
        info = get_video_info_ytdlp(video['video_id'], yt_dlp_path)
        
        if info:
            video['upload_date'] = info['upload_date']
            video['actual_date'] = info['actual_date']
            video['exact_date'] = info['actual_date']  # For compatibility
            # Update approximate_date to be exact
            video['approximate_date'] = info['actual_date']
            video['was_live'] = info['was_live']
            video['duration_seconds'] = info['duration']
            video['view_count'] = info['view_count']
            updated_count += 1
        else:
            failed_count += 1
        
        # Small delay to be nice to YouTube
        time.sleep(0.5)
        
        # Save periodically (every 50 videos)
        if updated_count % 50 == 0 and updated_count > 0:
            with open(input_file, 'w') as f:
                json.dump(videos, f, indent=2)
            print(f"\n  💾 Progress saved: {updated_count} dates found so far...")
    
    # Final save
    with open(input_file, 'w') as f:
        json.dump(videos, f, indent=2)
    
    if updated_count > 0:
        print(f"  ✅ Updated {updated_count} videos with exact dates")
    if failed_count > 0:
        print(f"  ⚠️  Failed to get dates for {failed_count} videos")
    
    return True

def main():
    """Update all active committees with exact video dates"""
    
    print("🎯 YouTube Video Date Updater (using yt-dlp)")
    print("=" * 70)
    
    # Find yt-dlp
    yt_dlp_path = find_yt_dlp()
    
    if not yt_dlp_path:
        print("❌ yt-dlp not found!")
        print("\nPlease install yt-dlp:")
        print("  pip install yt-dlp")
        print("\nOr if you're using the venv:")
        print("  ./venv/bin/pip install yt-dlp")
        sys.exit(1)
    
    print(f"✅ Found yt-dlp at: {yt_dlp_path}")
    
    # Get root directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    
    # Load committee configuration
    config = load_committee_config()
    active_committees = config['active_committees']
    committees_info = config['committees']
    
    print(f"\n📋 Active committees: {', '.join(active_committees)}")
    
    # Process each committee
    for committee_id in active_committees:
        if committee_id not in committees_info:
            print(f"\n❌ Committee '{committee_id}' not found in configuration")
            continue
        
        committee_name = committees_info[committee_id]['short_name']
        print(f"\n📂 Processing: {committee_name}")
        
        update_committee_videos(committee_id, root_dir, yt_dlp_path, force='--force' in sys.argv)
    
    print("\n✅ Date update complete!")
    print("\nNow run the matching script to use these exact dates")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Fetch YouTube livestreams from all congressional committee channels
"""

import json
import os
import time
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()
API_KEY = os.environ.get('YOUTUBE_API_KEY')

# Committee channels we found
COMMITTEE_CHANNELS = {
    'UCVvQkEb8GkqB14I5oLNEk3A': 'House Armed Services Committee',
    'UCL6Clx5s9O-FkJewfM65tzQ': 'House Foreign Affairs Committee',
    'UCa-Al3CKLjRCQKhtfbn_FUg': 'House Financial Services Committee',
    'UC8vKJ3p4FExYEj5OFsQAJlw': 'House Science Committee', 
    'UCPxvyZJblT2cz8g9SLtyXtA': 'House Veterans Affairs Committee',
    'UCQtsiDrwfsEfX9EztXvA1ww': 'House Natural Resources Committee',
    'UCiQcpX6mJwB6OwBL_jLNjDQ': 'House Administration Committee',
    'UC5s1kIfkfWbap31d5ef-VtQ': 'House Energy and Commerce Committee',
    'UC5Z9wT6onnCFenRzCQ0TiGg': 'Senate Finance Committee',
    'UCCBJESjTTWeGSifHHq_VT6A': 'Senate Armed Services Committee',
    'UCUlGq0zaT3gYiVdBIGXl-EQ': 'Senate Commerce Committee',
    'UCVlD1YGzy1FqUlgEwzNuE5A': 'Senate Judiciary Committee',
    'UCcSGCxGOOBoq4PrAahRlhZg': 'Senate Foreign Relations Committee',
    'UCdp4NBEw65xGYkKh1tAH73g': 'Senate Environment and Public Works',
    'UCmIBKDO8H5Z88cFvQ1RTkGA': 'Senate Budget Committee',
    'UCqIKINGgWZ0Hv11O0zzLLpw': 'Senate Banking Committee',
    'UCzxJy_xgDLJCqcCYjdF8wNw': 'Senate Veterans Affairs Committee',
    'UCrBJdS5FAyGq6rGwJlCyJ3A': 'Oversight Committee (House)',
    'UCU6w8CfBGPSHNOeeHRb5t1A': 'House Judiciary Committee'
}

def fetch_channel_livestreams(youtube, channel_id, channel_name, max_results=500):
    """Fetch livestreams from a YouTube channel"""
    
    videos = []
    livestreams = []
    next_page = None
    
    print(f"\n📺 Fetching videos from {channel_name}...")
    
    try:
        # First, get the uploads playlist ID
        channel_resp = youtube.channels().list(
            part="contentDetails",
            id=channel_id
        ).execute()
        
        if not channel_resp.get('items'):
            print(f"   ⚠️  Channel not found: {channel_id}")
            return []
            
        uploads_playlist_id = channel_resp['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        
        # Get all videos from uploads playlist
        while len(videos) < max_results:
            playlist_resp = youtube.playlistItems().list(
                part="snippet",
                playlistId=uploads_playlist_id,
                maxResults=50,
                pageToken=next_page
            ).execute()
            
            items = playlist_resp.get('items', [])
            if not items:
                break
                
            # Get video IDs
            video_ids = [item['snippet']['resourceId']['videoId'] for item in items]
            
            # Get full video details including live streaming info
            videos_resp = youtube.videos().list(
                part="snippet,liveStreamingDetails,contentDetails,statistics",
                id=','.join(video_ids)
            ).execute()
            
            for video in videos_resp.get('items', []):
                videos.append(video)
                
                # Only include if it has live streaming details
                if 'liveStreamingDetails' in video:
                    video_data = {
                        'id': video['id'],
                        'title': video['snippet']['title'],
                        'publishedAt': video['snippet']['publishedAt'],
                        'description': video['snippet']['description'][:500],
                        'channelId': channel_id,
                        'channelName': channel_name,
                        'duration': video['contentDetails']['duration'],
                        'viewCount': video['statistics'].get('viewCount', '0'),
                        'liveStreamingDetails': video['liveStreamingDetails']
                    }
                    livestreams.append(video_data)
            
            # Check for next page
            next_page = playlist_resp.get('nextPageToken')
            if not next_page:
                break
                
            print(f"   Checked {len(videos)} videos, found {len(livestreams)} livestreams...")
            time.sleep(0.5)  # Rate limiting
            
    except HttpError as e:
        print(f"   ❌ Error fetching channel: {e}")
    
    return livestreams

def main():
    if not API_KEY:
        print("❌ Please set YOUTUBE_API_KEY environment variable")
        return
        
    youtube = build('youtube', 'v3', developerKey=API_KEY)
    
    all_livestreams = []
    channel_stats = {}
    
    print(f"🎬 Fetching livestreams from {len(COMMITTEE_CHANNELS)} congressional committee channels")
    print("=" * 70)
    
    # Process each channel
    for channel_id, channel_name in tqdm(COMMITTEE_CHANNELS.items(), desc="Channels"):
        livestreams = fetch_channel_livestreams(youtube, channel_id, channel_name)
        
        if livestreams:
            all_livestreams.extend(livestreams)
            channel_stats[channel_name] = {
                'livestream_count': len(livestreams),
                'channel_id': channel_id,
                'earliest_stream': min(v['liveStreamingDetails'].get('actualStartTime', v['publishedAt']) for v in livestreams),
                'latest_stream': max(v['liveStreamingDetails'].get('actualStartTime', v['publishedAt']) for v in livestreams)
            }
            
            print(f"   ✅ {channel_name}: {len(livestreams)} livestreams found")
        else:
            print(f"   ⚠️  {channel_name}: No livestreams found")
    
    # Save all livestreams
    output = {
        'metadata': {
            'total_channels': len(COMMITTEE_CHANNELS),
            'total_livestreams': len(all_livestreams),
            'timestamp': datetime.now().isoformat(),
            'channel_stats': channel_stats
        },
        'videos': sorted(all_livestreams, key=lambda x: x.get('liveStreamingDetails', {}).get('actualStartTime', x.get('publishedAt', '')), reverse=True)
    }
    
    with open('all_committee_livestreams.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n✅ Complete!")
    print(f"   Total livestreams collected: {len(all_livestreams)}")
    print(f"   Saved to: all_committee_livestreams.json")
    
    # Show summary by committee
    print("\n📊 Summary by Committee (sorted by livestream count):")
    for name, stats in sorted(channel_stats.items(), key=lambda x: x[1]['livestream_count'], reverse=True):
        print(f"   {name}: {stats['livestream_count']} livestreams")
        print(f"      Date range: {stats['earliest_stream'][:10]} to {stats['latest_stream'][:10]}")
    
    # Show date coverage
    print("\n📅 Overall date coverage:")
    all_dates = []
    for v in all_livestreams:
        if v.get('liveStreamingDetails', {}).get('actualStartTime'):
            all_dates.append(v['liveStreamingDetails']['actualStartTime'][:10])
    
    if all_dates:
        all_dates.sort()
        print(f"   Earliest: {all_dates[0]}")
        print(f"   Latest: {all_dates[-1]}")
        print(f"   Unique dates: {len(set(all_dates))}")

if __name__ == "__main__":
    main()
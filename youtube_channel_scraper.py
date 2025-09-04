import os
import requests
import json
from typing import Dict, List, Optional
from datetime import datetime
from dotenv import load_dotenv
import time
from tqdm import tqdm

load_dotenv()

# You'll need to get a YouTube Data API key from Google Cloud Console
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')
BASE_URL = 'https://www.googleapis.com/youtube/v3'

def get_channel_id_from_handle(handle: str) -> Optional[str]:
    """Convert YouTube handle (e.g., @energyandcommerce) to channel ID"""
    if not YOUTUBE_API_KEY:
        raise ValueError("YOUTUBE_API_KEY environment variable not set")
    
    # Remove @ if present
    handle = handle.replace('@', '')
    
    # Search for channel by handle - try with full search term first
    search_terms = [
        f"@{handle}",  # Try with @ symbol
        f"House {handle}",  # Try with House prefix
        f"US House {handle}",  # Try with US House prefix
        handle  # Try just the handle
    ]
    
    for search_term in search_terms:
        url = f"{BASE_URL}/search"
        params = {
            'part': 'snippet',
            'q': search_term,
            'type': 'channel',
            'key': YOUTUBE_API_KEY,
            'maxResults': 10
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Print all found channels for debugging
        print(f"\nSearching for: {search_term}")
        for i, item in enumerate(data.get('items', [])):
            print(f"  {i+1}. {item['snippet']['channelTitle']} (ID: {item['snippet']['channelId']})")
        
        # Look for US House committee
        for item in data.get('items', []):
            title = item['snippet']['channelTitle']
            if 'house' in title.lower() and 'energy' in title.lower() and 'commerce' in title.lower():
                print(f"\n✅ Found US House Energy & Commerce: {title}")
                return item['snippet']['channelId']
    
    # If no exact match found, ask user to select
    print("\n⚠️  Could not find exact match. Please check channel ID manually.")
    return None

def get_channel_info(channel_id: str) -> Dict:
    """Get detailed channel information"""
    url = f"{BASE_URL}/channels"
    params = {
        'part': 'snippet,statistics,contentDetails',
        'id': channel_id,
        'key': YOUTUBE_API_KEY
    }
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    
    if data.get('items'):
        channel = data['items'][0]
        return {
            'id': channel['id'],
            'title': channel['snippet']['title'],
            'description': channel['snippet']['description'],
            'customUrl': channel['snippet'].get('customUrl'),
            'publishedAt': channel['snippet']['publishedAt'],
            'viewCount': channel['statistics'].get('viewCount'),
            'subscriberCount': channel['statistics'].get('subscriberCount'),
            'videoCount': channel['statistics'].get('videoCount'),
            'uploadsPlaylistId': channel['contentDetails']['relatedPlaylists']['uploads']
        }
    
    return {}

def get_channel_videos(channel_id: str, max_results: int = 50, include_live: bool = True) -> List[Dict]:
    """Get videos from a channel including live streams"""
    videos = []
    
    # Get uploads playlist ID
    channel_info = get_channel_info(channel_id)
    if not channel_info:
        return videos
    
    uploads_playlist_id = channel_info['uploadsPlaylistId']
    
    # Get videos from uploads playlist
    next_page_token = None
    
    with tqdm(total=max_results, desc="Fetching videos") as pbar:
        while len(videos) < max_results:
            url = f"{BASE_URL}/playlistItems"
            params = {
                'part': 'snippet,contentDetails',
                'playlistId': uploads_playlist_id,
                'key': YOUTUBE_API_KEY,
                'maxResults': min(50, max_results - len(videos))
            }
            
            if next_page_token:
                params['pageToken'] = next_page_token
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            video_ids = [item['contentDetails']['videoId'] for item in data.get('items', [])]
            
            if video_ids:
                # Get detailed video info
                video_details = get_video_details(video_ids)
                videos.extend(video_details)
                pbar.update(len(video_details))
            
            next_page_token = data.get('nextPageToken')
            if not next_page_token:
                break
            
            time.sleep(0.1)  # Rate limiting
    
    # Also search for live streams if requested
    if include_live:
        print("\n🔴 Searching for live streams...")
        live_streams = search_channel_live_streams(channel_id, max_results=20)
        videos.extend(live_streams)
    
    return videos

def get_video_details(video_ids: List[str]) -> List[Dict]:
    """Get detailed information for multiple videos"""
    url = f"{BASE_URL}/videos"
    params = {
        'part': 'snippet,statistics,contentDetails,liveStreamingDetails',
        'id': ','.join(video_ids),
        'key': YOUTUBE_API_KEY
    }
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    
    videos = []
    for item in data.get('items', []):
        video_info = {
            'id': item['id'],
            'title': item['snippet']['title'],
            'description': item['snippet']['description'],
            'publishedAt': item['snippet']['publishedAt'],
            'duration': item['contentDetails']['duration'],
            'viewCount': item['statistics'].get('viewCount', 0),
            'likeCount': item['statistics'].get('likeCount', 0),
            'commentCount': item['statistics'].get('commentCount', 0),
            'tags': item['snippet'].get('tags', []),
            'categoryId': item['snippet'].get('categoryId'),
            'liveBroadcastContent': item['snippet'].get('liveBroadcastContent')
        }
        
        # Add live streaming details if available
        if 'liveStreamingDetails' in item:
            video_info['liveStreamingDetails'] = {
                'actualStartTime': item['liveStreamingDetails'].get('actualStartTime'),
                'actualEndTime': item['liveStreamingDetails'].get('actualEndTime'),
                'scheduledStartTime': item['liveStreamingDetails'].get('scheduledStartTime'),
                'concurrentViewers': item['liveStreamingDetails'].get('concurrentViewers')
            }
        
        videos.append(video_info)
    
    return videos

def search_channel_live_streams(channel_id: str, max_results: int = 20) -> List[Dict]:
    """Search specifically for live streams from a channel"""
    url = f"{BASE_URL}/search"
    params = {
        'part': 'snippet',
        'channelId': channel_id,
        'eventType': 'completed',  # completed live streams
        'type': 'video',
        'order': 'date',
        'maxResults': max_results,
        'key': YOUTUBE_API_KEY
    }
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    
    video_ids = [item['id']['videoId'] for item in data.get('items', [])]
    
    if video_ids:
        return get_video_details(video_ids)
    
    return []

def main():
    """Main function to scrape YouTube channel data"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Scrape YouTube channel metadata')
    parser.add_argument('channel', help='YouTube channel URL or handle (e.g., @energyandcommerce)')
    parser.add_argument('--max-videos', type=int, default=50, help='Maximum number of videos to fetch')
    parser.add_argument('--output', help='Output JSON file (default: channel_handle.json)')
    
    args = parser.parse_args()
    
    print(f"\n📺 YouTube Channel Scraper")
    print(f"🔑 API Key: {'✅ Set' if YOUTUBE_API_KEY else '❌ Not Set'}")
    print("=" * 50)
    
    if not YOUTUBE_API_KEY:
        print("\n❌ Please set YOUTUBE_API_KEY in your .env file")
        print("Get one at: https://console.cloud.google.com/apis/credentials")
        return
    
    # Extract handle from URL if provided
    channel_input = args.channel
    if 'youtube.com' in channel_input:
        # Extract handle from URL
        if '/@' in channel_input:
            channel_input = '@' + channel_input.split('/@')[1].split('/')[0]
        elif '/channel/' in channel_input:
            channel_input = channel_input.split('/channel/')[1].split('/')[0]
    
    print(f"\n🔍 Looking up channel: {channel_input}")
    
    # Get channel ID
    if channel_input.startswith('@'):
        channel_id = get_channel_id_from_handle(channel_input)
    else:
        channel_id = channel_input  # Assume it's already a channel ID
    
    if not channel_id:
        print(f"❌ Could not find channel: {channel_input}")
        return
    
    # Get channel info
    print(f"\n📊 Fetching channel information...")
    channel_info = get_channel_info(channel_id)
    
    if channel_info:
        print(f"✅ Found channel: {channel_info['title']}")
        print(f"   Subscribers: {int(channel_info.get('subscriberCount', 0)):,}")
        print(f"   Total videos: {int(channel_info.get('videoCount', 0)):,}")
        print(f"   Total views: {int(channel_info.get('viewCount', 0)):,}")
    
    # Get videos
    print(f"\n📹 Fetching up to {args.max_videos} videos...")
    videos = get_channel_videos(channel_id, max_results=args.max_videos)
    
    # Prepare output
    output_data = {
        'channel': channel_info,
        'videos': videos,
        'metadata': {
            'scraped_date': datetime.now().isoformat(),
            'total_videos_fetched': len(videos),
            'live_streams_found': len([v for v in videos if v.get('liveStreamingDetails')])
        }
    }
    
    # Save to file
    output_file = args.output or f"{channel_input.replace('@', '').replace('/', '_')}.json"
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n✅ Data saved to {output_file}")
    print(f"📊 Summary:")
    print(f"   Videos fetched: {len(videos)}")
    print(f"   Live streams: {output_data['metadata']['live_streams_found']}")

if __name__ == "__main__":
    main()
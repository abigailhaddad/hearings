#!/usr/bin/env python3
"""
Scrape YouTube channel pages to get all videos (not just recent ones from RSS)
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re

def scrape_youtube_channel(channel_url):
    """
    Scrape YouTube channel page for video information
    Note: YouTube loads content dynamically, so basic scraping gets limited results
    """
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    }
    
    try:
        response = requests.get(channel_url, headers=headers)
        response.raise_for_status()
        
        # Look for initial data in the page
        videos = []
        
        # YouTube embeds initial data in script tags
        # Look for ytInitialData
        pattern = r'var ytInitialData = ({.*?});'
        match = re.search(pattern, response.text)
        
        if match:
            print("Found ytInitialData in page")
            # This would contain the initial video data
            # But parsing it requires complex JSON extraction
            
        # Alternative: Look for video IDs in the HTML
        video_id_pattern = r'/watch\?v=([a-zA-Z0-9_-]{11})'
        video_ids = re.findall(video_id_pattern, response.text)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_video_ids = []
        for vid in video_ids:
            if vid not in seen:
                seen.add(vid)
                unique_video_ids.append(vid)
        
        print(f"Found {len(unique_video_ids)} video IDs in initial page")
        
        # Extract any visible metadata
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for video titles and metadata
        # Note: This is limited because YouTube loads most content dynamically
        
        return unique_video_ids
        
    except Exception as e:
        print(f"Error scraping {channel_url}: {e}")
        return []

def get_video_info_from_rss(channel_id, video_ids):
    """
    Try to get video info for specific IDs using various methods
    """
    video_info = {}
    
    # For each video ID, we could:
    # 1. Check if it's in our RSS data
    # 2. Try to construct direct video URLs
    # 3. Use other non-API methods
    
    for video_id in video_ids:
        video_info[video_id] = {
            'id': video_id,
            'url': f'https://www.youtube.com/watch?v={video_id}',
            'title': 'Unknown',
            'channel_id': channel_id
        }
    
    return video_info

def main():
    print("🕷️ YouTube Channel Scraper (No API Required)")
    print("=" * 60)
    
    # E&C Committee channel
    channel_handle = "@energyandcommerce"
    channel_id = "UC5s1kIfkfWbap31d5ef-VtQ"
    
    # Different YouTube URLs to try
    urls_to_try = [
        f"https://www.youtube.com/{channel_handle}/videos",
        f"https://www.youtube.com/{channel_handle}/streams",
        f"https://www.youtube.com/channel/{channel_id}/videos",
        f"https://www.youtube.com/channel/{channel_id}/streams"
    ]
    
    all_video_ids = set()
    
    for url in urls_to_try:
        print(f"\nScraping: {url}")
        video_ids = scrape_youtube_channel(url)
        all_video_ids.update(video_ids)
        time.sleep(1)  # Be polite
    
    print(f"\n📊 Total unique video IDs found: {len(all_video_ids)}")
    
    # Try to get more info about these videos
    video_info = get_video_info_from_rss(channel_id, list(all_video_ids))
    
    # Save results
    output = {
        'channel': {
            'handle': channel_handle,
            'id': channel_id,
            'name': 'House Energy and Commerce Committee'
        },
        'scrape_time': time.strftime('%Y-%m-%d %H:%M:%S'),
        'total_videos_found': len(all_video_ids),
        'video_ids': list(all_video_ids),
        'videos': video_info
    }
    
    with open('scraped_channel_videos.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n💾 Saved to: scraped_channel_videos.json")
    
    # Important note about limitations
    print("\n⚠️  Note: Basic web scraping has limitations:")
    print("   - YouTube loads most content dynamically with JavaScript")
    print("   - Only initial page content is accessible without browser automation")
    print("   - For complete historical data, consider:")
    print("     1. Using Selenium/Playwright for dynamic content")
    print("     2. YouTube Data API (with rate limits)")
    print("     3. Third-party YouTube data services")

if __name__ == "__main__":
    main()
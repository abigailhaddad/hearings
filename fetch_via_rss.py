#!/usr/bin/env python3
"""
Fetch YouTube videos from congressional committee channels using RSS feeds
No API key required - avoids rate limits
"""

import requests
import xml.etree.ElementTree as ET
import json
from datetime import datetime
import time
from urllib.parse import urlparse, parse_qs

# Committee channels from your existing data
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

def parse_youtube_duration(duration_str):
    """Convert YouTube duration format (PT4H30M15S) to seconds"""
    if not duration_str or not duration_str.startswith('PT'):
        return None
    
    duration_str = duration_str[2:]  # Remove PT prefix
    hours = minutes = seconds = 0
    
    if 'H' in duration_str:
        hours, duration_str = duration_str.split('H')
        hours = int(hours)
    if 'M' in duration_str:
        minutes, duration_str = duration_str.split('M')
        minutes = int(minutes)
    if 'S' in duration_str:
        seconds = duration_str.replace('S', '')
        seconds = int(seconds) if seconds else 0
    
    return hours * 3600 + minutes * 60 + seconds

def fetch_channel_rss(channel_id, channel_name):
    """Fetch videos from YouTube channel RSS feed"""
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Parse XML
        root = ET.fromstring(response.content)
        
        # Define namespaces
        namespaces = {
            'atom': 'http://www.w3.org/2005/Atom',
            'media': 'http://search.yahoo.com/mrss/',
            'yt': 'http://www.youtube.com/xml/schemas/2015'
        }
        
        videos = []
        entries = root.findall('atom:entry', namespaces)
        
        print(f"📺 {channel_name}: Found {len(entries)} recent videos")
        
        for entry in entries:
            video_id = entry.find('yt:videoId', namespaces).text
            title = entry.find('atom:title', namespaces).text
            published = entry.find('atom:published', namespaces).text
            updated = entry.find('atom:updated', namespaces).text
            
            # Get video link
            link = entry.find('atom:link[@rel="alternate"]', namespaces)
            video_url = link.get('href') if link is not None else f"https://www.youtube.com/watch?v={video_id}"
            
            # Get description
            media_group = entry.find('media:group', namespaces)
            description = ''
            if media_group is not None:
                desc_elem = media_group.find('media:description', namespaces)
                if desc_elem is not None and desc_elem.text:
                    description = desc_elem.text[:500]
            
            # Get statistics
            stats = entry.find('media:community', namespaces)
            view_count = '0'
            if stats is not None:
                starrating = stats.find('media:starRating', namespaces)
                statistics = stats.find('media:statistics', namespaces)
                if statistics is not None:
                    view_count = statistics.get('views', '0')
            
            video_data = {
                'id': video_id,
                'title': title,
                'publishedAt': published,
                'updatedAt': updated,
                'description': description,
                'channelId': channel_id,
                'channelName': channel_name,
                'viewCount': view_count,
                'url': video_url,
                'source': 'rss'
            }
            
            videos.append(video_data)
        
        return videos
        
    except Exception as e:
        print(f"   ❌ Error fetching RSS for {channel_name}: {e}")
        return []

def check_for_livestreams(videos):
    """
    Check video titles and descriptions for livestream indicators
    RSS doesn't provide live streaming details, so we use heuristics
    """
    livestream_keywords = [
        'hearing', 'meeting', 'briefing', 'markup', 'committee',
        'subcommittee', 'live', 'stream', 'session', 'conference',
        'testimony', 'witnesses', 'oversight', 'investigation'
    ]
    
    potential_livestreams = []
    
    for video in videos:
        title_lower = video['title'].lower()
        desc_lower = video.get('description', '').lower()
        
        # Check if title/description contains livestream keywords
        is_likely_livestream = any(keyword in title_lower or keyword in desc_lower 
                                   for keyword in livestream_keywords)
        
        # Check for typical livestream title patterns
        has_date_pattern = any(month in title_lower for month in 
                               ['january', 'february', 'march', 'april', 'may', 'june',
                                'july', 'august', 'september', 'october', 'november', 'december'])
        
        # Long videos are more likely to be hearings
        is_long_video = False  # RSS doesn't provide duration directly
        
        if is_likely_livestream:
            video['livestream_confidence'] = 'high' if has_date_pattern else 'medium'
            potential_livestreams.append(video)
    
    return potential_livestreams

def discover_committee_channels():
    """
    Discover congressional committee YouTube channels through multiple methods
    """
    print("\n🔍 Discovering Congressional Committee YouTube Channels")
    print("=" * 70)
    
    discovered_channels = {}
    
    # Method 1: Check known government YouTube channels
    print("\n1️⃣ Checking known government channels...")
    known_gov_channels = {
        # House Committees
        'UC5s1kIfkfWbap31d5ef-VtQ': 'House Energy and Commerce Committee',
        'UCU6w8CfBGPSHNOeeHRb5t1A': 'House Judiciary Committee',
        'UCa-Al3CKLjRCQKhtfbn_FUg': 'House Financial Services Committee',
        'UCL6Clx5s9O-FkJewfM65tzQ': 'House Foreign Affairs Committee',
        'UCVvQkEb8GkqB14I5oLNEk3A': 'House Armed Services Committee',
        
        # Senate Committees
        'UCVlD1YGzy1FqUlgEwzNuE5A': 'Senate Judiciary Committee',
        'UC5Z9wT6onnCFenRzCQ0TiGg': 'Senate Finance Committee',
        'UCcSGCxGOOBoq4PrAahRlhZg': 'Senate Foreign Relations Committee',
    }
    
    # Verify each channel exists and is active
    for channel_id, channel_name in known_gov_channels.items():
        if verify_channel_via_rss(channel_id):
            discovered_channels[channel_id] = channel_name
            print(f"   ✅ Verified: {channel_name}")
        else:
            print(f"   ❌ Could not verify: {channel_name}")
    
    # Method 2: Parse congress.gov for YouTube links
    print("\n2️⃣ Searching congress.gov for YouTube channel links...")
    congress_youtube_links = search_congress_gov_for_youtube()
    discovered_channels.update(congress_youtube_links)
    
    # Method 3: Check committee websites for YouTube links
    print("\n3️⃣ Checking committee websites for social media links...")
    committee_websites = get_committee_websites()
    for site in committee_websites:
        youtube_links = extract_youtube_from_website(site)
        discovered_channels.update(youtube_links)
    
    return discovered_channels

def verify_channel_via_rss(channel_id):
    """Verify if a YouTube channel exists and has recent content via RSS"""
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            # Check if feed has entries
            entries = root.findall('{http://www.w3.org/2005/Atom}entry')
            return len(entries) > 0
    except:
        pass
    return False

def search_congress_gov_for_youtube():
    """Search congress.gov pages for YouTube channel links"""
    # This would require scraping congress.gov committee pages
    # For now, returning empty dict as placeholder
    print("   ℹ️  Would search committee pages on congress.gov for YouTube links")
    return {}

def get_committee_websites():
    """Get list of committee websites to check"""
    # Common committee website patterns
    committee_sites = [
        "https://energycommerce.house.gov",
        "https://judiciary.house.gov",
        "https://financialservices.house.gov",
        "https://foreignaffairs.house.gov",
        "https://armedservices.house.gov",
        "https://judiciary.senate.gov",
        "https://finance.senate.gov",
        "https://foreign.senate.gov",
    ]
    return committee_sites

def extract_youtube_from_website(url):
    """Extract YouTube channel links from a website"""
    channels = {}
    try:
        response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code == 200:
            # Look for YouTube links in the HTML
            import re
            youtube_patterns = [
                r'href=["\']?([^"\'>]*youtube\.com/channel/[^"\'>]+)',
                r'href=["\']?([^"\'>]*youtube\.com/c/[^"\'>]+)',
                r'href=["\']?([^"\'>]*youtube\.com/user/[^"\'>]+)',
                r'href=["\']?([^"\'>]*youtube\.com/@[^"\'>]+)',
            ]
            
            for pattern in youtube_patterns:
                matches = re.findall(pattern, response.text)
                for match in matches:
                    channel_id = extract_channel_id_from_url(match)
                    if channel_id and verify_channel_via_rss(channel_id):
                        # Get committee name from URL
                        committee_name = url.split('//')[1].split('.')[0].replace('-', ' ').title()
                        channels[channel_id] = f"{committee_name} Committee"
                        print(f"      Found YouTube channel for {committee_name}")
    except Exception as e:
        print(f"      Could not fetch {url}: {str(e)}")
    
    return channels

def extract_channel_id_from_url(url):
    """Extract channel ID from various YouTube URL formats"""
    import re
    
    # Pattern for channel URLs
    patterns = [
        r'youtube\.com/channel/([a-zA-Z0-9_-]+)',
        r'youtube\.com/c/([a-zA-Z0-9_-]+)',
        r'youtube\.com/user/([a-zA-Z0-9_-]+)',
        r'youtube\.com/@([a-zA-Z0-9_-]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def main():
    print("🎬 Congressional Committee YouTube Channel Discovery & RSS Feed Fetcher")
    print("=" * 70)
    print("✅ No API key required - No rate limits!")
    print()
    
    import sys
    
    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == 'discover':
        # Discovery mode
        discovered = discover_committee_channels()
        
        print(f"\n📊 Discovery Results:")
        print(f"   Found {len(discovered)} committee channels")
        
        # Save discovered channels
        with open('discovered_committee_channels.json', 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'channels': discovered,
                'rss_urls': {name: f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}" 
                            for cid, name in discovered.items()}
            }, f, indent=2)
        
        print(f"\n💾 Saved to: discovered_committee_channels.json")
        print("\n🔄 Run without 'discover' argument to fetch videos from these channels")
        return
    
    # Regular fetch mode
    print("📋 Using channels from COMMITTEE_CHANNELS constant")
    print(f"   Total channels: {len(COMMITTEE_CHANNELS)}")
    print("\n💡 Tip: Run with 'discover' argument to find new channels: python fetch_via_rss.py discover")
    print()
    
    all_videos = []
    all_livestreams = []
    channel_stats = {}
    
    # Fetch from each known channel
    for channel_id, channel_name in COMMITTEE_CHANNELS.items():
        videos = fetch_channel_rss(channel_id, channel_name)
        
        if videos:
            all_videos.extend(videos)
            
            # Check for livestreams
            livestreams = check_for_livestreams(videos)
            all_livestreams.extend(livestreams)
            
            channel_stats[channel_name] = {
                'channel_id': channel_id,
                'total_videos': len(videos),
                'potential_livestreams': len(livestreams),
                'latest_video': videos[0]['publishedAt'] if videos else None,
                'rss_url': f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
            }
        
        time.sleep(0.5)  # Be polite even though there's no rate limit
    
    # Save results
    output = {
        'metadata': {
            'source': 'rss_feeds',
            'timestamp': datetime.now().isoformat(),
            'total_channels': len(COMMITTEE_CHANNELS),
            'total_videos': len(all_videos),
            'potential_livestreams': len(all_livestreams),
            'channel_stats': channel_stats
        },
        'videos': sorted(all_videos, key=lambda x: x['publishedAt'], reverse=True),
        'potential_livestreams': sorted(all_livestreams, key=lambda x: x['publishedAt'], reverse=True)
    }
    
    with open('rss_committee_videos.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n✅ Complete!")
    print(f"   Total videos collected: {len(all_videos)}")
    print(f"   Potential livestreams: {len(all_livestreams)}")
    print(f"   Saved to: rss_committee_videos.json")
    
    # Show summary
    print("\n📊 Channel Summary:")
    for name, stats in sorted(channel_stats.items(), key=lambda x: x[1]['potential_livestreams'], reverse=True):
        if stats['total_videos'] > 0:
            print(f"   {name}:")
            print(f"      Videos: {stats['total_videos']}")
            print(f"      Potential livestreams: {stats['potential_livestreams']}")
            print(f"      RSS URL: {stats['rss_url']}")
    
    # Save RSS URLs for easy access
    rss_urls = {name: stats['rss_url'] for name, stats in channel_stats.items()}
    with open('committee_rss_urls.json', 'w') as f:
        json.dump(rss_urls, f, indent=2)
    
    print(f"\n💡 RSS URLs saved to: committee_rss_urls.json")
    print("   You can add these to any RSS reader for real-time updates!")

if __name__ == "__main__":
    main()
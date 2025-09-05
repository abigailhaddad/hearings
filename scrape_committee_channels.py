#!/usr/bin/env python3
"""
Scrape Google to find congressional committee YouTube channels
No API keys required!
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
from urllib.parse import quote

def search_google_for_youtube_channel(committee_name, chamber):
    """Search Google for YouTube channel links"""
    
    # Build search query
    query = f'site:youtube.com/channel "{chamber} {committee_name}" official'
    url = f"https://www.google.com/search?q={quote(query)}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find YouTube channel links
        channel_ids = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            # Extract YouTube channel IDs
            match = re.search(r'youtube\.com/channel/([a-zA-Z0-9_-]+)', href)
            if match:
                channel_ids.append(match.group(1))
        
        return list(set(channel_ids))  # Remove duplicates
        
    except Exception as e:
        print(f"Error searching for {committee_name}: {e}")
        return []

def get_committees_to_search():
    """List of committees to search for"""
    committees = [
        # House
        ('House', 'Energy and Commerce Committee'),
        ('House', 'Judiciary Committee'),
        ('House', 'Financial Services Committee'),
        ('House', 'Foreign Affairs Committee'),
        ('House', 'Armed Services Committee'),
        ('House', 'Ways and Means Committee'),
        ('House', 'Appropriations Committee'),
        ('House', 'Budget Committee'),
        ('House', 'Education and Labor Committee'),
        ('House', 'Transportation and Infrastructure Committee'),
        ('House', 'Natural Resources Committee'),
        ('House', 'Science, Space, and Technology Committee'),
        ('House', 'Veterans Affairs Committee'),
        ('House', 'Homeland Security Committee'),
        ('House', 'Agriculture Committee'),
        ('House', 'Small Business Committee'),
        ('House', 'Rules Committee'),
        ('House', 'Oversight and Reform Committee'),
        
        # Senate
        ('Senate', 'Judiciary Committee'),
        ('Senate', 'Finance Committee'),
        ('Senate', 'Foreign Relations Committee'),
        ('Senate', 'Armed Services Committee'),
        ('Senate', 'Appropriations Committee'),
        ('Senate', 'Banking Committee'),
        ('Senate', 'Budget Committee'),
        ('Senate', 'Commerce Committee'),
        ('Senate', 'Energy and Natural Resources Committee'),
        ('Senate', 'Environment and Public Works Committee'),
        ('Senate', 'Health, Education, Labor, and Pensions Committee'),
        ('Senate', 'Homeland Security Committee'),
        ('Senate', 'Veterans Affairs Committee'),
        ('Senate', 'Agriculture Committee'),
        ('Senate', 'Rules Committee'),
    ]
    return committees

def verify_channel_id(channel_id):
    """Check if channel ID works with RSS feed"""
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        response = requests.get(rss_url, timeout=5)
        return response.status_code == 200
    except:
        return False

def main():
    print("🔍 Searching for Congressional Committee YouTube Channels via Google")
    print("=" * 70)
    
    committees = get_committees_to_search()
    discovered_channels = {}
    
    for chamber, committee in committees:
        print(f"\nSearching for: {chamber} {committee}")
        
        # Search Google
        channel_ids = search_google_for_youtube_channel(committee, chamber)
        
        if channel_ids:
            print(f"  Found {len(channel_ids)} potential channel(s)")
            
            # Verify each channel
            for channel_id in channel_ids:
                if verify_channel_id(channel_id):
                    discovered_channels[channel_id] = f"{chamber} {committee}"
                    print(f"  ✅ Verified: {channel_id}")
                    break  # Found working channel, move to next committee
                else:
                    print(f"  ❌ Invalid: {channel_id}")
        else:
            print(f"  ⚠️  No channels found")
        
        # Be polite to Google
        time.sleep(2)
    
    # Save results
    output = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'total_found': len(discovered_channels),
        'channels': discovered_channels,
        'rss_urls': {
            name: f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}"
            for cid, name in discovered_channels.items()
        }
    }
    
    with open('scraped_committee_channels.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n✅ Complete! Found {len(discovered_channels)} working channels")
    print("💾 Saved to: scraped_committee_channels.json")

if __name__ == "__main__":
    main()
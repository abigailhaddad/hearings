#!/usr/bin/env python3
"""
Manually search for congressional committee YouTube channels
"""

import json
import os
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.environ.get('YOUTUBE_API_KEY')

# Known committee search terms based on common patterns
COMMITTEE_SEARCHES = [
    # House committees
    "House Energy and Commerce Committee",
    "House Armed Services Committee", 
    "House Financial Services Committee",
    "House Foreign Affairs Committee",
    "House Judiciary Committee",
    "House Science Committee",
    "House Veterans Affairs Committee", 
    "House Natural Resources Committee",
    "House Oversight Committee",
    "House Administration Committee",
    "House Agriculture Committee",
    "House Appropriations Committee",
    "House Budget Committee",
    "House Education and Labor Committee",
    "House Ethics Committee",
    "House Homeland Security Committee",
    "House Intelligence Committee",
    "House Rules Committee",
    "House Small Business Committee",
    "House Transportation Committee",
    "House Ways and Means Committee",
    # Senate committees
    "Senate Finance Committee",
    "Senate Armed Services Committee",
    "Senate Commerce Committee", 
    "Senate Judiciary Committee",
    "Senate Foreign Relations Committee",
    "Senate Environment and Public Works",
    "Senate Budget Committee",
    "Senate Banking Committee",
    "Senate Veterans Affairs Committee",
    "Senate Agriculture Committee",
    "Senate Appropriations Committee",
    "Senate Energy Committee",
    "Senate Health Education Labor Pensions",
    "Senate Homeland Security Committee",
    "Senate Intelligence Committee",
    "Senate Rules Committee",
    "Senate Small Business Committee",
    # Alternative names/variations
    "energycommerce", # E&C custom URL
    "HouseCommerce",
    "SenateCommerce",
    "HouseForeignAffairs",
    "SenateForeign"
]

def search_for_channel(youtube, search_term):
    """Search for a YouTube channel by name"""
    try:
        search_response = youtube.search().list(
            q=search_term,
            part="id,snippet",
            type="channel",
            maxResults=5
        ).execute()
        
        channels = []
        for item in search_response.get('items', []):
            channel_id = item['id']['channelId']
            
            # Get full channel details
            channel_response = youtube.channels().list(
                part="snippet,statistics,contentDetails",
                id=channel_id
            ).execute()
            
            if channel_response.get('items'):
                channel = channel_response['items'][0]
                channels.append({
                    'id': channel_id,
                    'title': channel['snippet']['title'],
                    'customUrl': channel['snippet'].get('customUrl', ''),
                    'description': channel['snippet']['description'][:200],
                    'subscriberCount': channel['statistics'].get('subscriberCount', '0'),
                    'videoCount': channel['statistics'].get('videoCount', '0'),
                    'search_term': search_term
                })
        
        return channels
    except Exception as e:
        print(f"   Error: {e}")
        return []

def main():
    if not API_KEY:
        print("❌ Please set YOUTUBE_API_KEY environment variable")
        return
    
    youtube = build('youtube', 'v3', developerKey=API_KEY)
    
    all_channels = {}
    
    print("🔍 Searching for Congressional Committee YouTube Channels")
    print("=" * 60)
    
    for search_term in COMMITTEE_SEARCHES[:10]:  # Limit to 10 to avoid quota
        print(f"\nSearching: {search_term}")
        
        channels = search_for_channel(youtube, search_term)
        
        for channel in channels:
            # Check if likely a real committee channel
            title_lower = channel['title'].lower()
            desc_lower = channel['description'].lower()
            
            # Look for indicators this is official
            if any(word in title_lower for word in ['committee', 'senate', 'house']) or \
               any(word in desc_lower for word in ['committee', 'congress', 'official']):
                
                # Avoid duplicates
                if channel['id'] not in all_channels:
                    all_channels[channel['id']] = channel
                    print(f"  ✅ {channel['title']} ({channel['videoCount']} videos)")
                    print(f"     ID: {channel['id']}")
                    if channel.get('customUrl'):
                        print(f"     URL: @{channel['customUrl']}")
    
    # Save results
    with open('outputs/found_committee_channels.json', 'w') as f:
        json.dump(all_channels, f, indent=2)
    
    print(f"\n✅ Found {len(all_channels)} unique committee channels")
    print("   Saved to: outputs/found_committee_channels.json")
    
    # Generate updated channel dict for the script
    print("\n📋 Channel dictionary for fetch_committee_livestreams.py:")
    print("COMMITTEE_CHANNELS = {")
    for channel_id, channel in all_channels.items():
        print(f"    '{channel_id}': '{channel['title']}',")
    print("}")

if __name__ == "__main__":
    main()
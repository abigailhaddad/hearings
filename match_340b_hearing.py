import json
import requests
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.environ.get('CONGRESS_API_KEY')

def find_340b_youtube_video():
    """Get the 340B hearing from YouTube data"""
    youtube_data = json.load(open('house_energy_commerce_full.json'))
    
    for video in youtube_data['videos']:
        if "Oversight Of 340B Drug Pricing Program" in video['title']:
            return video
    return None

def search_congress_meetings_by_date(target_date: str, congress: int = 118):
    """Search for committee meetings on a specific date"""
    print(f"🔍 Searching for meetings on {target_date}")
    
    # Load the data we already have
    congress_data = json.load(open('data/congress_118_both.json'))
    meetings = congress_data['committee_meetings']['data']
    
    # Filter to just House meetings
    house_meetings = [m for m in meetings if m['chamber'] == 'House']
    print(f"   Checking {len(house_meetings)} House meetings...")
    
    matches = []
    checked = 0
    
    # Check meetings around the target date
    for meeting in house_meetings:
        # Fetch the meeting details
        url = f"{meeting['url']}&api_key={API_KEY}"
        response = requests.get(url)
        
        if response.status_code == 200:
            details = response.json()
            meeting_date = details.get('date', '')
            
            # Check if date matches
            if meeting_date.startswith(target_date):
                # Check if it's Energy & Commerce
                committees = details.get('committees', [])
                for committee in committees:
                    if 'Energy' in committee.get('name', '') and 'Commerce' in committee.get('name', ''):
                        print(f"\n✅ Found E&C meeting on {target_date}:")
                        print(f"   Event ID: {meeting['eventId']}")
                        print(f"   Title: {details.get('title', 'N/A')}")
                        
                        # Check if it's the 340B hearing
                        title = details.get('title', '').lower()
                        if '340b' in title:
                            print("   🎯 THIS IS THE 340B HEARING!")
                            return meeting['eventId'], details
                        
                        matches.append({
                            'eventId': meeting['eventId'],
                            'title': details.get('title'),
                            'committees': [c['name'] for c in committees]
                        })
                        break
        
        checked += 1
        if checked >= 100:  # Limit to first 100 for demo
            break
    
    return None, matches

def main():
    print("🎯 Finding match for 340B hearing")
    print("=" * 50)
    
    # Get the YouTube video
    youtube_video = find_340b_youtube_video()
    if not youtube_video:
        print("❌ Could not find 340B YouTube video")
        return
    
    print("📺 YouTube Video:")
    print(f"   Title: {youtube_video['title']}")
    print(f"   Date: {youtube_video['liveStreamingDetails']['actualStartTime']}")
    print(f"   Duration: {youtube_video['duration']}")
    print(f"   Views: {youtube_video['viewCount']}")
    
    # Extract date
    stream_date = youtube_video['liveStreamingDetails']['actualStartTime']
    date_only = stream_date.split('T')[0]  # Get just the date part
    
    print(f"\n🔍 Searching Congress API for meetings on {date_only}...")
    
    # Search for matching meeting
    event_id, matches = search_congress_meetings_by_date(date_only)
    
    if event_id:
        print(f"\n\n🎉 SUCCESS! Matched YouTube video to Congress Event ID: {event_id}")
    else:
        print(f"\n\nFound {len(matches) if isinstance(matches, list) else 0} E&C meetings on that date")
        print("May need to check more meetings or adjust date matching")

if __name__ == "__main__":
    main()
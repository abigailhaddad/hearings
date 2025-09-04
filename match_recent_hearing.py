import json
import requests
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.environ.get('CONGRESS_API_KEY')

def find_recent_youtube_video():
    """Get the recent AI healthcare hearing from YouTube data"""
    youtube_data = json.load(open('house_energy_commerce_full.json'))
    
    # Find the AI in Healthcare hearing from Sept 3, 2025
    for video in youtube_data['videos']:
        if "Examining Opportunities to Advance American Health Care through the Use of AI" in video['title']:
            if video.get('liveStreamingDetails', {}).get('actualStartTime', '').startswith('2025-09-03'):
                return video
    return None

def search_congress_meetings_by_date(target_date: str, congress: int = 119):
    """Search for committee meetings on a specific date"""
    print(f"🔍 Searching for meetings on {target_date} in {congress}th Congress")
    
    # Load the Congress 119 data (current congress)
    try:
        congress_data = json.load(open(f'data/congress_{congress}_both.json'))
    except:
        print(f"❌ No data file for {congress}th Congress")
        return None, []
    
    meetings = congress_data['committee_meetings']['data']
    
    # Filter to just House meetings
    house_meetings = [m for m in meetings if m['chamber'] == 'House']
    print(f"   Checking {len(house_meetings)} House meetings...")
    
    matches = []
    checked = 0
    
    # Check recent meetings first (they're usually at the beginning)
    for meeting in house_meetings[:200]:  # Check first 200
        # Fetch the meeting details
        url = f"{meeting['url']}&api_key={API_KEY}"
        try:
            response = requests.get(url, timeout=10)
            
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
                            
                            # Check if it's about AI/healthcare
                            title = details.get('title', '').lower()
                            if 'ai' in title or 'artificial intelligence' in title:
                                print("   🎯 THIS IS THE AI HEALTHCARE HEARING!")
                                return meeting['eventId'], details
                            
                            matches.append({
                                'eventId': meeting['eventId'],
                                'title': details.get('title'),
                                'committees': [c['name'] for c in committees]
                            })
                            break
        except Exception as e:
            print(f"   Error fetching meeting {meeting['eventId']}: {e}")
        
        checked += 1
        if checked % 50 == 0:
            print(f"   Checked {checked} meetings...")
    
    return None, matches

def main():
    print("🎯 Finding match for recent AI Healthcare hearing")
    print("=" * 50)
    
    # Get the YouTube video
    youtube_video = find_recent_youtube_video()
    if not youtube_video:
        print("❌ Could not find AI Healthcare YouTube video")
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
    
    # Search for matching meeting in 119th Congress (current)
    event_id, result = search_congress_meetings_by_date(date_only, congress=119)
    
    if event_id:
        print(f"\n\n🎉 SUCCESS! Matched YouTube video to Congress Event ID: {event_id}")
        print("\n📊 Match Summary:")
        print(f"   YouTube Title: {youtube_video['title']}")
        print(f"   Congress Title: {result.get('title')}")
        print(f"   Date: {date_only}")
        print(f"   Event ID: {event_id}")
    else:
        print(f"\n\nFound {len(result) if isinstance(result, list) else 0} E&C meetings on that date")
        if isinstance(result, list) and result:
            print("\nOther E&C meetings found:")
            for m in result:
                print(f"   - {m['eventId']}: {m['title'][:60]}...")

if __name__ == "__main__":
    main()
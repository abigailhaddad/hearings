import json
import requests
import os
from datetime import datetime
from dotenv import load_dotenv
import time
import pickle

load_dotenv()
API_KEY = os.environ.get('CONGRESS_API_KEY')

def build_date_index():
    """Build an index of Energy & Commerce events by date"""
    
    # Check if we already have an index
    index_file = "ec_date_index.json"
    if os.path.exists(index_file):
        print("📂 Loading existing index...")
        with open(index_file, 'r') as f:
            return json.load(f)
    
    print("🔨 Building Energy & Commerce date index...")
    print("This will take a few minutes but only needs to run once.\n")
    
    # Load bulk data
    all_events = []
    
    for congress in [118, 119]:
        filename = f'data/congress_{congress}_both.json'
        if os.path.exists(filename):
            print(f"\n📋 Processing {congress}th Congress...")
            data = json.load(open(filename))
            
            # Get House meetings
            meetings = data['committee_meetings']['data']
            house_meetings = [m for m in meetings if m['chamber'] == 'House']
            
            print(f"   Checking {len(house_meetings)} House meetings...")
            
            # Sample check - just first 50 for now
            for i, meeting in enumerate(house_meetings[:50]):
                if i % 10 == 0:
                    print(f"   Checked {i}/50...")
                
                try:
                    url = f"{meeting['url']}&api_key={API_KEY}"
                    resp = requests.get(url, timeout=10)
                    
                    if resp.status_code == 200:
                        details = resp.json()
                        cm = details.get('committeeMeeting', {})
                        
                        # Check if Energy & Commerce
                        committees = cm.get('committees', [])
                        for committee in committees:
                            if 'Energy' in committee.get('name', '') and 'Commerce' in committee.get('name', ''):
                                event = {
                                    'eventId': cm['eventId'],
                                    'congress': congress,
                                    'date': cm.get('date'),
                                    'title': cm.get('title'),
                                    'committee': committee.get('name')
                                }
                                all_events.append(event)
                                
                                date_str = cm.get('date', 'No date')[:10] if cm.get('date') else 'No date'
                                print(f"\n   ✅ Found E&C event on {date_str}")
                                print(f"      {cm.get('title', 'No title')[:60]}...")
                                break
                    
                    time.sleep(0.1)  # Rate limit
                    
                except Exception as e:
                    print(f"   Error: {e}")
    
    # Save the index
    with open(index_file, 'w') as f:
        json.dump(all_events, f, indent=2)
    
    print(f"\n✅ Saved {len(all_events)} Energy & Commerce events to {index_file}")
    
    return all_events

def match_youtube_to_congress(youtube_video, ec_events):
    """Match a YouTube video to Congress events by date"""
    
    # Extract YouTube date
    yt_date = youtube_video['liveStreamingDetails']['actualStartTime'][:10]
    
    print(f"\n🔍 Looking for matches on {yt_date}...")
    
    matches = []
    for event in ec_events:
        if event['date'] and event['date'].startswith(yt_date):
            matches.append(event)
            print(f"   ✅ Found match: Event {event['eventId']}")
            print(f"      {event['title'][:60]}...")
    
    return matches

def main():
    # Build or load the index
    ec_events = build_date_index()
    
    # Load YouTube data
    youtube_data = json.load(open('house_energy_commerce_full.json'))
    
    # Find the AI healthcare hearing
    for video in youtube_data['videos']:
        if "AI" in video['title'] and video.get('liveStreamingDetails', {}).get('actualStartTime', '').startswith('2025-09-03'):
            print(f"\n📺 YouTube Video: {video['title']}")
            
            matches = match_youtube_to_congress(video, ec_events)
            
            if matches:
                print(f"\n🎉 Found {len(matches)} matching Congress events!")
                for match in matches:
                    print(f"\n   Event ID: {match['eventId']}")
                    print(f"   Title: {match['title']}")
                    print(f"   Committee: {match['committee']}")
            else:
                print("\n❌ No matches found")
            
            break

if __name__ == "__main__":
    main()
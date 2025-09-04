import json
import re
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

def load_json_file(filepath: str) -> Dict:
    """Load JSON file"""
    with open(filepath, 'r') as f:
        return json.load(f)

def normalize_title(title: str) -> str:
    """Normalize title for comparison"""
    # Remove common prefixes/suffixes
    title = re.sub(r'^(.*?)(Hearing|Subcommittee|Committee):\s*', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\s+', ' ', title)  # Normalize whitespace
    return title.lower().strip()

def find_340b_hearing_in_youtube():
    """Find the 340B hearing in YouTube data"""
    youtube_data = load_json_file('house_energy_commerce_full.json')
    
    print("🔍 Searching for 340B hearing in YouTube data...")
    
    for video in youtube_data['videos']:
        if '340B' in video['title']:
            print(f"\n📺 Found YouTube video:")
            print(f"   Title: {video['title']}")
            print(f"   ID: {video['id']}")
            print(f"   Published: {video['publishedAt']}")
            if video.get('liveStreamingDetails'):
                print(f"   Stream Date: {video['liveStreamingDetails'].get('actualStartTime', 'N/A')}")
            print(f"   Duration: {video['duration']}")
            print(f"   Views: {video['viewCount']}")
            
            # Return the main hearing video
            if "Oversight Of 340B Drug Pricing Program" in video['title']:
                return video
    
    return None

def find_340b_hearing_in_congress_api():
    """Find the 340B hearing in Congress API data"""
    # Load Congress API data for 118th Congress
    try:
        congress_data = load_json_file('data/congress_118_both.json')
    except:
        print("❌ Could not load Congress API data for 118th Congress")
        return None
    
    print("\n🏛️ Searching for 340B hearing in Congress API data...")
    
    # Search in committee meetings
    if 'committee_meetings' in congress_data:
        for meeting in congress_data['committee_meetings']['data']:
            # Get meeting details URL
            if meeting.get('url'):
                print(f"   Checking meeting {meeting.get('eventId')}...")
                # For now, just print the structure
                # In a real implementation, we'd fetch the detailed data
    
    # Search in hearings
    if 'hearings' in congress_data:
        print(f"\n   Total hearings to search: {len(congress_data['hearings']['data'])}")
        
        # For demo, just show structure of first few
        for i, hearing in enumerate(congress_data['hearings']['data'][:5]):
            print(f"\n   Hearing {i+1}:")
            print(f"     Chamber: {hearing.get('chamber')}")
            print(f"     Congress: {hearing.get('congress')}")
            print(f"     Jacket Number: {hearing.get('jacketNumber')}")
            print(f"     Update Date: {hearing.get('updateDate')}")
            print(f"     URL: {hearing.get('url')}")

def match_by_date_and_title(youtube_video: Dict, congress_event: Dict) -> float:
    """Calculate match score based on date and title similarity"""
    score = 0.0
    
    # Title similarity
    youtube_title = normalize_title(youtube_video.get('title', ''))
    congress_title = normalize_title(congress_event.get('title', ''))
    
    title_similarity = SequenceMatcher(None, youtube_title, congress_title).ratio()
    score += title_similarity * 0.7  # 70% weight for title
    
    # Date similarity (if available)
    if youtube_video.get('liveStreamingDetails', {}).get('actualStartTime'):
        youtube_date = datetime.fromisoformat(youtube_video['liveStreamingDetails']['actualStartTime'].replace('Z', '+00:00'))
        
        if congress_event.get('date'):
            congress_date = datetime.fromisoformat(congress_event['date'])
            
            # Check if dates are within 1 day of each other
            date_diff = abs((youtube_date - congress_date).days)
            if date_diff == 0:
                score += 0.3  # 30% weight for exact date match
            elif date_diff == 1:
                score += 0.15  # 15% weight for 1-day difference
    
    return score

def main():
    """Main function to demonstrate matching"""
    print("🎯 YouTube to Congress API Event Matching Demo")
    print("=" * 50)
    
    # Find 340B hearing in YouTube
    youtube_340b = find_340b_hearing_in_youtube()
    
    if youtube_340b:
        print("\n✅ Found 340B hearing in YouTube data!")
        
        # Try to find in Congress API data
        congress_340b = find_340b_hearing_in_congress_api()
        
        print("\n📊 Matching Strategy:")
        print("1. Search by title keywords (340B, drug pricing, oversight)")
        print("2. Match by date (committee meetings on same day)")
        print("3. Match by committee (Energy and Commerce)")
        print("4. Use fuzzy string matching for title similarity")
        
        print("\n🔗 To complete the matching:")
        print("1. Fetch detailed hearing/meeting data from Congress API URLs")
        print("2. Extract titles and dates from the detailed data")
        print("3. Calculate similarity scores")
        print("4. Assign event IDs to YouTube videos with high confidence matches")
        
    else:
        print("\n❌ Could not find 340B hearing in YouTube data")

if __name__ == "__main__":
    main()
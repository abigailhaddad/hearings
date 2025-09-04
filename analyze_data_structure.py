import json
import re
from datetime import datetime
from pprint import pprint

def analyze_youtube_structure():
    """Analyze YouTube video structure for the 340B hearing"""
    youtube_data = json.load(open('house_energy_commerce_full.json'))
    
    print("🎥 YOUTUBE VIDEO STRUCTURE ANALYSIS")
    print("=" * 60)
    
    # Find the 340B hearing
    for video in youtube_data['videos']:
        if "Oversight Of 340B Drug Pricing Program" in video['title']:
            print("\n📺 Found 340B Hearing Video:")
            print(f"Title: {video['title']}")
            
            print("\n📊 Available Fields:")
            for key, value in video.items():
                if isinstance(value, dict):
                    print(f"\n{key}:")
                    for k2, v2 in value.items():
                        print(f"  - {k2}: {v2}")
                else:
                    print(f"- {key}: {value}")
            
            # Extract potential identifiers
            print("\n🔍 Extracted Identifiers:")
            
            # Check description for event IDs
            description = video.get('description', '')
            
            # Look for patterns like "Event ID: 12345" or "Hearing ID: 12345"
            event_id_patterns = [
                r'Event ID[:\s]+(\d+)',
                r'Hearing ID[:\s]+(\d+)',
                r'Meeting ID[:\s]+(\d+)',
                r'ID[:\s]+(\d+)',
                r'eventId=(\d+)',
                r'hearing/(\d+)',
                r'meeting/(\d+)'
            ]
            
            for pattern in event_id_patterns:
                matches = re.findall(pattern, description, re.IGNORECASE)
                if matches:
                    print(f"  Found ID with pattern '{pattern}': {matches}")
            
            # Extract date information
            print("\n📅 Date Information:")
            published = video.get('publishedAt')
            if published:
                pub_date = datetime.fromisoformat(published.replace('Z', '+00:00'))
                print(f"  Published: {pub_date}")
            
            if video.get('liveStreamingDetails'):
                stream_details = video['liveStreamingDetails']
                if stream_details.get('scheduledStartTime'):
                    sched_date = datetime.fromisoformat(stream_details['scheduledStartTime'].replace('Z', '+00:00'))
                    print(f"  Scheduled: {sched_date}")
                if stream_details.get('actualStartTime'):
                    actual_date = datetime.fromisoformat(stream_details['actualStartTime'].replace('Z', '+00:00'))
                    print(f"  Actual Start: {actual_date}")
                    print(f"  Date only: {actual_date.date()}")
            
            break

def analyze_congress_structure():
    """Analyze Congress API data structure"""
    print("\n\n🏛️ CONGRESS API DATA STRUCTURE ANALYSIS")
    print("=" * 60)
    
    # Load sample from Congress API
    try:
        congress_data = json.load(open('data/congress_118_both.json'))
    except:
        print("❌ Could not load Congress 118 data")
        return
    
    # Check what fields we have
    print("\n📊 Available Data Types:")
    for key in congress_data.keys():
        if key not in ['metadata']:
            print(f"- {key}")
    
    # Sample committee meeting structure
    if 'committee_meetings' in congress_data:
        meetings = congress_data['committee_meetings']['data']
        if meetings:
            print(f"\n📋 Committee Meeting Structure (sample from {len(meetings)} meetings):")
            sample_meeting = meetings[0]
            for key, value in sample_meeting.items():
                print(f"- {key}: {value}")
            
            # Check URL patterns
            if sample_meeting.get('url'):
                print(f"\n🔗 URL Pattern Analysis:")
                url = sample_meeting['url']
                print(f"  Full URL: {url}")
                
                # Extract patterns
                patterns = {
                    'eventId': r'/committee-meeting/\d+/\w+/(\d+)',
                    'congress': r'/committee-meeting/(\d+)/',
                    'chamber': r'/committee-meeting/\d+/(\w+)/'
                }
                
                for name, pattern in patterns.items():
                    match = re.search(pattern, url)
                    if match:
                        print(f"  {name}: {match.group(1)}")
    
    # Sample hearing structure  
    if 'hearings' in congress_data:
        hearings = congress_data['hearings']['data']
        if hearings:
            print(f"\n📋 Hearing Structure (sample from {len(hearings)} hearings):")
            sample_hearing = hearings[0]
            for key, value in sample_hearing.items():
                print(f"- {key}: {value}")

def propose_matching_strategy():
    """Propose a matching strategy based on available fields"""
    print("\n\n🎯 PROPOSED MATCHING STRATEGY")
    print("=" * 60)
    
    print("\n1️⃣ Direct ID Match (if available):")
    print("   - Search YouTube description for eventId patterns")
    print("   - Match against Congress API eventId field")
    
    print("\n2️⃣ Date-based Match:")
    print("   - Use YouTube liveStreamingDetails.actualStartTime (date only)")
    print("   - Will need to fetch detailed meeting/hearing data for dates")
    print("   - Consider ±1 day tolerance for timezone/scheduling differences")
    
    print("\n3️⃣ Title Similarity Match:")
    print("   - Normalize titles (remove 'Hearing:', 'Committee:', etc.)")
    print("   - Use fuzzy string matching (e.g., Levenshtein distance)")
    print("   - Set threshold (e.g., 80% similarity)")
    
    print("\n4️⃣ Committee Match:")
    print("   - Extract committee name from YouTube channel/title")
    print("   - Match against committee field in Congress API")
    
    print("\n5️⃣ Combined Score:")
    print("   - Weight each factor (e.g., Date: 40%, Title: 40%, Committee: 20%)")
    print("   - Set confidence threshold for automatic matching")
    
    print("\n⚠️ Challenges:")
    print("   - Congress API data needs detailed fetching (only have URLs)")
    print("   - No direct event IDs in current YouTube metadata")
    print("   - Date formats and timezones need careful handling")
    print("   - Multiple videos per hearing (opening statements, full hearing)")

if __name__ == "__main__":
    analyze_youtube_structure()
    analyze_congress_structure()
    propose_matching_strategy()
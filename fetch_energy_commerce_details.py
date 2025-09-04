import json
import requests
import os
from datetime import datetime
from dotenv import load_dotenv
from tqdm import tqdm
import time

load_dotenv()
API_KEY = os.environ.get('CONGRESS_API_KEY')

def fetch_details(url: str) -> dict:
    """Fetch detailed data from Congress API"""
    try:
        response = requests.get(f"{url}&api_key={API_KEY}", timeout=30)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"  Error: {e}")
    return None

def is_energy_commerce_event(details: dict) -> bool:
    """Check if event is from Energy and Commerce committee"""
    if not details:
        return False
    
    # Check committees field
    committees = details.get('committees', [])
    for committee in committees:
        name = committee.get('name', '').lower()
        if 'energy' in name and 'commerce' in name:
            return True
    
    # Also check title
    title = details.get('title', '').lower()
    if 'energy and commerce' in title:
        return True
    
    return False

def fetch_energy_commerce_events(congress_number: int):
    """Fetch all Energy and Commerce events for a specific Congress"""
    print(f"\n📋 Fetching Energy and Commerce events for {congress_number}th Congress")
    print("=" * 60)
    
    # Load data
    filename = f'data/congress_{congress_number}_both.json'
    if not os.path.exists(filename):
        print(f"❌ File not found: {filename}")
        return []
    
    congress_data = json.load(open(filename))
    energy_commerce_events = []
    
    # Check committee meetings
    if 'committee_meetings' in congress_data:
        meetings = congress_data['committee_meetings']['data']
        
        # Filter for House meetings only (Energy & Commerce is a House committee)
        house_meetings = [m for m in meetings if m.get('chamber', '').lower() == 'house']
        print(f"\n🏛️ Found {len(meetings)} total meetings, {len(house_meetings)} House meetings")
        print(f"   Checking House meetings for Energy & Commerce...")
        
        found_count = 0
        with tqdm(total=len(house_meetings), desc="House Committee Meetings") as pbar:
            for meeting in house_meetings:
                # Quick check - if we already found many, just sample
                if found_count > 50:
                    pbar.update(len(house_meetings) - pbar.n)
                    break
                    
                details = fetch_details(meeting['url'])
                
                if is_energy_commerce_event(details):
                    found_count += 1
                    event_data = {
                        'type': 'committee_meeting',
                        'eventId': meeting['eventId'],
                        'congress': meeting['congress'],
                        'chamber': meeting['chamber'],
                        'url': meeting['url'],
                        'details': details
                    }
                    energy_commerce_events.append(event_data)
                    
                    # Print sample info
                    if found_count <= 3:
                        print(f"\n  ✅ Found E&C meeting:")
                        print(f"     Event ID: {meeting['eventId']}")
                        print(f"     Date: {details.get('date', 'N/A')}")
                        print(f"     Title: {details.get('title', 'N/A')[:80]}...")
                
                pbar.update(1)
                time.sleep(0.1)  # Rate limiting
        
        print(f"\n  Found {found_count} Energy & Commerce committee meetings")
    
    # Check hearings
    if 'hearings' in congress_data:
        hearings = congress_data['hearings']['data']
        print(f"\n📄 Checking {len(hearings)} hearings...")
        
        found_count = 0
        # Sample first 100 hearings (full check would take too long)
        sample_size = min(100, len(hearings))
        print(f"  (Sampling first {sample_size} hearings for demo)")
        
        with tqdm(total=sample_size, desc="Hearings") as pbar:
            for hearing in hearings[:sample_size]:
                details = fetch_details(hearing['url'])
                
                if is_energy_commerce_event(details):
                    found_count += 1
                    event_data = {
                        'type': 'hearing',
                        'jacketNumber': hearing['jacketNumber'],
                        'congress': hearing['congress'],
                        'chamber': hearing['chamber'],
                        'url': hearing['url'],
                        'details': details
                    }
                    energy_commerce_events.append(event_data)
                    
                    # Print sample info
                    if found_count <= 3:
                        print(f"\n  ✅ Found E&C hearing:")
                        print(f"     Jacket: {hearing['jacketNumber']}")
                        print(f"     Date: {details.get('date', 'N/A')}")
                        print(f"     Title: {details.get('title', 'N/A')[:80]}...")
                
                pbar.update(1)
                time.sleep(0.1)
        
        print(f"\n  Found {found_count} Energy & Commerce hearings (in sample)")
    
    return energy_commerce_events

def main():
    all_events = []
    
    # Fetch for both 118th and 119th Congress
    for congress in [118, 119]:
        events = fetch_energy_commerce_events(congress)
        all_events.extend(events)
    
    # Save results
    output_file = 'energy_commerce_detailed_events.json'
    
    # Prepare clean output
    output_data = {
        'metadata': {
            'total_events': len(all_events),
            'fetch_date': datetime.now().isoformat(),
            'congresses': [118, 119]
        },
        'events': []
    }
    
    # Clean up event data for storage
    for event in all_events:
        clean_event = {
            'type': event['type'],
            'id': event.get('eventId') or event.get('jacketNumber'),
            'congress': event['congress'],
            'chamber': event['chamber'],
            'date': event['details'].get('date'),
            'title': event['details'].get('title'),
            'committees': [c.get('name') for c in event['details'].get('committees', [])],
            'url': event['url']
        }
        output_data['events'].append(clean_event)
    
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n\n✅ Saved {len(all_events)} Energy & Commerce events to {output_file}")
    
    # Show date range
    dates = [e['date'] for e in output_data['events'] if e['date']]
    if dates:
        dates.sort()
        print(f"📅 Date range: {dates[0]} to {dates[-1]}")

if __name__ == "__main__":
    main()
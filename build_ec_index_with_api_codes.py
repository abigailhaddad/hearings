import json
import requests
import os
from datetime import datetime
from dotenv import load_dotenv
import time
from tqdm import tqdm
import sys

load_dotenv()
API_KEY = os.environ.get('CONGRESS_API_KEY')

# Energy & Commerce committee system codes from the API
EC_COMMITTEE_CODES = {
    'hsif00': 'Energy and Commerce Committee (Main)',
    'hsif02': 'Oversight and Investigations Subcommittee',
    'hsif03': 'Energy Subcommittee',
    'hsif14': 'Health Subcommittee', 
    'hsif16': 'Communications and Technology Subcommittee',
    'hsif17': 'Commerce, Manufacturing, and Trade Subcommittee',
    'hsif18': 'Environment Subcommittee'
}

def fetch_committee_meetings_by_code(committee_code, congress):
    """Fetch all meetings for a specific committee code"""
    
    print(f"\n📋 Fetching meetings for {EC_COMMITTEE_CODES[committee_code]} ({committee_code}) - Congress {congress}")
    
    meetings = []
    offset = 0
    limit = 250
    
    while True:
        url = f"https://api.congress.gov/v3/committee/{committee_code}/{congress}/committee-meetings"
        url += f"?format=json&limit={limit}&offset={offset}&api_key={API_KEY}"
        
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                batch = data.get('committeeMeetings', [])
                if not batch:
                    break
                    
                meetings.extend(batch)
                offset += limit
                print(f"   Fetched {len(meetings)} meetings so far...")
                time.sleep(0.1)
                
            elif resp.status_code == 404:
                print(f"   No meetings endpoint for this committee/congress")
                break
            else:
                print(f"   Error: {resp.status_code}")
                break
                
        except Exception as e:
            print(f"   Exception: {e}")
            break
    
    return meetings

def build_comprehensive_ec_index():
    """Build comprehensive index using official committee codes"""
    
    index_file = "ec_api_comprehensive_index.json"
    checkpoint_file = ".checkpoint_ec_api.json"
    
    # Load checkpoint if exists
    checkpoint = {}
    if os.path.exists(checkpoint_file):
        print("📂 Found checkpoint file, resuming...")
        with open(checkpoint_file, 'r') as f:
            checkpoint = json.load(f)
    
    all_events = checkpoint.get('events', [])
    processed_ids = set(checkpoint.get('processed_ids', []))
    
    print("🔨 Building comprehensive Energy & Commerce index using API committee codes")
    print("Fetching ALL event types (not just Hearings/Markups)")
    print("=" * 70)
    
    for congress in [117, 118, 119]:  # Include 117th Congress too
        print(f"\n📅 Processing {congress}th Congress")
        
        # Process each committee/subcommittee
        for committee_code, committee_name in EC_COMMITTEE_CODES.items():
            
            # Skip if already processed
            checkpoint_key = f"{committee_code}_{congress}_done"
            if checkpoint.get(checkpoint_key, False):
                print(f"   ✅ {committee_name} already processed")
                continue
            
            # Fetch meetings for this committee
            meetings = fetch_committee_meetings_by_code(committee_code, congress)
            
            if not meetings:
                # Mark as done even if no meetings
                checkpoint[checkpoint_key] = True
                continue
            
            print(f"   Processing {len(meetings)} meetings...")
            added_count = 0
            
            # Process each meeting
            with tqdm(total=len(meetings), desc=f"{committee_code}") as pbar:
                for meeting in meetings:
                    try:
                        # Get meeting details if we have a URL
                        if meeting.get('url'):
                            # Check if already processed
                            event_id = meeting.get('eventId')
                            if event_id and event_id in processed_ids:
                                pbar.update(1)
                                continue
                            
                            url = f"{meeting['url']}&api_key={API_KEY}"
                            resp = requests.get(url, timeout=10)
                            
                            if resp.status_code == 200:
                                details = resp.json()
                                cm = details.get('committeeMeeting', {})
                                
                                # Extract all relevant info
                                event = {
                                    'eventId': cm.get('eventId'),
                                    'congress': congress,
                                    'date': cm.get('date'),
                                    'title': cm.get('title', ''),
                                    'committeeCode': committee_code,
                                    'committeeName': committee_name,
                                    'type': cm.get('type', ''),
                                    'meetingStatus': cm.get('meetingStatus', ''),
                                    'location': cm.get('meetingLocation', ''),
                                    'committees': [c.get('name', '') for c in cm.get('committees', [])]
                                }
                                
                                # Include ALL events, not just Hearings/Markups
                                # Let the matching algorithm decide what's relevant
                                all_events.append(event)
                                added_count += 1
                                processed_ids.add(event_id)
                                
                                pbar.set_postfix({'added': added_count})
                            
                            time.sleep(0.05)  # Rate limit
                            
                    except Exception as e:
                        pass  # Skip errors
                    
                    pbar.update(1)
                    
                    # Save checkpoint periodically
                    if len(all_events) % 100 == 0 and len(all_events) > 0:
                        checkpoint['events'] = all_events
                        checkpoint['processed_ids'] = list(processed_ids)
                        with open(checkpoint_file, 'w') as f:
                            json.dump(checkpoint, f)
            
            print(f"   Added {added_count} events from {committee_name}")
            
            # Mark committee/congress as done
            checkpoint[checkpoint_key] = True
            checkpoint['events'] = all_events
            checkpoint['processed_ids'] = list(processed_ids)
            with open(checkpoint_file, 'w') as f:
                json.dump(checkpoint, f)
    
    # Remove duplicates
    seen = set()
    unique_events = []
    for event in all_events:
        if event['eventId'] not in seen:
            seen.add(event['eventId'])
            unique_events.append(event)
    
    # Sort by date
    unique_events.sort(key=lambda x: x.get('date') or '', reverse=True)
    
    # Save final index
    with open(index_file, 'w') as f:
        json.dump(unique_events, f, indent=2)
    
    # Clean up checkpoint
    if os.path.exists(checkpoint_file):
        os.remove(checkpoint_file)
    
    print(f"\n✅ Saved {len(unique_events)} unique Energy & Commerce events")
    
    # Statistics
    print("\n📊 Event Statistics:")
    
    # By type
    type_counts = {}
    for event in unique_events:
        event_type = event.get('type', 'Unknown')
        type_counts[event_type] = type_counts.get(event_type, 0) + 1
    
    print("\n  By Type:")
    for event_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"    {event_type}: {count}")
    
    # By committee
    committee_counts = {}
    for event in unique_events:
        committee = event.get('committeeName', 'Unknown')
        committee_counts[committee] = committee_counts.get(committee, 0) + 1
    
    print("\n  By Committee:")
    for committee, count in sorted(committee_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"    {committee}: {count}")
    
    # By status
    status_counts = {}
    for event in unique_events:
        status = event.get('meetingStatus', 'Unknown')
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print("\n  By Status:")
    for status, count in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"    {status}: {count}")
    
    # Date range
    dates = [e['date'][:10] for e in unique_events if e.get('date')]
    if dates:
        dates.sort()
        print(f"\n  Date Range: {dates[0]} to {dates[-1]}")
    
    return unique_events

if __name__ == "__main__":
    if '--clean' in sys.argv:
        for f in ['.checkpoint_ec_api.json', 'ec_api_comprehensive_index.json']:
            if os.path.exists(f):
                os.remove(f)
                print(f"🧹 Cleaned {f}")
    
    build_comprehensive_ec_index()
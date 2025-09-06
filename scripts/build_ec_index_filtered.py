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

# Energy & Commerce committee system codes
EC_SYSTEM_CODES = {
    'hsif00': 'Energy and Commerce Committee (Main)',
    'hsif02': 'Oversight and Investigations Subcommittee',
    'hsif03': 'Energy Subcommittee',
    'hsif14': 'Health Subcommittee', 
    'hsif16': 'Communications and Technology Subcommittee',
    'hsif17': 'Commerce, Manufacturing, and Trade Subcommittee',
    'hsif18': 'Environment Subcommittee'
}

def is_ec_committee(committees_list):
    """Check if any committee in the list is E&C related"""
    for committee in committees_list:
        if committee.get('systemCode') in EC_SYSTEM_CODES:
            return True, committee.get('systemCode'), committee.get('name')
    return False, None, None

def build_comprehensive_ec_index():
    """Build comprehensive E&C index by filtering all committee meetings"""
    
    # Get the root directory (parent of scripts)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    
    index_file = os.path.join(root_dir, "outputs", "ec_filtered_index.json")
    checkpoint_file = os.path.join(root_dir, "outputs", ".checkpoint_ec_filtered.json")
    
    # Create outputs directory if it doesn't exist
    os.makedirs(os.path.join(root_dir, "outputs"), exist_ok=True)
    
    # Check for existing index file first
    if os.path.exists(index_file) and not os.path.exists(checkpoint_file):
        print("📂 Found existing index file, creating checkpoint from it...")
        with open(index_file, 'r') as f:
            existing_events = json.load(f)
        
        # Create checkpoint from existing data
        checkpoint = {
            'events': existing_events,
            'processed_ids': [e.get('eventId') for e in existing_events if e.get('eventId')]
        }
        
        # Mark completed congresses based on existing data
        congress_counts = {}
        for event in existing_events:
            congress = event.get('congress')
            if congress:
                congress_counts[congress] = congress_counts.get(congress, 0) + 1
        
        for congress in [113, 114, 115, 116, 117, 118, 119]:
            count = congress_counts.get(congress, 0)
            if count > 50:  # If we have substantial data, mark as done
                checkpoint[f'congress_{congress}_done'] = True
                print(f"   Congress {congress}: ✅ Marked as done ({count} events)")
        
        # Save checkpoint
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint, f)
        print("   Checkpoint created from existing data!")
    
    # Load checkpoint if exists
    checkpoint = {}
    if os.path.exists(checkpoint_file):
        print("📂 Found checkpoint file, resuming...")
        with open(checkpoint_file, 'r') as f:
            checkpoint = json.load(f)
    
    all_events = checkpoint.get('events', [])
    processed_ids = set(checkpoint.get('processed_ids', []))
    
    print("🔨 Building comprehensive Energy & Commerce index")
    print("Fetching ALL committee meetings and filtering by E&C system codes")
    print("=" * 70)
    
    # Going back 11 years from 2025 to ~2014
    # Congress 113: 2013-2014
    # Congress 114: 2015-2016
    # Congress 115: 2017-2018
    # Congress 116: 2019-2020
    # Congress 117: 2021-2022
    # Congress 118: 2023-2024
    # Congress 119: 2025-2026
    for congress in [113, 114, 115, 116, 117, 118, 119]:
        # Skip if already done
        if checkpoint.get(f'congress_{congress}_done', False):
            print(f"✅ Congress {congress} already processed")
            continue
            
        print(f"\n📅 Processing {congress}th Congress")
        
        # Fetch all committee meetings for this congress
        offset = checkpoint.get(f'congress_{congress}_offset', 0)
        limit = 250
        total_processed = 0
        ec_found = 0
        
        while True:
            url = f"https://api.congress.gov/v3/committee-meeting/{congress}"
            url += f"?format=json&limit={limit}&offset={offset}&api_key={API_KEY}"
            
            try:
                resp = requests.get(url, timeout=30)
                if resp.status_code == 200:
                    data = resp.json()
                    meetings = data.get('committeeMeetings', [])
                    
                    if not meetings:
                        print(f"   Finished processing {congress}th Congress")
                        break
                    
                    print(f"   Processing batch at offset {offset} ({len(meetings)} meetings)")
                    
                    # Filter for House meetings
                    house_meetings = [m for m in meetings if m.get('chamber') == 'House']
                    
                    # Process each meeting
                    with tqdm(total=len(house_meetings), desc=f"Batch {offset//limit + 1}") as pbar:
                        for meeting in house_meetings:
                            event_id = meeting.get('eventId')
                            
                            # Skip if already processed
                            if event_id in processed_ids:
                                pbar.update(1)
                                continue
                            
                            # Get meeting details
                            if meeting.get('url'):
                                detail_url = f"{meeting['url']}&api_key={API_KEY}"
                                
                                try:
                                    detail_resp = requests.get(detail_url, timeout=10)
                                    if detail_resp.status_code == 200:
                                        details = detail_resp.json()
                                        cm = details.get('committeeMeeting', {})
                                        
                                        # Check if it's an E&C committee
                                        committees = cm.get('committees', [])
                                        is_ec, system_code, committee_name = is_ec_committee(committees)
                                        
                                        if is_ec:
                                            event = {
                                                'eventId': cm.get('eventId'),
                                                'congress': congress,
                                                'date': cm.get('date'),
                                                'title': cm.get('title', ''),
                                                'systemCode': system_code,
                                                'committeeName': committee_name,
                                                'type': cm.get('type', ''),
                                                'meetingStatus': cm.get('meetingStatus', ''),
                                                'location': cm.get('location', {}),
                                                'allCommittees': [
                                                    {'name': c.get('name'), 'systemCode': c.get('systemCode')}
                                                    for c in committees
                                                ]
                                            }
                                            
                                            all_events.append(event)
                                            ec_found += 1
                                            pbar.set_postfix({'E&C found': ec_found})
                                    
                                    processed_ids.add(event_id)
                                    time.sleep(0.05)  # Rate limit
                                    
                                except Exception as e:
                                    # Skip individual meeting errors
                                    pass
                            
                            pbar.update(1)
                            total_processed += 1
                            
                            # Save checkpoint every 100 meetings
                            if total_processed % 100 == 0:
                                checkpoint['events'] = all_events
                                checkpoint['processed_ids'] = list(processed_ids)
                                checkpoint[f'congress_{congress}_offset'] = offset
                                with open(checkpoint_file, 'w') as f:
                                    json.dump(checkpoint, f)
                    
                    offset += limit
                    
                else:
                    print(f"   Error: {resp.status_code}")
                    break
                    
            except Exception as e:
                print(f"   Exception: {e}")
                break
        
        # Mark congress as done
        checkpoint[f'congress_{congress}_done'] = True
        checkpoint['events'] = all_events
        checkpoint['processed_ids'] = list(processed_ids)
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint, f)
        
        print(f"   Found {ec_found} E&C meetings in {congress}th Congress")
    
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
    status_counts = {}
    committee_counts = {}
    
    for event in unique_events:
        # Type
        event_type = event.get('type', 'Unknown')
        type_counts[event_type] = type_counts.get(event_type, 0) + 1
        
        # Status
        status = event.get('meetingStatus', 'Unknown')
        status_counts[status] = status_counts.get(status, 0) + 1
        
        # Committee
        committee = event.get('committeeName', 'Unknown')
        committee_counts[committee] = committee_counts.get(committee, 0) + 1
    
    print("\n  By Type:")
    for event_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"    {event_type}: {count}")
    
    print("\n  By Status:")
    for status, count in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"    {status}: {count}")
    
    print("\n  By Committee:")
    for committee, count in sorted(committee_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"    {committee}: {count}")
    
    # Date range
    dates = [e['date'][:10] for e in unique_events if e.get('date')]
    if dates:
        dates.sort()
        print(f"\n  Date Range: {dates[0]} to {dates[-1]}")
    
    return unique_events

if __name__ == "__main__":
    if '--clean' in sys.argv:
        for f in ['.checkpoint_ec_filtered.json', 'ec_filtered_index.json']:
            if os.path.exists(f):
                os.remove(f)
                print(f"🧹 Cleaned {f}")
    
    build_comprehensive_ec_index()
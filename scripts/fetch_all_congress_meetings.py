#!/usr/bin/env python3
"""
Fetch ALL House committee meetings from Congress.gov API
This runs ONCE to get all data, then individual committees can filter from this master dataset
"""

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

def fetch_all_house_meetings():
    """Fetch ALL House committee meetings across all congresses"""
    
    # Get the root directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    
    # Master file location
    master_file = os.path.join(root_dir, "outputs", "all_house_meetings_master.json")
    checkpoint_file = os.path.join(root_dir, "outputs", ".checkpoint_all_house_meetings.json")
    
    # Create outputs directory if it doesn't exist
    os.makedirs(os.path.join(root_dir, "outputs"), exist_ok=True)
    
    # Check if master file exists and is recent
    if os.path.exists(master_file) and not os.path.exists(checkpoint_file):
        file_age_days = (datetime.now().timestamp() - os.path.getmtime(master_file)) / 86400
        if file_age_days < 7:  # If less than a week old
            print("📂 Found recent master file (less than 7 days old)")
            with open(master_file, 'r') as f:
                data = json.load(f)
            print(f"   Contains {len(data['meetings'])} meetings")
            print(f"   Last updated: {data['metadata']['generated_at']}")
            return data['meetings']
    
    # Load checkpoint if exists
    checkpoint = {}
    if os.path.exists(checkpoint_file):
        print("📂 Found checkpoint file, resuming...")
        with open(checkpoint_file, 'r') as f:
            checkpoint = json.load(f)
    
    all_meetings = checkpoint.get('meetings', [])
    processed_ids = set(checkpoint.get('processed_ids', []))
    
    print("🔨 Fetching ALL House committee meetings from Congress.gov")
    print("This will create a master dataset that all committees can use")
    print("=" * 70)
    
    # Process each congress
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
        house_meetings_found = 0
        
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
                                        
                                        # Store ALL House meetings with full details
                                        meeting_data = {
                                            'eventId': cm.get('eventId'),
                                            'congress': congress,
                                            'date': cm.get('date'),
                                            'title': cm.get('title', ''),
                                            'type': cm.get('type', ''),
                                            'meetingStatus': cm.get('meetingStatus', ''),
                                            'location': cm.get('location', {}),
                                            'committees': [
                                                {
                                                    'name': c.get('name'),
                                                    'systemCode': c.get('systemCode'),
                                                    'chamber': c.get('chamber')
                                                }
                                                for c in cm.get('committees', [])
                                            ]
                                        }
                                        
                                        all_meetings.append(meeting_data)
                                        house_meetings_found += 1
                                        pbar.set_postfix({'House meetings': house_meetings_found})
                                    
                                    processed_ids.add(event_id)
                                    time.sleep(0.05)  # Rate limit
                                    
                                except Exception as e:
                                    # Skip individual meeting errors
                                    pass
                            
                            pbar.update(1)
                            total_processed += 1
                            
                            # Save checkpoint every 100 meetings
                            if total_processed % 100 == 0:
                                checkpoint['meetings'] = all_meetings
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
        checkpoint['meetings'] = all_meetings
        checkpoint['processed_ids'] = list(processed_ids)
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint, f)
        
        print(f"   Found {house_meetings_found} House meetings in {congress}th Congress")
    
    # Remove duplicates
    seen = set()
    unique_meetings = []
    for meeting in all_meetings:
        if meeting['eventId'] not in seen:
            seen.add(meeting['eventId'])
            unique_meetings.append(meeting)
    
    # Sort by date
    unique_meetings.sort(key=lambda x: x.get('date') or '', reverse=True)
    
    # Save master file
    output = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'total_meetings': len(unique_meetings),
            'congresses': [113, 114, 115, 116, 117, 118, 119]
        },
        'meetings': unique_meetings
    }
    
    with open(master_file, 'w') as f:
        json.dump(output, f, indent=2)
    
    # Clean up checkpoint
    if os.path.exists(checkpoint_file):
        os.remove(checkpoint_file)
    
    print(f"\n✅ Master dataset saved with {len(unique_meetings)} House meetings")
    
    # Statistics
    print("\n📊 Meeting Statistics:")
    
    # By congress
    congress_counts = {}
    committee_counts = {}
    type_counts = {}
    
    for meeting in unique_meetings:
        # Congress
        congress = meeting.get('congress')
        congress_counts[congress] = congress_counts.get(congress, 0) + 1
        
        # Committees
        for comm in meeting.get('committees', []):
            code = comm.get('systemCode')
            if code:
                committee_counts[code] = committee_counts.get(code, 0) + 1
        
        # Type
        meeting_type = meeting.get('type', 'Unknown')
        type_counts[meeting_type] = type_counts.get(meeting_type, 0) + 1
    
    print("\n  By Congress:")
    for congress in sorted(congress_counts.keys()):
        print(f"    {congress}th Congress: {congress_counts[congress]} meetings")
    
    print(f"\n  Total unique committees: {len(committee_counts)}")
    
    print("\n  By Type:")
    for mtype, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"    {mtype}: {count}")
    
    return unique_meetings

if __name__ == "__main__":
    if '--clean' in sys.argv:
        files = ['all_house_meetings_master.json', '.checkpoint_all_house_meetings.json']
        for f in files:
            path = os.path.join('outputs', f)
            if os.path.exists(path):
                os.remove(path)
                print(f"🧹 Cleaned {f}")
    
    fetch_all_house_meetings()
import json
import requests
import os
import yaml
from datetime import datetime
from dotenv import load_dotenv
import time
from tqdm import tqdm
import sys

load_dotenv()
API_KEY = os.environ.get('CONGRESS_API_KEY')

def load_committee_config():
    """Load committee configuration from YAML file"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'committees_config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def build_committee_index():
    """Build comprehensive committee index for all active committees"""
    
    config = load_committee_config()
    active_committees = config['active_committees']
    committees_info = config['committees']
    
    print(f"🔨 Building index for {len(active_committees)} active committee(s)")
    
    # Combine all committee codes from active committees
    all_committee_codes = {}
    committee_names = []
    
    for comm_id in active_committees:
        if comm_id in committees_info:
            comm = committees_info[comm_id]
            committee_names.append(comm['short_name'])
            for code, name in comm['codes'].items():
                all_committee_codes[code] = {
                    'name': name,
                    'committee': comm['short_name']
                }
    
    print(f"Committees: {', '.join(committee_names)}")
    print(f"Total system codes to search: {len(all_committee_codes)}")
    print("=" * 70)
    
    # Get the root directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    
    # Create unified output filename
    committee_suffix = '_'.join(active_committees)
    index_file = os.path.join(root_dir, "outputs", f"{committee_suffix}_filtered_index.json")
    checkpoint_file = os.path.join(root_dir, "outputs", f".checkpoint_{committee_suffix}_filtered.json")
    
    # Create outputs directory if it doesn't exist
    os.makedirs(os.path.join(root_dir, "outputs"), exist_ok=True)
    
    def is_target_committee(committees_list):
        """Check if any committee in the list matches our target committees"""
        for committee in committees_list:
            if committee.get('systemCode') in all_committee_codes:
                code = committee.get('systemCode')
                return True, code, committee.get('name'), all_committee_codes[code]['committee']
        return False, None, None, None
    
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
    
    print("Fetching ALL committee meetings and filtering by committee system codes")
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
        committee_found = 0
        
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
                                        
                                        # Check if it's one of our target committees
                                        committees = cm.get('committees', [])
                                        is_target, system_code, committee_name, parent_committee = is_target_committee(committees)
                                        
                                        if is_target:
                                            event = {
                                                'eventId': cm.get('eventId'),
                                                'congress': congress,
                                                'date': cm.get('date'),
                                                'title': cm.get('title', ''),
                                                'systemCode': system_code,
                                                'committeeName': committee_name,
                                                'parentCommittee': parent_committee,
                                                'type': cm.get('type', ''),
                                                'meetingStatus': cm.get('meetingStatus', ''),
                                                'location': cm.get('location', {}),
                                                'allCommittees': [
                                                    {'name': c.get('name'), 'systemCode': c.get('systemCode')}
                                                    for c in committees
                                                ]
                                            }
                                            
                                            all_events.append(event)
                                            committee_found += 1
                                            pbar.set_postfix({'Found': committee_found})
                                    
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
        
        print(f"   Found {committee_found} committee meetings in {congress}th Congress")
    
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
    
    print(f"\n✅ Saved {len(unique_events)} unique committee events")
    
    # Statistics by committee
    print("\n📊 Event Statistics by Committee:")
    committee_counts = {}
    
    for event in unique_events:
        committee = event.get('parentCommittee', 'Unknown')
        committee_counts[committee] = committee_counts.get(committee, 0) + 1
    
    for committee, count in sorted(committee_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {committee}: {count} events")
    
    # Date range
    dates = [e['date'][:10] for e in unique_events if e.get('date')]
    if dates:
        dates.sort()
        print(f"\n  Date Range: {dates[0]} to {dates[-1]}")
    
    return unique_events

if __name__ == "__main__":
    # Check if PyYAML is installed
    try:
        import yaml
    except ImportError:
        print("ERROR: PyYAML is required. Please run: pip install pyyaml")
        sys.exit(1)
    
    if '--clean' in sys.argv:
        config = load_committee_config()
        committee_suffix = '_'.join(config['active_committees'])
        for f in [f'.checkpoint_{committee_suffix}_filtered.json', f'{committee_suffix}_filtered_index.json']:
            path = os.path.join('outputs', f)
            if os.path.exists(path):
                os.remove(path)
                print(f"🧹 Cleaned {f}")
    
    build_committee_index()
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

def build_comprehensive_ec_index():
    """Build a comprehensive index of ALL Energy & Commerce events"""
    
    index_file = "ec_comprehensive_index.json"
    checkpoint_file = ".checkpoint_ec_index.json"
    
    # Load checkpoint if exists
    checkpoint = {}
    if os.path.exists(checkpoint_file):
        print("📂 Found checkpoint file, resuming...")
        with open(checkpoint_file, 'r') as f:
            checkpoint = json.load(f)
    
    all_events = checkpoint.get('events', [])
    processed_ids = set(checkpoint.get('processed_ids', []))
    
    print("🔨 Building Energy & Commerce STREAMABLE events index...")
    print("Only fetching Hearings and Markups (excluding postponed/cancelled)")
    print("This will be much faster!\n")
    
    for congress in [118, 119]:
        filename = f'data/congress_{congress}_both.json'
        if not os.path.exists(filename):
            continue
        
        # Skip if already processed this congress
        if checkpoint.get(f'congress_{congress}_done', False):
            print(f"✅ Congress {congress} already processed")
            continue
            
        print(f"\n📋 Processing {congress}th Congress...")
        data = json.load(open(filename))
        
        # Get House meetings
        meetings = data['committee_meetings']['data']
        house_meetings = [m for m in meetings if m['chamber'] == 'House']
        
        # Skip already processed meetings
        to_process = [m for m in house_meetings if m['eventId'] not in processed_ids]
        
        if len(to_process) < len(house_meetings):
            print(f"   Skipping {len(house_meetings) - len(to_process)} already processed meetings")
        
        print(f"   Checking {len(to_process)} House meetings...")
        
        ec_count = 0
        errors = 0
        
        with tqdm(total=len(to_process), desc=f"Congress {congress}") as pbar:
            for i, meeting in enumerate(to_process):
                try:
                    url = f"{meeting['url']}&api_key={API_KEY}"
                    resp = requests.get(url, timeout=10)
                    
                    if resp.status_code == 200:
                        details = resp.json()
                        cm = details.get('committeeMeeting', {})
                        
                        # Check if Energy & Commerce
                        committees = cm.get('committees', [])
                        is_ec = False
                        committee_name = ''
                        for committee in committees:
                            name = committee.get('name', '')
                            if 'Energy' in name and 'Commerce' in name:
                                is_ec = True
                                committee_name = name
                                break
                        
                        if is_ec:
                            # Check if it's likely to be streamed
                            meeting_type = cm.get('type', '')
                            status = cm.get('meetingStatus', '')
                            title = cm.get('title', '').lower()
                            
                            # Skip if not a streamable type
                            if meeting_type not in ['Hearing', 'Markup']:
                                pbar.set_postfix({'E&C': ec_count, 'errors': errors, 'skip': 'Not Hearing/Markup'})
                            # Skip if postponed/cancelled
                            elif status in ['Postponed', 'Cancelled', 'Canceled']:
                                pbar.set_postfix({'E&C': ec_count, 'errors': errors, 'skip': 'Postponed/Cancelled'})
                            # Skip business meetings
                            elif 'business meeting' in title:
                                pbar.set_postfix({'E&C': ec_count, 'errors': errors, 'skip': 'Business Meeting'})
                            else:
                                # This is a streamable E&C event!
                                event = {
                                    'eventId': cm['eventId'],
                                    'congress': congress,
                                    'date': cm.get('date'),
                                    'title': cm.get('title', ''),
                                    'committee': committee_name,
                                    'type': meeting_type,
                                    'meetingStatus': status
                                }
                                all_events.append(event)
                                ec_count += 1
                                pbar.set_postfix({'E&C': ec_count, 'errors': errors})
                    
                    elif resp.status_code == 429:  # Rate limited
                        print("\n⚠️  Rate limited, waiting 60 seconds...")
                        time.sleep(60)
                        continue
                    
                    processed_ids.add(meeting['eventId'])
                    
                except Exception as e:
                    errors += 1
                    pbar.set_postfix({'E&C': ec_count, 'errors': errors})
                
                pbar.update(1)
                
                # Save checkpoint every 100 meetings
                if i % 100 == 0 and i > 0:
                    checkpoint = {
                        'events': all_events,
                        'processed_ids': list(processed_ids),
                        f'congress_{congress}_done': False
                    }
                    with open(checkpoint_file, 'w') as f:
                        json.dump(checkpoint, f)
                
                time.sleep(0.05)  # Rate limit
        
        # Mark congress as done
        checkpoint[f'congress_{congress}_done'] = True
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint, f)
        
        print(f"   Found {ec_count} Energy & Commerce events (Errors: {errors})")
    
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
    
    print(f"\n✅ Saved {len(unique_events)} unique Energy & Commerce events to {index_file}")
    
    # Show date range
    dates = [e['date'][:10] for e in unique_events if e.get('date')]
    if dates:
        dates.sort()
        print(f"📅 Date range: {dates[0]} to {dates[-1]}")
        
        # Check coverage against YouTube
        youtube_data = json.load(open('house_energy_commerce_full.json'))
        live_videos = [v for v in youtube_data['videos'] if v.get('liveStreamingDetails')]
        youtube_dates = set()
        for v in live_videos:
            if v.get('liveStreamingDetails', {}).get('actualStartTime'):
                youtube_dates.add(v['liveStreamingDetails']['actualStartTime'][:10])
        
        congress_dates = set(dates)
        overlap = youtube_dates & congress_dates
        
        print(f"\n📊 Date coverage:")
        print(f"   YouTube dates: {len(youtube_dates)}")
        print(f"   Congress dates with E&C events: {len(congress_dates)}")
        print(f"   Overlapping dates: {len(overlap)} ({len(overlap)/len(youtube_dates)*100:.1f}% of YouTube dates)")
    
    return unique_events

if __name__ == "__main__":
    # Allow running with --clean to start fresh
    if '--clean' in sys.argv and os.path.exists('.checkpoint_ec_index.json'):
        os.remove('.checkpoint_ec_index.json')
        print("🧹 Cleaned checkpoint file")
    
    build_comprehensive_ec_index()
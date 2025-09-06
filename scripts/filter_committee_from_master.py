#!/usr/bin/env python3
"""
Filter committee-specific meetings from the master dataset
This is FAST because it just filters existing data rather than making API calls
"""

import json
import os
import yaml
from datetime import datetime
import sys

def filter_committees_from_master():
    """Filter meetings for active committees from master dataset"""
    
    # Get the root directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    
    # Load committee configuration
    with open(os.path.join(root_dir, 'committees_config.yaml'), 'r') as f:
        config = yaml.safe_load(f)
    
    active_committees = config['active_committees']
    committees_info = config['committees']
    
    # Load master dataset
    master_file = os.path.join(root_dir, "outputs", "all_house_meetings_master.json")
    
    if not os.path.exists(master_file):
        print("❌ Master dataset not found!")
        print("   Please run: python scripts/fetch_all_congress_meetings.py")
        return False
    
    print("📂 Loading master dataset...")
    with open(master_file, 'r') as f:
        master_data = json.load(f)
    
    all_meetings = master_data['meetings']
    print(f"   Loaded {len(all_meetings)} total House meetings")
    
    # Process each active committee
    print(f"\n🔍 Filtering data for {len(active_committees)} active committee(s)")
    
    all_filtered_meetings = []
    committee_stats = {}
    
    for comm_id in active_committees:
        if comm_id not in committees_info:
            print(f"❌ Committee '{comm_id}' not found in configuration")
            continue
        
        comm = committees_info[comm_id]
        committee_codes = set(comm['codes'].keys())
        
        print(f"\n📋 {comm['short_name']}:")
        print(f"   System codes: {', '.join(sorted(committee_codes))}")
        
        # Filter meetings for this committee
        committee_meetings = []
        
        for meeting in all_meetings:
            # Check if any of the meeting's committees match our target codes
            meeting_codes = {c.get('systemCode') for c in meeting.get('committees', [])}
            
            if committee_codes & meeting_codes:  # If there's any intersection
                # Add committee info to the meeting
                meeting_copy = meeting.copy()
                meeting_copy['matched_committee'] = comm_id
                meeting_copy['matched_committee_name'] = comm['short_name']
                
                # Find which specific committee/subcommittee matched
                for c in meeting['committees']:
                    if c.get('systemCode') in committee_codes:
                        meeting_copy['matched_system_code'] = c.get('systemCode')
                        meeting_copy['matched_committee_full'] = c.get('name')
                        break
                
                committee_meetings.append(meeting_copy)
        
        print(f"   Found {len(committee_meetings)} meetings")
        
        committee_stats[comm_id] = {
            'name': comm['short_name'],
            'count': len(committee_meetings)
        }
        
        # Save individual committee file (for backward compatibility)
        individual_file = os.path.join(root_dir, "outputs", f"{comm_id}_filtered_index.json")
        with open(individual_file, 'w') as f:
            json.dump(committee_meetings, f, indent=2)
        print(f"   Saved to: outputs/{comm_id}_filtered_index.json")
        
        all_filtered_meetings.extend(committee_meetings)
    
    # Save combined file for all active committees
    if len(active_committees) > 1:
        # Remove duplicates (meetings that belong to multiple active committees)
        seen = set()
        unique_meetings = []
        for meeting in all_filtered_meetings:
            event_id = meeting['eventId']
            if event_id not in seen:
                seen.add(event_id)
                unique_meetings.append(meeting)
            else:
                # If we've seen this meeting, add the additional committee info
                for m in unique_meetings:
                    if m['eventId'] == event_id:
                        if 'additional_matched_committees' not in m:
                            m['additional_matched_committees'] = []
                        m['additional_matched_committees'].append({
                            'committee_id': meeting['matched_committee'],
                            'committee_name': meeting['matched_committee_name']
                        })
                        break
        
        all_filtered_meetings = unique_meetings
    
    # Sort by date
    all_filtered_meetings.sort(key=lambda x: x.get('date') or '', reverse=True)
    
    # Save combined file
    combined_suffix = '_'.join(active_committees)
    combined_file = os.path.join(root_dir, "outputs", f"{combined_suffix}_filtered_index.json")
    with open(combined_file, 'w') as f:
        json.dump(all_filtered_meetings, f, indent=2)
    
    print(f"\n✅ Filtering complete!")
    print(f"   Combined dataset: outputs/{combined_suffix}_filtered_index.json")
    print(f"   Total meetings across all committees: {len(all_filtered_meetings)}")
    
    # Summary
    print("\n📊 Summary by committee:")
    for comm_id, stats in committee_stats.items():
        print(f"   {stats['name']}: {stats['count']} meetings")
    
    return True

if __name__ == "__main__":
    filter_committees_from_master()
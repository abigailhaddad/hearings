import os
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.environ.get('CONGRESS_API_KEY')
BASE_URL = 'https://api.congress.gov/v3'

def find_energy_commerce_code():
    """Find the Energy and Commerce committee system code"""
    url = f"{BASE_URL}/committee/house?api_key={API_KEY}&limit=100"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        print("🔍 Looking for Energy & Commerce Committee code...")
        
        for committee in data.get('committees', []):
            name = committee.get('name', '')
            if 'Energy' in name and 'Commerce' in name:
                print(f"\n✅ Found: {name}")
                print(f"   System Code: {committee.get('systemCode')}")
                print(f"   Committee Code: {committee.get('committeeCode')}")
                
                # Get the full details to find activity URL
                detail_url = f"{committee.get('url')}&api_key={API_KEY}"
                detail_resp = requests.get(detail_url)
                if detail_resp.status_code == 200:
                    details = detail_resp.json()
                    if 'committee' in details:
                        print(f"   Type: {details['committee'].get('type')}")
                        # Check for subcommittees
                        if details['committee'].get('subcommittees'):
                            print(f"   Subcommittees: {len(details['committee']['subcommittees'])}")
                
                return committee.get('systemCode')
    
    return None

def get_committee_meetings_filtered(congress: int, chamber: str = 'house'):
    """Try to get committee meetings with filtering"""
    print(f"\n📋 Fetching {congress}th Congress {chamber} committee meetings...")
    
    # First, let's see what the unfiltered endpoint gives us
    url = f"{BASE_URL}/committee-meeting/{congress}/{chamber}?api_key={API_KEY}&limit=250"
    all_meetings = []
    offset = 0
    
    while True:
        paginated_url = f"{url}&offset={offset}"
        response = requests.get(paginated_url)
        
        if response.status_code == 200:
            data = response.json()
            meetings = data.get('committeeMeetings', [])
            
            if not meetings:
                break
                
            all_meetings.extend(meetings)
            
            # Check if we have all
            pagination = data.get('pagination', {})
            if len(all_meetings) >= pagination.get('count', 0):
                break
                
            offset += 250
            print(f"   Fetched {len(all_meetings)} of {pagination.get('count', 'unknown')} meetings...")
        else:
            print(f"❌ Error: {response.status_code}")
            break
    
    return all_meetings

def filter_energy_commerce_meetings(meetings: list):
    """Filter meetings to find Energy & Commerce ones"""
    print(f"\n🔍 Filtering {len(meetings)} meetings for Energy & Commerce...")
    
    ec_meetings = []
    sample_checked = 0
    
    # Just check a sample to see the pattern
    for meeting in meetings[:20]:  # Check first 20
        sample_checked += 1
        
        # Get meeting details
        detail_url = f"{meeting.get('url')}&api_key={API_KEY}"
        response = requests.get(detail_url)
        
        if response.status_code == 200:
            details = response.json()
            
            # Check committees
            committees = details.get('committees', [])
            for committee in committees:
                name = committee.get('name', '').lower()
                if 'energy' in name and 'commerce' in name:
                    print(f"\n✅ Found E&C meeting:")
                    print(f"   Event ID: {meeting.get('eventId')}")
                    print(f"   Date: {details.get('date')}")
                    print(f"   Title: {details.get('title', 'N/A')[:80]}...")
                    
                    ec_meetings.append({
                        'eventId': meeting.get('eventId'),
                        'date': details.get('date'),
                        'title': details.get('title'),
                        'committees': [c.get('name') for c in committees]
                    })
                    
                    # Check for 340B
                    if '340b' in (details.get('title', '') or '').lower():
                        print("   🎯 THIS IS THE 340B MEETING!")
                    
                    break
    
    print(f"\nChecked {sample_checked} meetings, found {len(ec_meetings)} E&C meetings")
    return ec_meetings

def main():
    # Find committee code
    ec_code = find_energy_commerce_code()
    
    # Get meetings for 118th Congress
    meetings = get_committee_meetings_filtered(118, 'house')
    
    # Filter for Energy & Commerce
    ec_meetings = filter_energy_commerce_meetings(meetings)
    
    # Save sample
    with open('energy_commerce_meetings_sample.json', 'w') as f:
        json.dump(ec_meetings, f, indent=2)
    
    print(f"\n✅ Saved {len(ec_meetings)} E&C meetings to energy_commerce_meetings_sample.json")

if __name__ == "__main__":
    main()
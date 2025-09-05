import json
import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.environ.get('CONGRESS_API_KEY')

def test_committee_meeting_endpoint():
    """Test different committee meeting endpoint patterns"""
    
    print("🔍 Testing committee meeting endpoint patterns...")
    
    # Test patterns
    test_urls = [
        # General committee meetings
        ("General meetings", f"https://api.congress.gov/v3/committee-meeting?format=json&limit=5&api_key={API_KEY}"),
        
        # Try filtering by congress
        ("Meetings for 118th Congress", f"https://api.congress.gov/v3/committee-meeting/118?format=json&limit=5&api_key={API_KEY}"),
        
        # Try committee parameter
        ("With committee param", f"https://api.congress.gov/v3/committee-meeting?committee=hsif00&format=json&limit=5&api_key={API_KEY}"),
        
        # Try committeeCode parameter
        ("With committeeCode param", f"https://api.congress.gov/v3/committee-meeting?committeeCode=hsif00&format=json&limit=5&api_key={API_KEY}"),
    ]
    
    for desc, url in test_urls:
        print(f"\n📋 Testing: {desc}")
        print(f"   URL: {url}")
        
        try:
            resp = requests.get(url, timeout=30)
            print(f"   Status: {resp.status_code}")
            
            if resp.status_code == 200:
                data = resp.json()
                meetings = data.get('committeeMeetings', [])
                print(f"   Found {len(meetings)} meetings")
                
                # Look at first meeting structure
                if meetings:
                    meeting = meetings[0]
                    print(f"   Sample meeting keys: {list(meeting.keys())}")
                    
                    # Check if it has committee info
                    if 'committees' in meeting:
                        print(f"   Has 'committees' field")
                    if 'committeeCode' in meeting:
                        print(f"   Has 'committeeCode' field: {meeting['committeeCode']}")
                    if 'committee' in meeting:
                        print(f"   Has 'committee' field: {meeting['committee']}")
                    
                    # Save sample for inspection
                    with open(f'sample_meeting_{desc.replace(" ", "_")}.json', 'w') as f:
                        json.dump(meeting, f, indent=2)
            
            else:
                print(f"   Response: {resp.text[:200]}")
                
        except Exception as e:
            print(f"   Error: {e}")
    
    # Now let's get a sample and see the structure
    print("\n📋 Getting detailed sample of committee meetings...")
    url = f"https://api.congress.gov/v3/committee-meeting?format=json&limit=10&api_key={API_KEY}"
    
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            meetings = data.get('committeeMeetings', [])
            
            # Find any E&C meetings
            ec_meetings = []
            for meeting in meetings:
                # Get the meeting detail URL to check committees
                if meeting.get('url'):
                    detail_url = f"{meeting['url']}&api_key={API_KEY}"
                    detail_resp = requests.get(detail_url, timeout=10)
                    
                    if detail_resp.status_code == 200:
                        details = detail_resp.json()
                        cm = details.get('committeeMeeting', {})
                        committees = cm.get('committees', [])
                        
                        for committee in committees:
                            if 'hsif' in committee.get('systemCode', '').lower():
                                print(f"\n✅ Found E&C meeting!")
                                print(f"   Title: {cm.get('title')}")
                                print(f"   Committee: {committee.get('name')} ({committee.get('systemCode')})")
                                ec_meetings.append(details)
                                break
            
            if ec_meetings:
                with open('sample_ec_meetings.json', 'w') as f:
                    json.dump(ec_meetings, f, indent=2)
                print(f"\n💾 Saved {len(ec_meetings)} E&C meeting samples")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_committee_meeting_endpoint()
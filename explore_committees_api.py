import json
import requests
import os
from dotenv import load_dotenv
import time

load_dotenv()
API_KEY = os.environ.get('CONGRESS_API_KEY')

def explore_committees():
    """Explore the committees endpoint to find Energy & Commerce structure"""
    
    print("🔍 Exploring Congress API committees endpoint...")
    
    # First, try to get all committees
    url = f"https://api.congress.gov/v3/committee?format=json&limit=250&api_key={API_KEY}"
    
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            committees = data.get('committees', [])
            
            print(f"✅ Found {len(committees)} committees")
            
            # Filter for House committees
            house_committees = [c for c in committees if c.get('chamber') == 'House']
            print(f"   House committees: {len(house_committees)}")
            
            # Look for Energy and Commerce
            ec_committees = []
            for comm in house_committees:
                name = comm.get('name', '')
                if 'Energy' in name or 'Commerce' in name:
                    ec_committees.append(comm)
                    print(f"\n📍 Found: {name}")
                    print(f"   Committee Code: {comm.get('committeeCode', 'N/A')}")
                    print(f"   Type: {comm.get('type', 'N/A')}")
                    print(f"   URL: {comm.get('url', 'N/A')}")
            
            # Save all committees for inspection
            with open('all_committees.json', 'w') as f:
                json.dump({'committees': committees}, f, indent=2)
            print(f"\n💾 Saved all committees to all_committees.json")
            
            return ec_committees
            
        else:
            print(f"❌ Error: {resp.status_code}")
            print(f"Response: {resp.text}")
    
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    return []

def get_committee_details(committee_url):
    """Get detailed info about a specific committee"""
    
    url = f"{committee_url}?api_key={API_KEY}"
    
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            return data.get('committee', {})
        else:
            print(f"❌ Error getting committee details: {resp.status_code}")
    
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    return {}

def explore_subcommittees(committee_code, congress=119):
    """Try to get subcommittees for a committee"""
    
    print(f"\n🔍 Looking for subcommittees of {committee_code}...")
    
    # Try different endpoint patterns
    patterns = [
        f"https://api.congress.gov/v3/committee/{committee_code}/{congress}?format=json&api_key={API_KEY}",
        f"https://api.congress.gov/v3/committee/house/{committee_code}?format=json&api_key={API_KEY}",
        f"https://api.congress.gov/v3/committee/house/{committee_code}/{congress}?format=json&api_key={API_KEY}"
    ]
    
    for pattern in patterns:
        print(f"   Trying: {pattern}")
        try:
            resp = requests.get(pattern, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                committee = data.get('committee', {})
                
                # Look for subcommittees
                subcommittees = committee.get('subcommittees', [])
                if subcommittees:
                    print(f"   ✅ Found {len(subcommittees)} subcommittees!")
                    return committee
                
                # Save for inspection even if no subcommittees found
                filename = f"committee_{committee_code}_details.json"
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)
                print(f"   💾 Saved details to {filename}")
                
                return committee
                
            elif resp.status_code == 404:
                print(f"   ❌ Not found")
            else:
                print(f"   ❌ Error: {resp.status_code}")
        
        except Exception as e:
            print(f"   ❌ Exception: {e}")
        
        time.sleep(0.5)
    
    return {}

def main():
    print("🏛️ Congress API Committee Explorer")
    print("=" * 60)
    
    # Step 1: Get all committees
    ec_committees = explore_committees()
    
    # Step 2: Get details for E&C committees
    if ec_committees:
        for comm in ec_committees:
            code = comm.get('committeeCode')
            if code:
                details = explore_subcommittees(code)
                
                if details.get('subcommittees'):
                    print(f"\n📋 Subcommittees of {details.get('name')}:")
                    for sub in details['subcommittees']:
                        print(f"   - {sub.get('name')} ({sub.get('committeeCode', 'N/A')})")

if __name__ == "__main__":
    main()
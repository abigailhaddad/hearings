import os
import requests
import json
from datetime import datetime
from dotenv import load_dotenv
from tqdm import tqdm
import time

load_dotenv()
API_KEY = os.environ.get('CONGRESS_API_KEY')

def get_energy_commerce_committee_code():
    """Get the committee code for House Energy and Commerce"""
    # First, let's find the committee code
    url = f"https://api.congress.gov/v3/committee/house?api_key={API_KEY}&limit=100"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        for committee in data.get('committees', []):
            name = committee.get('name', '').lower()
            if 'energy' in name and 'commerce' in name:
                print(f"✅ Found Energy & Commerce Committee:")
                print(f"   Name: {committee.get('name')}")
                print(f"   Code: {committee.get('systemCode')}")
                print(f"   URL: {committee.get('url')}")
                return committee.get('systemCode'), committee.get('url')
    return None, None

def get_committee_activities(committee_code: str, congress: int):
    """Get all activities for a specific committee"""
    print(f"\n📋 Getting Energy & Commerce activities for {congress}th Congress")
    
    # Try committee-reports endpoint
    activities_url = f"https://api.congress.gov/v3/committee-report/{committee_code}/{congress}?api_key={API_KEY}&limit=250"
    
    print(f"   Checking committee reports...")
    response = requests.get(activities_url)
    if response.status_code == 200:
        data = response.json()
        print(f"   Found {len(data.get('reports', []))} reports")
    
    # Try bills sponsored by committee
    bills_url = f"https://api.congress.gov/v3/bill/{congress}?api_key={API_KEY}&limit=20"
    response = requests.get(bills_url)
    if response.status_code == 200:
        data = response.json()
        # We'd need to filter these by committee
        print(f"   Found bills endpoint (would need filtering)")
    
    # The main issue is that the Congress API doesn't have a direct "meetings by committee" endpoint
    print("\n⚠️  Note: Congress API doesn't have a direct 'meetings by committee' endpoint")
    print("   We'd need to either:")
    print("   1. Use the committee's website directly")
    print("   2. Filter from all meetings (as we were doing)")
    print("   3. Use committee print/report data as proxy for meetings")

def check_api_endpoints():
    """Explore available API endpoints"""
    print("\n🔍 Exploring Congress API endpoints...")
    
    endpoints = [
        "/committee",
        "/committee/house/hsif",  # Energy & Commerce code
        "/committee-print",
        "/committee-report", 
        "/committee-meeting",
        "/hearing"
    ]
    
    for endpoint in endpoints:
        url = f"https://api.congress.gov/v3{endpoint}?api_key={API_KEY}&limit=1"
        try:
            response = requests.get(url, timeout=5)
            print(f"\n{endpoint}: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Keys: {list(data.keys())}")
        except:
            print(f"{endpoint}: Failed")

def main():
    # First, find the committee
    committee_code, committee_url = get_energy_commerce_committee_code()
    
    if committee_code:
        # Get committee activities
        for congress in [118, 119]:
            get_committee_activities(committee_code, congress)
    
    # Check what endpoints are available
    check_api_endpoints()
    
    print("\n💡 Best approach:")
    print("   Since there's no direct committee filtering in the meetings endpoint,")
    print("   we should create a one-time filtered dataset by:")
    print("   1. Fetching all House meetings once")
    print("   2. Checking which are Energy & Commerce")
    print("   3. Saving just those to a file")
    print("   4. Then matching against YouTube data")

if __name__ == "__main__":
    main()
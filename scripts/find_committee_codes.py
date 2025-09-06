import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.environ.get('CONGRESS_API_KEY')

# Get all committees
url = f"https://api.congress.gov/v3/committee?format=json&limit=250&api_key={API_KEY}"
resp = requests.get(url)

if resp.status_code == 200:
    data = resp.json()
    committees = data.get('committees', [])
    
    # Filter for House committees
    house_committees = [c for c in committees if c.get('chamber') == 'House']
    
    print("House Committees and their System Codes:")
    print("=" * 60)
    for comm in sorted(house_committees, key=lambda x: x.get('name', '')):
        print(f"{comm.get('systemCode', 'N/A'):8} - {comm.get('name', 'Unknown')}")

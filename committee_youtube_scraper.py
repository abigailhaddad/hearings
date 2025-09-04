import requests
from bs4 import BeautifulSoup
import json
import re
from typing import Dict, List, Optional
from datetime import datetime
import time
from tqdm import tqdm
import os
from dotenv import load_dotenv

load_dotenv()

def get_current_committee_youtube_urls() -> Dict[str, List[Dict[str, str]]]:
    """Scrape current committee YouTube URLs using Wayback Machine"""
    # Use Wayback Machine for current year too
    return get_archived_committee_urls(119)  # 119th Congress is current (2025-2026)

def get_archived_committee_urls(congress_number: int) -> Dict[str, List[Dict[str, str]]]:
    """Get archived committee YouTube URLs using Wayback Machine"""
    committees = {
        'house': [],
        'senate': [],
        'joint': []
    }
    
    # Estimate year for congress number
    # 119th Congress = 2025-2026
    # 118th Congress = 2023-2024
    # etc.
    year = 2025 - (119 - congress_number) * 2
    
    # Try Wayback Machine
    wayback_url = f"https://web.archive.org/web/{year}0601120000*/https://www.congress.gov/committees/video"
    
    print(f"🗄️ Checking Wayback Machine for Congress {congress_number} (~{year})")
    
    try:
        # First get available snapshots
        cdx_url = f"https://web.archive.org/cdx/search/cdx?url=congress.gov/committees/video&from={year}&to={year+1}&output=json"
        response = requests.get(cdx_url, timeout=30)
        
        if response.status_code == 200:
            snapshots = response.json()
            if len(snapshots) > 1:  # First row is headers
                # Get a snapshot from middle of the year
                snapshot = snapshots[len(snapshots)//2]
                timestamp = snapshot[1]
                
                archived_url = f"https://web.archive.org/web/{timestamp}/https://www.congress.gov/committees/video"
                print(f"📸 Found snapshot from {timestamp[:8]}")
                
                # Fetch and parse archived page
                response = requests.get(archived_url, timeout=30)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for YouTube links
                all_links = soup.find_all('a', href=re.compile(r'youtube\.com'))
                
                for link in all_links:
                    youtube_url = link.get('href')
                    parent = link.find_parent(['div', 'li', 'td'])
                    if parent:
                        committee_name = parent.get_text(strip=True)
                        
                        chamber = 'joint'
                        if 'house' in committee_name.lower():
                            chamber = 'house'
                        elif 'senate' in committee_name.lower():
                            chamber = 'senate'
                        
                        committees[chamber].append({
                            'name': committee_name,
                            'youtube_url': youtube_url,
                            'congress': congress_number,
                            'source': f'wayback_{timestamp}',
                            'scraped_date': datetime.now().isoformat()
                        })
    
    except Exception as e:
        print(f"⚠️ Could not fetch Wayback data for Congress {congress_number}: {e}")
    
    return committees

def merge_committee_data(current_data: Dict, historical_data: List[Dict]) -> Dict:
    """Merge current and historical committee YouTube data"""
    merged = {
        'current': current_data,
        'historical': {},
        'metadata': {
            'scraped_date': datetime.now().isoformat(),
            'total_committees': 0
        }
    }
    
    # Add historical data by congress
    for hist_data in historical_data:
        congress = hist_data.get('congress')
        if congress:
            merged['historical'][f'congress_{congress}'] = hist_data
    
    # Count total committees
    total = sum(len(committees) for committees in current_data.values())
    for hist in historical_data:
        total += sum(len(committees) for committees in hist.values() if isinstance(committees, list))
    
    merged['metadata']['total_committees'] = total
    
    return merged

def main():
    """Main function to scrape committee YouTube URLs"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Scrape Congressional committee YouTube channel URLs')
    parser.add_argument('--congress', type=int, nargs='+', help='Historical congress numbers to include')
    parser.add_argument('--output', default='committee_youtube_urls.json', help='Output JSON file')
    
    args = parser.parse_args()
    
    print(f"\n📺 Congressional Committee YouTube Scraper")
    print(f"🕐 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Get current committee URLs
    current_committees = get_current_committee_youtube_urls()
    
    print(f"\n📊 Found current committees:")
    for chamber, committees in current_committees.items():
        print(f"   {chamber.title()}: {len(committees)} committees")
    
    # Get historical data if requested
    historical_data = []
    if args.congress:
        print(f"\n🗄️ Fetching historical data for Congress(es): {', '.join(map(str, args.congress))}")
        for congress_num in tqdm(args.congress, desc="Fetching historical data"):
            hist_data = get_archived_committee_urls(congress_num)
            hist_data['congress'] = congress_num
            historical_data.append(hist_data)
            time.sleep(2)  # Be nice to Wayback Machine
    
    # Merge and save data
    final_data = merge_committee_data(current_committees, historical_data)
    
    with open(args.output, 'w') as f:
        json.dump(final_data, f, indent=2)
    
    print(f"\n✅ Data saved to {args.output}")
    print(f"📊 Total committees found: {final_data['metadata']['total_committees']}")

if __name__ == "__main__":
    main()
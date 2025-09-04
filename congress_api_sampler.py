import os
import requests
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from dotenv import load_dotenv
import time
from tqdm import tqdm

load_dotenv()
API_KEY = os.environ.get('CONGRESS_API_KEY')
BASE_URL = 'https://api.congress.gov/v3'

def make_request(endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """Make a request to the Congress API"""
    if not API_KEY:
        raise ValueError("CONGRESS_API_KEY environment variable not set")
    
    if params is None:
        params = {}
    params['api_key'] = API_KEY
    params['format'] = 'json'
    
    url = f"{BASE_URL}{endpoint}"
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        raise Exception(f"Request timed out after 30 seconds for {endpoint}")
    except requests.exceptions.ConnectionError as e:
        raise Exception(f"Connection error: {str(e)}")
    except requests.exceptions.HTTPError as e:
        raise Exception(f"HTTP {response.status_code} error: {response.text[:200]}...")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Request failed: {type(e).__name__}: {str(e)}")

def sample_hearings():
    """Sample hearing data from the API"""
    print("Sampling Hearings...")
    print("-" * 50)
    
    # Get first page of hearings
    response = make_request('/hearing', {'limit': 5})
    
    print(f"Total hearings available: {response.get('pagination', {}).get('count', 'Unknown')}")
    print(f"\nFirst 5 hearings:")
    
    for hearing in response.get('hearings', []):
        print(f"\n  Chamber: {hearing.get('chamber')}")
        print(f"  Congress: {hearing.get('congress')}")
        print(f"  Jacket Number: {hearing.get('jacketNumber')}")
        print(f"  Update Date: {hearing.get('updateDate')}")
        
        # Get details for the first hearing
        if response.get('hearings', []).index(hearing) == 0:
            print("\n  Fetching detailed info for first hearing...")
            detail_url = hearing.get('url').replace(BASE_URL, '')
            detail_response = make_request(detail_url)
            
            print(f"  Title: {detail_response.get('title', 'N/A')}")
            print(f"  Date: {detail_response.get('date', 'N/A')}")
            if detail_response.get('committees'):
                print(f"  Committee: {detail_response['committees'][0].get('name', 'N/A')}")

def sample_committee_meetings():
    """Sample committee meeting data from the API"""
    print("\n\nSampling Committee Meetings...")
    print("-" * 50)
    
    # Get first page of committee meetings
    response = make_request('/committee-meeting', {'limit': 5})
    
    print(f"Total committee meetings available: {response.get('pagination', {}).get('count', 'Unknown')}")
    print(f"\nFirst 5 committee meetings:")
    
    for meeting in response.get('committeeMeetings', []):
        print(f"\n  Chamber: {meeting.get('chamber')}")
        print(f"  Congress: {meeting.get('congress')}")
        print(f"  Event ID: {meeting.get('eventId')}")
        print(f"  Update Date: {meeting.get('updateDate')}")
        
        # Get details for the first meeting
        if response.get('committeeMeetings', []).index(meeting) == 0:
            print("\n  Fetching detailed info for first meeting...")
            detail_url = meeting.get('url').replace(BASE_URL, '')
            detail_response = make_request(detail_url)
            
            print(f"  Title: {detail_response.get('title', 'N/A')}")
            print(f"  Date: {detail_response.get('date', 'N/A')}")
            if detail_response.get('committees'):
                print(f"  Committee: {detail_response['committees'][0].get('name', 'N/A')}")

def fetch_all_data_for_congress(congress_number: int, data_type: str = 'both', output_dir: str = 'data', resume: bool = True) -> Dict[str, Any]:
    """Fetch all hearings and/or committee meetings for a specific Congress"""
    results = {'congress': congress_number, 'timestamp': datetime.now().isoformat()}
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Check for existing partial data if resume is enabled
    checkpoint_file = f"{output_dir}/.checkpoint_congress_{congress_number}_{data_type}.json"
    checkpoint_data = {}
    if resume and os.path.exists(checkpoint_file):
        try:
            with open(checkpoint_file, 'r') as f:
                checkpoint_data = json.load(f)
            print(f"📂 Found checkpoint file, resuming from previous state...")
        except:
            checkpoint_data = {}
    
    if data_type in ['hearings', 'both']:
        print(f"\n📋 Fetching all hearings for Congress {congress_number}...")
        
        # Load existing data if resuming
        hearings = checkpoint_data.get('hearings', [])
        offset = checkpoint_data.get('hearings_offset', 0)
        limit = 250  # Max allowed by API
        
        # Get total count first
        initial_response = make_request('/hearing', {
            'congress': congress_number,
            'limit': 1,
            'offset': 0
        })
        total_hearings = initial_response.get('pagination', {}).get('count', 0)
        
        if hearings:
            print(f"📂 Resuming from {len(hearings)} hearings already fetched...")
        
        with tqdm(total=total_hearings, initial=len(hearings), desc=f"Congress {congress_number} Hearings", unit="hearing") as pbar:
            retry_count = 0
            max_retries = 3
            
            while len(hearings) < total_hearings:
                try:
                    response = make_request('/hearing', {
                        'congress': congress_number,
                        'limit': limit,
                        'offset': offset
                    })
                    
                    batch = response.get('hearings', [])
                    if not batch:
                        break
                        
                    hearings.extend(batch)
                    pbar.update(len(batch))
                    offset += limit
                    retry_count = 0  # Reset retry count on success
                    
                    # Save checkpoint every 1000 items
                    if len(hearings) % 1000 == 0:
                        checkpoint_data['hearings'] = hearings
                        checkpoint_data['hearings_offset'] = offset
                        with open(checkpoint_file, 'w') as f:
                            json.dump(checkpoint_data, f)
                        pbar.set_postfix({'saved': len(hearings)})
                    
                    time.sleep(0.1)  # Be nice to the API
                    
                except Exception as e:
                    retry_count += 1
                    if retry_count >= max_retries:
                        print(f"\n⚠️  Failed after {max_retries} retries: {e}")
                        print(f"💾 Saving partial data ({len(hearings)} hearings)...")
                        break
                    else:
                        wait_time = 2 ** retry_count  # Exponential backoff
                        pbar.set_postfix({'retry': f'{retry_count}/{max_retries}', 'wait': f'{wait_time}s'})
                        time.sleep(wait_time)
            
        results['hearings'] = {
            'count': len(hearings),
            'data': hearings
        }
        print(f"✅ Found {len(hearings)} hearings")
        
    if data_type in ['meetings', 'both']:
        print(f"\n🏛️ Fetching all committee meetings for Congress {congress_number}...")
        
        # Load existing data if resuming
        meetings = checkpoint_data.get('meetings', [])
        offset = checkpoint_data.get('meetings_offset', 0)
        limit = 250
        
        # Get total count first
        initial_response = make_request('/committee-meeting', {
            'congress': congress_number,
            'limit': 1,
            'offset': 0
        })
        total_meetings = initial_response.get('pagination', {}).get('count', 0)
        
        if meetings:
            print(f"📂 Resuming from {len(meetings)} meetings already fetched...")
        
        with tqdm(total=total_meetings, initial=len(meetings), desc=f"Congress {congress_number} Meetings", unit="meeting") as pbar:
            retry_count = 0
            max_retries = 3
            
            while len(meetings) < total_meetings:
                try:
                    response = make_request('/committee-meeting', {
                        'congress': congress_number,
                        'limit': limit,
                        'offset': offset
                    })
                    
                    batch = response.get('committeeMeetings', [])
                    if not batch:
                        break
                        
                    meetings.extend(batch)
                    pbar.update(len(batch))
                    offset += limit
                    retry_count = 0
                    
                    # Save checkpoint every 1000 items
                    if len(meetings) % 1000 == 0:
                        checkpoint_data['meetings'] = meetings
                        checkpoint_data['meetings_offset'] = offset
                        with open(checkpoint_file, 'w') as f:
                            json.dump(checkpoint_data, f)
                        pbar.set_postfix({'saved': len(meetings)})
                    
                    time.sleep(0.1)
                    
                except Exception as e:
                    retry_count += 1
                    if retry_count >= max_retries:
                        print(f"\n⚠️  Failed after {max_retries} retries: {e}")
                        print(f"💾 Saving partial data ({len(meetings)} meetings)...")
                        break
                    else:
                        wait_time = 2 ** retry_count
                        pbar.set_postfix({'retry': f'{retry_count}/{max_retries}', 'wait': f'{wait_time}s'})
                        time.sleep(wait_time)
            
        results['committee_meetings'] = {
            'count': len(meetings),
            'data': meetings
        }
        print(f"✅ Found {len(meetings)} committee meetings")
    
    # Save to JSON file
    filename = f"{output_dir}/congress_{congress_number}_{data_type}.json"
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"💾 Data saved to {filename}")
    
    # Clean up checkpoint file if successful
    if os.path.exists(checkpoint_file):
        os.remove(checkpoint_file)
        print(f"🧹 Cleaned up checkpoint file")
    
    return results

def main():
    """Main function to run samples or fetch full data"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fetch Congressional hearing and committee meeting data')
    parser.add_argument('--sample', action='store_true', help='Just show samples')
    parser.add_argument('--congress', type=int, nargs='+', help='Congress number(s) to fetch (e.g., 117 118)')
    parser.add_argument('--type', choices=['hearings', 'meetings', 'both'], default='both', help='Type of data to fetch')
    parser.add_argument('--output', default='data', help='Output directory for JSON files')
    parser.add_argument('--no-resume', action='store_true', help='Start fresh, ignore checkpoint files')
    
    args = parser.parse_args()
    
    print(f"\n🏛️  Congress API Tool")
    print(f"🔑 API Key: {'✅ Set' if API_KEY else '❌ Not Set'}")
    print(f"🕐 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    try:
        if args.sample:
            sample_hearings()
            sample_committee_meetings()
            print("\n\n✅ Sampling complete!")
        elif args.congress:
            print(f"\n🎯 Fetching data for Congress(es): {', '.join(map(str, args.congress))}")
            print(f"📊 Data type: {args.type}")
            print(f"📁 Output directory: {args.output}\n")
            
            total_hearings = 0
            total_meetings = 0
            
            for congress_num in args.congress:
                result = fetch_all_data_for_congress(congress_num, args.type, args.output, resume=not args.no_resume)
                if 'hearings' in result:
                    total_hearings += result['hearings']['count']
                if 'committee_meetings' in result:
                    total_meetings += result['committee_meetings']['count']
            
            print(f"\n\n🎉 All data fetched successfully!")
            print(f"📊 Summary:")
            if args.type in ['hearings', 'both']:
                print(f"   - Total hearings: {total_hearings:,}")
            if args.type in ['meetings', 'both']:
                print(f"   - Total committee meetings: {total_meetings:,}")
            print(f"   - Congress(es): {', '.join(map(str, args.congress))}")
            print(f"   - Files saved in: {args.output}/")
        else:
            print("📌 Usage examples:")
            print("   Sample mode: python congress_api_sampler.py --sample")
            print("   Last 5 years: python congress_api_sampler.py --congress 115 116 117 118 119")
            print("   Current Congress: python congress_api_sampler.py --congress 119")
            print("\n💡 Congress numbers:")
            print("   119th: 2025-2026 (current)")
            print("   118th: 2023-2024")
            print("   117th: 2021-2022")
            print("   116th: 2019-2020")
            print("   115th: 2017-2018")
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error making API request: {e}")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()
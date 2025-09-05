import json
import requests
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import time
from tqdm import tqdm
from difflib import SequenceMatcher

load_dotenv()
API_KEY = os.environ.get('CONGRESS_API_KEY')

def build_comprehensive_ec_index():
    """Build a comprehensive index of ALL Energy & Commerce events"""
    
    # For testing, use the smaller index if it exists
    if os.path.exists("ec_date_index.json"):
        print("📂 Using existing small index for testing...")
        with open("ec_date_index.json", 'r') as f:
            return json.load(f)
    
    index_file = "ec_comprehensive_index.json"
    if os.path.exists(index_file):
        print("📂 Loading existing comprehensive index...")
        with open(index_file, 'r') as f:
            return json.load(f)
    
    print("🔨 Building comprehensive Energy & Commerce index...")
    print("This will take 30-45 minutes but only needs to run once.\n")
    
    all_events = []
    
    for congress in [118, 119]:
        filename = f'data/congress_{congress}_both.json'
        if not os.path.exists(filename):
            continue
            
        print(f"\n📋 Processing {congress}th Congress...")
        data = json.load(open(filename))
        
        # Get House meetings
        meetings = data['committee_meetings']['data']
        house_meetings = [m for m in meetings if m['chamber'] == 'House']
        
        print(f"   Checking {len(house_meetings)} House meetings...")
        
        # Check ALL meetings
        ec_count = 0
        with tqdm(total=len(house_meetings), desc=f"Congress {congress}") as pbar:
            for meeting in house_meetings:
                try:
                    url = f"{meeting['url']}&api_key={API_KEY}"
                    resp = requests.get(url, timeout=10)
                    
                    if resp.status_code == 200:
                        details = resp.json()
                        cm = details.get('committeeMeeting', {})
                        
                        # Check if Energy & Commerce
                        committees = cm.get('committees', [])
                        for committee in committees:
                            name = committee.get('name', '')
                            if 'Energy' in name and 'Commerce' in name:
                                event = {
                                    'eventId': cm['eventId'],
                                    'congress': congress,
                                    'date': cm.get('date'),
                                    'title': cm.get('title', ''),
                                    'committee': name,
                                    'type': cm.get('type'),
                                    'meetingStatus': cm.get('meetingStatus')
                                }
                                all_events.append(event)
                                ec_count += 1
                                
                                if ec_count % 10 == 0:
                                    pbar.set_postfix({'E&C found': ec_count})
                                break
                    
                    time.sleep(0.05)  # Rate limit
                    
                except Exception as e:
                    pass  # Skip errors
                
                pbar.update(1)
        
        print(f"   Found {ec_count} Energy & Commerce events")
    
    # Sort by date
    all_events.sort(key=lambda x: x.get('date') or '', reverse=True)
    
    # Save the index
    with open(index_file, 'w') as f:
        json.dump(all_events, f, indent=2)
    
    print(f"\n✅ Saved {len(all_events)} total Energy & Commerce events")
    
    return all_events

def normalize_title(title: str) -> str:
    """Normalize title for comparison"""
    import re
    # Remove common prefixes
    title = re.sub(r'^(.*?)(Hearing|Markup|Subcommittee|Committee|Full Committee):\s*', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\s+', ' ', title)
    return title.lower().strip()

def calculate_match_score(youtube_video: dict, congress_event: dict) -> dict:
    """Calculate match score between YouTube video and Congress event"""
    
    score = 0.0
    reasons = []
    
    # Extract dates
    yt_date = None
    if youtube_video.get('liveStreamingDetails', {}).get('actualStartTime'):
        yt_date = youtube_video['liveStreamingDetails']['actualStartTime'][:10]
    
    congress_date = None
    if congress_event.get('date'):
        congress_date = congress_event['date'][:10]
    
    # Date matching (50% weight)
    if yt_date and congress_date:
        if yt_date == congress_date:
            score += 0.5
            reasons.append(f"Exact date match: {yt_date}")
        else:
            # Check if within 1 day
            yt_dt = datetime.fromisoformat(yt_date)
            cg_dt = datetime.fromisoformat(congress_date)
            diff = abs((yt_dt - cg_dt).days)
            if diff == 1:
                score += 0.25
                reasons.append(f"Date within 1 day: {yt_date} vs {congress_date}")
    
    # Title similarity (40% weight)
    yt_title = normalize_title(youtube_video.get('title', ''))
    cg_title = normalize_title(congress_event.get('title', ''))
    
    title_similarity = SequenceMatcher(None, yt_title, cg_title).ratio()
    title_score = title_similarity * 0.4
    score += title_score
    
    if title_similarity > 0.8:
        reasons.append(f"High title similarity: {title_similarity:.2f}")
    elif title_similarity > 0.6:
        reasons.append(f"Moderate title similarity: {title_similarity:.2f}")
    
    # Keyword matching (10% weight)
    keywords = ['markup', 'oversight', 'investigation', 'hearing', 'briefing']
    yt_lower = youtube_video.get('title', '').lower()
    cg_lower = congress_event.get('title', '').lower()
    
    for keyword in keywords:
        if keyword in yt_lower and keyword in cg_lower:
            score += 0.02
            reasons.append(f"Keyword match: {keyword}")
    
    return {
        'score': score,
        'reasons': reasons,
        'eventId': congress_event['eventId'],
        'congress_title': congress_event['title'],
        'congress_date': congress_date,
        'youtube_title': youtube_video['title'],
        'youtube_date': yt_date
    }

def match_all_youtube_videos():
    """Match all YouTube videos to Congress events"""
    
    # Load or build the comprehensive index
    ec_events = build_comprehensive_ec_index()
    
    # Load YouTube data
    youtube_data = json.load(open('house_energy_commerce_full.json'))
    
    # Filter videos with live streaming details
    live_videos = [v for v in youtube_data['videos'] if v.get('liveStreamingDetails')]
    
    print(f"\n📺 Matching {len(live_videos)} YouTube live streams to Congress events...")
    
    matches = []
    unmatched = []
    
    for video in tqdm(live_videos, desc="Matching videos"):
        best_match = None
        best_score = 0
        
        # Check all Congress events
        for event in ec_events:
            match_result = calculate_match_score(video, event)
            
            if match_result['score'] > best_score:
                best_score = match_result['score']
                best_match = match_result
        
        if best_match and best_score >= 0.6:  # 60% threshold
            matches.append({
                'youtube_id': video['id'],
                'youtube_title': video['title'],
                'youtube_date': video['liveStreamingDetails']['actualStartTime'],
                'eventId': best_match['eventId'],
                'congress_title': best_match['congress_title'],
                'score': best_score,
                'reasons': best_match['reasons']
            })
        else:
            unmatched.append({
                'youtube_id': video['id'],
                'youtube_title': video['title'],
                'youtube_date': video.get('liveStreamingDetails', {}).get('actualStartTime'),
                'best_score': best_score
            })
    
    # Save results
    results = {
        'metadata': {
            'total_youtube_videos': len(live_videos),
            'matched': len(matches),
            'unmatched': len(unmatched),
            'match_rate': f"{len(matches)/len(live_videos)*100:.1f}%",
            'timestamp': datetime.now().isoformat()
        },
        'matches': sorted(matches, key=lambda x: x['youtube_date'], reverse=True),
        'unmatched': sorted(unmatched, key=lambda x: x['youtube_date'] or '', reverse=True)
    }
    
    with open('youtube_congress_matches.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Matching complete!")
    print(f"   Matched: {len(matches)} ({len(matches)/len(live_videos)*100:.1f}%)")
    print(f"   Unmatched: {len(unmatched)}")
    print(f"   Results saved to: youtube_congress_matches.json")
    
    # Show sample matches
    print(f"\n📊 Sample high-confidence matches:")
    high_confidence = [m for m in matches if m['score'] >= 0.8]
    for match in high_confidence[:5]:
        print(f"\n   YouTube: {match['youtube_title'][:60]}...")
        print(f"   Congress: {match['congress_title'][:60]}...")
        print(f"   Event ID: {match['eventId']}")
        print(f"   Score: {match['score']:.2f}")
        print(f"   Reasons: {', '.join(match['reasons'])}")

def main():
    print("🎯 YouTube to Congress Event Matching Tool")
    print("=" * 60)
    
    match_all_youtube_videos()

if __name__ == "__main__":
    main()
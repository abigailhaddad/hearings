import json
import os
from datetime import datetime, timedelta
from tqdm import tqdm
from difflib import SequenceMatcher

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
    
    # Date matching (40% weight - reduced to give more weight to title)
    if yt_date and congress_date:
        if yt_date == congress_date:
            score += 0.4
            reasons.append(f"Exact date match: {yt_date}")
        else:
            # Check if within days - more forgiving for YouTube being after Congress
            yt_dt = datetime.fromisoformat(yt_date)
            cg_dt = datetime.fromisoformat(congress_date)
            diff = (yt_dt - cg_dt).days
            
            # YouTube often posts 1-2 days after the event
            if 0 <= diff <= 2:  # YouTube is 0-2 days after Congress
                score += 0.3
                reasons.append(f"YouTube {diff} day(s) after Congress: {yt_date} vs {congress_date}")
            elif -1 <= diff < 0:  # YouTube is 1 day before Congress
                score += 0.2
                reasons.append(f"YouTube 1 day before Congress: {yt_date} vs {congress_date}")
            elif abs(diff) <= 3:  # Within 3 days either way
                score += 0.1
                reasons.append(f"Date within 3 days: {yt_date} vs {congress_date}")
    elif not yt_date and congress_date:
        # No YouTube date - don't penalize too much
        score += 0.05
        reasons.append("No YouTube date available")
    
    # Title similarity (45% weight - increased importance)
    yt_title = normalize_title(youtube_video.get('title', ''))
    cg_title = normalize_title(congress_event.get('title', ''))
    
    title_similarity = SequenceMatcher(None, yt_title, cg_title).ratio()
    title_score = title_similarity * 0.45
    score += title_score
    
    if title_similarity > 0.8:
        reasons.append(f"High title similarity: {title_similarity:.2f}")
    elif title_similarity > 0.6:
        reasons.append(f"Moderate title similarity: {title_similarity:.2f}")
    elif title_similarity > 0.4:
        reasons.append(f"Low title similarity: {title_similarity:.2f}")
    
    # Committee matching (10% weight)
    yt_lower = youtube_video.get('title', '').lower()
    committee_name = (congress_event.get('committeeName') or '').lower()
    
    # Check for subcommittee abbreviations
    committee_keywords = {
        'health': ['health', 'hhs', 'fda', 'cdc', 'nih'],
        'energy': ['energy', 'ferc', 'nuclear', 'pipeline'],
        'oversight': ['oversight', 'o&i', 'investigation'],
        'communications': ['communications', 'technology', 'tech', 'ftc'],
        'commerce': ['commerce', 'manufacturing', 'trade'],
        'environment': ['environment', 'epa', 'climate']
    }
    
    for key, keywords in committee_keywords.items():
        if key in committee_name:
            for kw in keywords:
                if kw in yt_lower:
                    score += 0.02
                    reasons.append(f"Committee keyword match: {kw}")
                    break
    
    # Event type matching (5% weight)
    event_type = congress_event.get('type', '').lower()
    if event_type in yt_lower:
        score += 0.05
        reasons.append(f"Event type match: {event_type}")
    
    return {
        'score': score,
        'reasons': reasons,
        'eventId': congress_event['eventId'],
        'congress_title': congress_event['title'],
        'congress_date': congress_date,
        'youtube_title': youtube_video['title'],
        'youtube_date': yt_date,
        'committee': congress_event.get('committeeName', 'Unknown')
    }

def match_youtube_to_expanded_congress():
    """Match YouTube videos to expanded Congress dataset"""
    
    # Load expanded E&C index
    print("📂 Loading expanded E&C index...")
    ec_events = json.load(open('../outputs/ec_filtered_index.json'))
    print(f"   Loaded {len(ec_events)} E&C events")
    
    # Load YouTube data
    youtube_data = json.load(open('../outputs/house_energy_commerce_full.json'))
    live_videos = [v for v in youtube_data['videos'] if v.get('liveStreamingDetails')]
    print(f"📺 Matching {len(live_videos)} YouTube live streams")
    
    matches = []
    unmatched = []
    
    # Create date index for faster matching
    print("\n🗂️  Building date index...")
    date_index = {}
    for event in ec_events:
        if event.get('date'):
            date = event['date'][:10]
            if date not in date_index:
                date_index[date] = []
            date_index[date].append(event)
    
    print(f"   Indexed {len(date_index)} unique dates with E&C events")
    
    # Match videos
    print("\n🔍 Matching videos...")
    for video in tqdm(live_videos, desc="Matching"):
        best_match = None
        best_score = 0
        
        # Get video date
        yt_date = None
        if video.get('liveStreamingDetails', {}).get('actualStartTime'):
            yt_date = video['liveStreamingDetails']['actualStartTime'][:10]
        
        # First check exact date matches
        candidates = []
        if yt_date and yt_date in date_index:
            candidates.extend(date_index[yt_date])
        
        # Check -3 to +1 days (Congress date 3 days before to 1 day after YouTube)
        if yt_date:
            yt_dt = datetime.fromisoformat(yt_date)
            for offset in [-3, -2, -1, 1]:
                check_date = (yt_dt + timedelta(days=offset)).strftime('%Y-%m-%d')
                if check_date in date_index:
                    candidates.extend(date_index[check_date])
        
        # If no date candidates, check all events
        if not candidates:
            candidates = ec_events
        
        # Score all candidates
        for event in candidates:
            match_result = calculate_match_score(video, event)
            
            if match_result['score'] > best_score:
                best_score = match_result['score']
                best_match = match_result
        
        # More flexible matching criteria
        if best_match and (
            best_score >= 0.4 or  # General threshold
            (best_match['reasons'] and any('High title similarity' in r for r in best_match['reasons'])) or  # High title match
            (not yt_date and best_score >= 0.3)  # No date but decent match
        ):
            # Get congress number from the matched event
            congress_num = next((e['congress'] for e in candidates if e['eventId'] == best_match['eventId']), None)
            
            matches.append({
                'youtube_id': video['id'],
                'youtube_title': video['title'],
                'youtube_date': video.get('liveStreamingDetails', {}).get('actualStartTime'),
                'eventId': best_match['eventId'],
                'congress_title': best_match['congress_title'],
                'congress_date': best_match['congress_date'],
                'committee': best_match['committee'],
                'score': best_score,
                'reasons': best_match['reasons'],
                'congress_url': f"https://www.congress.gov/event/{congress_num}/house-event/{best_match['eventId']}" if congress_num else None
            })
        else:
            unmatched.append({
                'youtube_id': video['id'],
                'youtube_title': video['title'],
                'youtube_date': video.get('liveStreamingDetails', {}).get('actualStartTime'),
                'best_score': best_score,
                'best_match': best_match['congress_title'] if best_match else None
            })
    
    # Save results
    results = {
        'metadata': {
            'total_youtube_videos': len(live_videos),
            'total_congress_events': len(ec_events),
            'matched': len(matches),
            'unmatched': len(unmatched),
            'match_rate': f"{len(matches)/len(live_videos)*100:.1f}%",
            'timestamp': datetime.now().isoformat()
        },
        'matches': sorted(matches, key=lambda x: x.get('youtube_date') or '', reverse=True),
        'unmatched': sorted(unmatched, key=lambda x: x.get('youtube_date') or '', reverse=True)
    }
    
    with open('../outputs/youtube_congress_expanded_matches.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Matching complete!")
    print(f"   Matched: {len(matches)} ({len(matches)/len(live_videos)*100:.1f}%)")
    print(f"   Unmatched: {len(unmatched)}")
    print(f"   Results saved to: youtube_congress_expanded_matches.json")
    
    # Show improvements
    print(f"\n📈 Improvement from original:")
    print(f"   Original: 7 matches (7.6%)")
    print(f"   Expanded: {len(matches)} matches ({len(matches)/len(live_videos)*100:.1f}%)")
    print(f"   Improvement: +{len(matches)-7} matches (+{(len(matches)/len(live_videos)*100)-7.6:.1f}%)")
    
    # Show sample matches
    print(f"\n📊 Sample high-confidence matches:")
    high_confidence = [m for m in matches if m['score'] >= 0.7]
    for match in high_confidence[:5]:
        print(f"\n   YouTube: {match['youtube_title'][:60]}...")
        print(f"   Congress: {match['congress_title'][:60]}...")
        print(f"   Committee: {match['committee']}")
        print(f"   Score: {match['score']:.2f}")
        print(f"   Reasons: {', '.join(match['reasons'])}")

if __name__ == "__main__":
    match_youtube_to_expanded_congress()
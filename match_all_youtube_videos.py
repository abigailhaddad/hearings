#!/usr/bin/env python3
"""
Match YouTube videos from Energy & Commerce committee with Congress API data
"""

import json
import re
from datetime import datetime, timedelta
from difflib import SequenceMatcher


def normalize_title(title):
    """Normalize title for comparison"""
    # Remove common prefixes
    title = re.sub(r'^(.*?)(Hearing|Markup|Subcommittee|Committee|Full Committee):\s*', '', title, flags=re.IGNORECASE)
    # Remove extra whitespace
    title = re.sub(r'\s+', ' ', title)
    return title.lower().strip()


def extract_date_from_info(date_info):
    """Extract approximate date from YouTube date info like '2 years ago'"""
    if not date_info:
        return None
    
    # For now, just return None - could implement more sophisticated parsing
    return None


def calculate_match_score(youtube_video, congress_event):
    """Calculate match score between YouTube video and Congress event"""
    
    score = 0.0
    reasons = []
    
    # Title similarity (60% weight)
    yt_title = normalize_title(youtube_video.get('title', ''))
    cg_title = normalize_title(congress_event.get('title', ''))
    
    title_similarity = SequenceMatcher(None, yt_title, cg_title).ratio()
    title_score = title_similarity * 0.6
    score += title_score
    
    if title_similarity > 0.8:
        reasons.append(f"High title similarity: {title_similarity:.2f}")
    elif title_similarity > 0.6:
        reasons.append(f"Moderate title similarity: {title_similarity:.2f}")
    elif title_similarity > 0.4:
        reasons.append(f"Low title similarity: {title_similarity:.2f}")
    
    # Check for key terms matching (20% weight)
    key_terms = []
    
    # Extract key terms from congress title
    congress_words = set(cg_title.split())
    youtube_words = set(yt_title.split())
    
    # Find significant overlapping words (>3 chars)
    overlapping = congress_words & youtube_words
    significant_overlaps = [w for w in overlapping if len(w) > 3 and w not in ['the', 'and', 'for', 'with']]
    
    if significant_overlaps:
        score += 0.2 * min(len(significant_overlaps) / 5, 1.0)
        reasons.append(f"Key terms match: {', '.join(significant_overlaps[:5])}")
    
    # Committee matching (10% weight)
    if 'energy' in yt_title and 'commerce' in yt_title:
        score += 0.1
        reasons.append("Committee name match")
    
    # Event type matching (10% weight)
    event_type = congress_event.get('type', '').lower()
    if event_type and event_type in yt_title:
        score += 0.1
        reasons.append(f"Event type match: {event_type}")
    
    return {
        'score': score,
        'reasons': reasons,
        'congress_title': congress_event['title'],
        'committee': congress_event.get('committees', [{}])[0].get('name', 'Unknown') if congress_event.get('committees') else 'Unknown'
    }


def main():
    print("🎯 Matching YouTube videos with Congress API data")
    print("=" * 70)
    
    # Load YouTube data
    print("\n📺 Loading YouTube data...")
    with open('ec_youtube_videos_for_matching.json', 'r') as f:
        youtube_videos = json.load(f)
    print(f"   Loaded {len(youtube_videos)} YouTube videos")
    
    # Load Congress data - check for comprehensive index first
    congress_events = []
    
    # Try to load from comprehensive index
    try:
        with open('outputs/ec_comprehensive_index.json', 'r') as f:
            data = json.load(f)
            congress_events = data['events']
            print(f"📂 Loaded comprehensive E&C index: {len(congress_events)} events")
    except:
        # Fall back to filtered index
        try:
            with open('outputs/ec_filtered_index.json', 'r') as f:
                congress_events = json.load(f)
                print(f"📂 Loaded filtered E&C index: {len(congress_events)} events")
        except:
            # Fall back to loading individual Congress files
            print("📂 Loading individual Congress files...")
            for congress_num in [115, 116, 117, 118, 119]:
                try:
                    with open(f'data/congress_{congress_num}_both.json', 'r') as f:
                        data = json.load(f)
                        
                        # Filter for Energy & Commerce events
                        for event in data.get('events', []):
                            committees = event.get('committees', [])
                            for committee in committees:
                                if 'energy' in committee.get('name', '').lower() and 'commerce' in committee.get('name', '').lower():
                                    congress_events.append(event)
                                    break
                        
                        print(f"   Congress {congress_num}: Found {len([e for e in data.get('events', []) if any('energy' in c.get('name', '').lower() and 'commerce' in c.get('name', '').lower() for c in e.get('committees', []))])} E&C events")
                except Exception as e:
                    print(f"   Could not load congress_{congress_num}_both.json: {e}")
    
    if not congress_events:
        print("❌ No Congress events found!")
        return
    
    print(f"\n📊 Total E&C events to match against: {len(congress_events)}")
    
    # Match videos
    matches = []
    unmatched = []
    
    print("\n🔍 Matching videos...")
    for video in youtube_videos:
        best_match = None
        best_score = 0
        
        # Score against all Congress events
        for event in congress_events:
            match_result = calculate_match_score(video, event)
            
            if match_result['score'] > best_score:
                best_score = match_result['score']
                best_match = {
                    **match_result,
                    'event': event
                }
        
        # Accept matches with reasonable scores
        if best_match and best_score >= 0.3:
            matches.append({
                'youtube_id': video['video_id'],
                'youtube_title': video['title'],
                'youtube_url': video['url'],
                'congress_title': best_match['congress_title'],
                'congress_event_id': best_match['event'].get('id'),
                'committee': best_match['committee'],
                'score': best_score,
                'reasons': best_match['reasons']
            })
        else:
            unmatched.append({
                'youtube_id': video['video_id'],
                'youtube_title': video['title'],
                'best_score': best_score,
                'best_match': best_match['congress_title'] if best_match else None
            })
    
    # Save results
    results = {
        'metadata': {
            'total_youtube_videos': len(youtube_videos),
            'total_congress_events': len(congress_events),
            'matched': len(matches),
            'unmatched': len(unmatched),
            'match_rate': f"{len(matches)/len(youtube_videos)*100:.1f}%",
            'timestamp': datetime.now().isoformat()
        },
        'matches': sorted(matches, key=lambda x: x['score'], reverse=True),
        'unmatched': unmatched
    }
    
    with open('youtube_congress_matches.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Matching complete!")
    print(f"   Matched: {len(matches)} videos ({len(matches)/len(youtube_videos)*100:.1f}%)")
    print(f"   Unmatched: {len(unmatched)} videos")
    print(f"   Results saved to: youtube_congress_matches.json")
    
    # Show top matches
    print(f"\n🏆 Top 10 matches:")
    for i, match in enumerate(matches[:10], 1):
        print(f"\n{i}. YouTube: {match['youtube_title'][:60]}...")
        print(f"   Congress: {match['congress_title'][:60]}...")
        print(f"   Score: {match['score']:.2f}")
        print(f"   Reasons: {', '.join(match['reasons'])}")
    
    # Search for the specific FTC video
    print(f"\n🔍 Searching for FTC Privacy hearing...")
    ftc_videos = [v for v in youtube_videos if 'ftc' in v['title'].lower() or 'federal trade commission' in v['title'].lower()]
    print(f"   Found {len(ftc_videos)} FTC-related videos")
    
    for video in ftc_videos:
        if 'privacy' in video['title'].lower():
            print(f"\n   ✓ Found: {video['title']}")
            print(f"     ID: {video['video_id']}")
            print(f"     URL: {video['url']}")
            
            # Check if it matched
            matched = next((m for m in matches if m['youtube_id'] == video['video_id']), None)
            if matched:
                print(f"     Matched to: {matched['congress_title']}")
                print(f"     Score: {matched['score']:.2f}")
            else:
                print("     ❌ No match found")


if __name__ == "__main__":
    main()
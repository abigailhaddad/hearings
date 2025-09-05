#!/usr/bin/env python3
"""
Match YouTube videos from Energy & Commerce committee with Congress API data
"""

import json
import re
from datetime import datetime, timedelta
from difflib import SequenceMatcher


def normalize_title(title):
    """Normalize title for comparison - smart version"""
    original = title
    
    # First, always remove date patterns at the beginning
    title = re.sub(r'^(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{1,2},?\s+\d{4}\s+', '', title, flags=re.IGNORECASE)
    
    # Extract content from parentheses if substantial
    paren_match = re.search(r'\((.*?)\)', title)
    if paren_match and len(paren_match.group(1).split()) > 2:
        paren_content = paren_match.group(1)
    else:
        paren_content = ""
    
    # Try aggressive normalization first (remove committee words but keep important procedural words)
    aggressive = title
    aggressive = re.sub(r'\b(Health |Energy |O&I |C&T |CMT |IDC |Full Committee |Committee |Subcommittee )', '', aggressive, flags=re.IGNORECASE)
    # Keep Markup but remove less important procedural words
    aggressive = re.sub(r'\b(Hearing|Meeting|Legislative|Oversight|Business)\b', '', aggressive, flags=re.IGNORECASE)
    aggressive = re.sub(r'\s+', ' ', aggressive)
    aggressive = re.sub(r'[:\-–—]\s*$', '', aggressive)
    aggressive = aggressive.strip()
    
    # If we have substantial content after aggressive normalization, use it
    if len(aggressive) > 5 and aggressive not in ['', ':', '-', '–']:
        result = aggressive
    elif paren_content:
        # If not, but we have parentheses content, use that
        result = paren_content
    else:
        # Otherwise, do minimal normalization (keep committee/type words)
        result = title
        result = re.sub(r'\s+', ' ', result)
        result = re.sub(r'[:\-–—]\s*$', '', result)
        result = result.strip()
    
    return result.lower()


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
    
    # DATE MATCHING - This is critical! (50% weight)
    yt_date = youtube_video.get('exact_date') or youtube_video.get('approximate_date')
    cg_date = congress_event.get('date', '')[:10] if congress_event.get('date') else None
    
    if yt_date and cg_date:
        from datetime import datetime
        yt_dt = datetime.strptime(yt_date, '%Y-%m-%d')
        cg_dt = datetime.strptime(cg_date, '%Y-%m-%d')
        days_diff = abs((yt_dt - cg_dt).days)
        
        if days_diff == 0:
            # Same day - good but title match is crucial
            score += 0.3
            reasons.append(f"Exact date match: {yt_date}")
        elif days_diff <= 2:
            # Within 2 days
            score += 0.2
            reasons.append(f"Date within 2 days: {yt_date} vs {cg_date}")
        elif days_diff <= 7:
            # Within a week
            score += 0.1
            reasons.append(f"Date within a week: {days_diff} days apart")
        else:
            # More than a week - strong penalty
            score -= 0.5
            reasons.append(f"Date mismatch: {days_diff} days apart")
    else:
        # No date info - can't properly match
        score += 0.0
        reasons.append("Missing date information")
    
    # Title similarity (60% weight - increased for better matching)
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
    
    # Event type matching (10% weight)
    event_type = congress_event.get('type', '').lower()
    if event_type and event_type in yt_title:
        score += 0.1
        reasons.append(f"Event type match: {event_type}")
    
    return {
        'score': score,
        'reasons': reasons,
        'congress_title': congress_event['title'],
        'committee': congress_event.get('committeeName') or (congress_event.get('committees', [{}])[0].get('name', 'House Energy and Commerce') if congress_event.get('committees') else 'House Energy and Commerce')
    }


def main():
    print("🎯 Matching YouTube videos with Congress API data")
    print("=" * 70)
    
    # Load YouTube data
    print("\n📺 Loading YouTube data...")
    # Use the file with exact dates
    with open('ec_youtube_videos_with_exact_dates.json', 'r') as f:
        youtube_videos = json.load(f)
    
    # Filter to only videos with exact dates
    youtube_videos = [v for v in youtube_videos if v.get('exact_date')]
    print(f"   Loaded {len(youtube_videos)} YouTube videos with exact dates")
    
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
        all_matches = []
        
        # Score against all Congress events
        for event in congress_events:
            match_result = calculate_match_score(video, event)
            all_matches.append({
                **match_result,
                'event': event
            })
        
        # Sort by score
        all_matches.sort(key=lambda x: x['score'], reverse=True)
        
        # Get the best match
        best_match = all_matches[0] if all_matches else None
        best_score = best_match['score'] if best_match else 0
        
        # For same-day matches, ensure we have good title similarity
        # If the best match is on the same day but has poor title match, check if there's a better same-day match
        if best_match and 'Exact date match' in str(best_match.get('reasons', [])):
            yt_date = video.get('exact_date')
            # Get all same-day matches
            same_day_matches = [m for m in all_matches if m['event'].get('date', '')[:10] == yt_date]
            
            if same_day_matches:
                # Find the one with best title similarity
                best_same_day = max(same_day_matches, key=lambda m: SequenceMatcher(None, 
                    normalize_title(video.get('title', '')), 
                    normalize_title(m['event'].get('title', ''))).ratio())
                
                # Use this if it has reasonable title similarity (>0.4)
                title_sim = SequenceMatcher(None, 
                    normalize_title(video.get('title', '')), 
                    normalize_title(best_same_day['event'].get('title', ''))).ratio()
                
                if title_sim > 0.4:
                    best_match = best_same_day
                    best_score = best_match['score']
        
        # Accept matches only if they have a positive score and reasonable total score
        # Lowered threshold to 0.45 to catch same-day events with moderate title similarity
        if best_match and best_score >= 0.45:
            congress_num = best_match['event'].get('congress')
            event_id = best_match['event'].get('eventId')
            congress_url = f"https://www.congress.gov/event/{congress_num}th-congress/house-event/{event_id}" if congress_num and event_id else None
            
            matches.append({
                'youtube_id': video['video_id'],
                'youtube_title': video['title'],
                'youtube_url': video['url'],
                'youtube_date': video.get('exact_date') or video.get('approximate_date'),
                'congress_title': best_match['congress_title'],
                'eventId': best_match['event'].get('eventId'),
                'congress_date': best_match['event'].get('date', '')[:10] if best_match['event'].get('date') else None,
                'congress_url': congress_url,
                'committee': best_match['committee'],
                'score': best_score,
                'reasons': best_match['reasons']
            })
        else:
            unmatched.append({
                'youtube_id': video['video_id'],
                'youtube_title': video['title'],
                'youtube_date': video.get('exact_date') or video.get('approximate_date'),
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
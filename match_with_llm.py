#!/usr/bin/env python3
"""
Enhanced YouTube-Congress matching using LLM for uncertain cases
"""

import json
import os
from datetime import datetime
from difflib import SequenceMatcher
from litellm import completion
from pydantic import BaseModel, Field
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class MatchDecision(BaseModel):
    """Model for LLM matching decision"""
    congress_event_id: Optional[str] = Field(
        description="The eventId of the matching Congress event, or null if no good match"
    )
    confidence: str = Field(
        description="Confidence level: high, medium, or low"
    )
    reasoning: str = Field(
        description="Brief explanation of the matching decision"
    )

def calculate_basic_match_score(youtube_video, congress_event):
    """Calculate match score between YouTube video and Congress event"""
    score = 0.0
    
    # Date matching
    yt_date = youtube_video.get('exact_date')
    cg_date = congress_event.get('date', '')[:10] if congress_event.get('date') else None
    
    if yt_date and cg_date:
        yt_dt = datetime.strptime(yt_date, '%Y-%m-%d')
        cg_dt = datetime.strptime(cg_date, '%Y-%m-%d')
        days_diff = abs((yt_dt - cg_dt).days)
        
        if days_diff == 0:
            score += 0.3
        elif days_diff <= 2:
            score += 0.2
        elif days_diff <= 7:
            score += 0.1
        else:
            score -= 0.5
    
    # Title similarity
    yt_title = youtube_video.get('title', '').lower()
    cg_title = congress_event.get('title', '').lower()
    
    title_similarity = SequenceMatcher(None, yt_title, cg_title).ratio()
    score += title_similarity * 0.6
    
    # Event type matching
    if 'markup' in yt_title and 'markup' in cg_title:
        score += 0.1
    elif 'hearing' in yt_title and 'hearing' in congress_event.get('type', '').lower():
        score += 0.1
    elif 'meeting' in yt_title and 'meeting' in congress_event.get('type', '').lower():
        score += 0.1
    
    return score

def get_llm_match(youtube_video, candidate_events):
    """Use LLM to decide best match among candidates"""
    
    # Prepare the prompt
    candidates_text = []
    for i, event in enumerate(candidate_events):
        candidates_text.append(f"""
{i+1}. Congress Event ID: {event['eventId']}
   Date: {event.get('date', '')[:10]}
   Title: {event['title']}
   Type: {event.get('type', 'Unknown')}
   Committee: {event.get('committeeName', 'Unknown')}""")
    
    prompt = f"""You are matching YouTube videos of congressional committee events with official Congress records.

YouTube Video:
- Date: {youtube_video.get('exact_date', 'Unknown')}
- Title: {youtube_video['title']}

Potential Congress Matches:
{''.join(candidates_text)}

Which Congress event (if any) matches this YouTube video? Consider:
1. Dates should be the same or very close (within a few days)
2. Titles should refer to the same event (even if worded differently)
3. "Full Committee Markup" on YouTube likely matches any "Markup" event on the same day
4. Sometimes YouTube titles are more descriptive than Congress titles

Return the eventId of the best match, or null if none are good matches."""

    try:
        response = completion(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You match YouTube videos with Congress events. Be precise and only match if you're confident they refer to the same event."},
                {"role": "user", "content": prompt}
            ],
            response_format=MatchDecision,
            temperature=0.0
        )
        
        # Parse response
        if hasattr(response.choices[0].message, 'content'):
            content = response.choices[0].message.content
            if isinstance(content, str):
                import json
                result = json.loads(content)
            else:
                result = content
        else:
            result = response.choices[0].message.model_dump()
        
        return result
        
    except Exception as e:
        print(f"LLM error: {e}")
        return None

def main():
    print("🎯 Enhanced YouTube-Congress Matching with LLM assist")
    print("=" * 70)
    
    # Load YouTube data
    with open('ec_youtube_videos_with_exact_dates.json', 'r') as f:
        youtube_videos = json.load(f)
    
    youtube_videos = [v for v in youtube_videos if v.get('exact_date')]
    print(f"\n📺 Loaded {len(youtube_videos)} YouTube videos with exact dates")
    
    # Load Congress data
    with open('outputs/ec_filtered_index.json', 'r') as f:
        congress_events = json.load(f)
    print(f"📂 Loaded {len(congress_events)} Congress events")
    
    matches = []
    unmatched = []
    llm_assists = 0
    
    print("\n🔍 Matching videos...")
    for i, video in enumerate(youtube_videos):
        if (i + 1) % 50 == 0:
            print(f"   Progress: {i + 1}/{len(youtube_videos)}")
        
        # Calculate scores for all events
        scored_events = []
        for event in congress_events:
            score = calculate_basic_match_score(video, event)
            scored_events.append({
                'event': event,
                'score': score
            })
        
        # Sort by score
        scored_events.sort(key=lambda x: x['score'], reverse=True)
        best_score = scored_events[0]['score'] if scored_events else 0
        
        # Decision logic
        if best_score >= 0.7:
            # High confidence match - use it directly
            best_event = scored_events[0]['event']
            matches.append({
                'youtube_id': video['video_id'],
                'youtube_title': video['title'],
                'youtube_url': video.get('url', f"https://youtube.com/watch?v={video['video_id']}"),
                'youtube_date': video['exact_date'],
                'congress_title': best_event['title'],
                'eventId': best_event.get('eventId'),
                'congress_date': best_event.get('date', '')[:10],
                'congress_url': f"https://www.congress.gov/event/{best_event.get('congress')}th-congress/house-event/{best_event.get('eventId')}",
                'committee': best_event.get('committeeName', 'House Energy and Commerce'),
                'score': best_score,
                'match_method': 'algorithmic'
            })
        
        elif 0.4 <= best_score < 0.7:
            # Uncertain - use LLM to decide
            # Get candidates within reasonable date range
            yt_date = datetime.strptime(video['exact_date'], '%Y-%m-%d')
            candidates = []
            
            for scored in scored_events[:10]:  # Top 10 candidates
                event = scored['event']
                if event.get('date'):
                    event_date = datetime.strptime(event['date'][:10], '%Y-%m-%d')
                    days_diff = abs((yt_date - event_date).days)
                    
                    # Include events within a week
                    if days_diff <= 7:
                        candidates.append(event)
            
            if candidates:
                llm_result = get_llm_match(video, candidates)
                
                if llm_result and llm_result.get('congress_event_id'):
                    # Find the matched event
                    matched_event = None
                    for event in candidates:
                        if event.get('eventId') == llm_result['congress_event_id']:
                            matched_event = event
                            break
                    
                    if matched_event:
                        llm_assists += 1
                        matches.append({
                            'youtube_id': video['video_id'],
                            'youtube_title': video['title'],
                            'youtube_url': video.get('url', f"https://youtube.com/watch?v={video['video_id']}"),
                            'youtube_date': video['exact_date'],
                            'congress_title': matched_event['title'],
                            'eventId': matched_event.get('eventId'),
                            'congress_date': matched_event.get('date', '')[:10],
                            'congress_url': f"https://www.congress.gov/event/{matched_event.get('congress')}th-congress/house-event/{matched_event.get('eventId')}",
                            'committee': matched_event.get('committeeName', 'House Energy and Commerce'),
                            'score': best_score,
                            'match_method': 'llm_assisted',
                            'llm_confidence': llm_result.get('confidence'),
                            'llm_reasoning': llm_result.get('reasoning')
                        })
                    else:
                        unmatched.append({
                            'youtube_id': video['video_id'],
                            'youtube_title': video['title'],
                            'youtube_date': video['exact_date'],
                            'best_score': best_score,
                            'best_match': scored_events[0]['event']['title'] if scored_events else None
                        })
                else:
                    unmatched.append({
                        'youtube_id': video['video_id'],
                        'youtube_title': video['title'],
                        'youtube_date': video['exact_date'],
                        'best_score': best_score,
                        'best_match': scored_events[0]['event']['title'] if scored_events else None
                    })
            else:
                unmatched.append({
                    'youtube_id': video['video_id'],
                    'youtube_title': video['title'],
                    'youtube_date': video['exact_date'],
                    'best_score': best_score,
                    'best_match': scored_events[0]['event']['title'] if scored_events else None
                })
        
        else:
            # Low confidence - don't match
            unmatched.append({
                'youtube_id': video['video_id'],
                'youtube_title': video['title'],
                'youtube_date': video['exact_date'],
                'best_score': best_score,
                'best_match': scored_events[0]['event']['title'] if scored_events else None
            })
    
    # Save results
    results = {
        'metadata': {
            'total_youtube_videos': len(youtube_videos),
            'total_congress_events': len(congress_events),
            'matched': len(matches),
            'unmatched': len(unmatched),
            'match_rate': f"{len(matches)/len(youtube_videos)*100:.1f}%",
            'algorithmic_matches': len([m for m in matches if m['match_method'] == 'algorithmic']),
            'llm_assisted_matches': llm_assists,
            'timestamp': datetime.now().isoformat()
        },
        'matches': sorted(matches, key=lambda x: x.get('youtube_date', ''), reverse=True),
        'unmatched': unmatched
    }
    
    with open('youtube_congress_matches.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Matching complete!")
    print(f"   Total matches: {len(matches)}")
    print(f"   - Algorithmic (high confidence): {results['metadata']['algorithmic_matches']}")
    print(f"   - LLM assisted (uncertain cases): {llm_assists}")
    print(f"   Unmatched: {len(unmatched)}")
    print(f"   Match rate: {results['metadata']['match_rate']}")
    print(f"   Results saved to: youtube_congress_matches.json")
    
    # Show some LLM-assisted matches
    if llm_assists > 0:
        print(f"\n🤖 Sample LLM-assisted matches:")
        llm_matches = [m for m in matches if m['match_method'] == 'llm_assisted'][:3]
        for match in llm_matches:
            print(f"\n   YouTube: {match['youtube_title']}")
            print(f"   Congress: {match['congress_title']}")
            print(f"   Confidence: {match.get('llm_confidence', 'N/A')}")
            print(f"   Reasoning: {match.get('llm_reasoning', 'N/A')}")

if __name__ == "__main__":
    main()
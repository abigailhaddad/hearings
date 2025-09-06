#!/usr/bin/env python3
"""
Parse saved committee YouTube HTML to extract complete video dataset for matching
"""

from bs4 import BeautifulSoup
import json
import re
from datetime import datetime, timedelta
import sys
import os

def parse_relative_date(date_str):
    """Convert relative date like '2 months ago' to approximate date"""
    if not date_str:
        return None
    
    today = datetime.now()
    
    # Parse the relative date
    match = re.search(r'(\d+)\s+(hour|day|week|month|year)s?\s+ago', date_str.lower())
    if not match:
        # Check for "Streamed" prefix
        if 'streamed' in date_str.lower():
            match = re.search(r'streamed\s+(\d+)\s+(hour|day|week|month|year)s?\s+ago', date_str.lower())
    
    if not match:
        return None
    
    amount = int(match.group(1))
    unit = match.group(2) if 'streamed' not in date_str.lower() else match.group(2)
    
    if unit == 'hour':
        return (today - timedelta(hours=amount)).strftime('%Y-%m-%d')
    elif unit == 'day':
        return (today - timedelta(days=amount)).strftime('%Y-%m-%d')
    elif unit == 'week':
        return (today - timedelta(weeks=amount)).strftime('%Y-%m-%d')
    elif unit == 'month':
        # Approximate
        return (today - timedelta(days=amount * 30)).strftime('%Y-%m-%d')
    elif unit == 'year':
        return (today - timedelta(days=amount * 365)).strftime('%Y-%m-%d')
    
    return None

def extract_video_data_from_html(html_file):
    """
    Extract comprehensive video data from saved YouTube HTML
    """
    
    print(f"📖 Reading HTML file: {html_file}")
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    videos = []
    video_ids_seen = set()
    
    # First, try to extract from ytInitialData JSON
    for script in soup.find_all('script'):
        if script.string and 'ytInitialData' in script.string:
            # Extract JSON data
            match = re.search(r'ytInitialData\s*=\s*({.*?});', script.string, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    
                    # Navigate to find videos
                    tabs = data.get('contents', {}).get('twoColumnBrowseResultsRenderer', {}).get('tabs', [])
                    
                    for tab in tabs:
                        if 'tabRenderer' in tab and tab['tabRenderer'].get('selected'):
                            content = tab['tabRenderer'].get('content', {})
                            if 'richGridRenderer' in content:
                                items = content['richGridRenderer'].get('contents', [])
                                
                                for item in items:
                                    if 'richItemRenderer' in item:
                                        video_renderer = item['richItemRenderer'].get('content', {}).get('videoRenderer', {})
                                        
                                        if video_renderer:
                                            video_id = video_renderer.get('videoId', '')
                                            
                                            if video_id and video_id not in video_ids_seen:
                                                video_ids_seen.add(video_id)
                                                
                                                # Extract all available data
                                                title_runs = video_renderer.get('title', {}).get('runs', [])
                                                title = title_runs[0].get('text', '') if title_runs else ''
                                                
                                                # Date info - check multiple places
                                                date_info = ''
                                                
                                                # Check publishedTimeText
                                                published_text = video_renderer.get('publishedTimeText', {}).get('simpleText', '')
                                                if published_text:
                                                    date_info = published_text
                                                
                                                # Check videoInfo for live streams
                                                video_info = video_renderer.get('videoInfo', {}).get('runs', [])
                                                for info in video_info:
                                                    text = info.get('text', '')
                                                    if 'ago' in text or 'Streamed' in text:
                                                        date_info = text
                                                        break
                                                
                                                # View count
                                                view_count_text = video_renderer.get('viewCountText', {}).get('simpleText', '')
                                                
                                                # Length/duration
                                                duration = ''
                                                length_text = video_renderer.get('lengthText', {}).get('simpleText', '')
                                                if length_text:
                                                    duration = length_text
                                                
                                                video_data = {
                                                    'id': video_id,
                                                    'url': f'https://www.youtube.com/watch?v={video_id}',
                                                    'title': title,
                                                    'duration': duration,
                                                    'metadata': f"{view_count_text} • {date_info}" if view_count_text or date_info else "",
                                                    'views': view_count_text,
                                                    'date_info': date_info
                                                }
                                                
                                                videos.append(video_data)
                
                except Exception as e:
                    print(f"⚠️  Error parsing ytInitialData: {e}")
                    # Fall back to HTML parsing
            break
    
    # Method 1: Find all video entries with titles and metadata
    # YouTube uses specific patterns for video entries
    
    # Look for video title links - these contain the most complete info
    video_links = soup.find_all('a', id='video-title-link')
    
    print(f"🔍 Found {len(video_links)} video title links")
    
    for link in video_links:
        # Extract video ID from href
        href = link.get('href', '')
        video_id_match = re.search(r'v=([a-zA-Z0-9_-]{11})', href)
        
        if video_id_match:
            video_id = video_id_match.group(1)
            
            if video_id not in video_ids_seen:
                video_ids_seen.add(video_id)
                
                # Extract title from aria-label or title attribute
                title = link.get('aria-label', '') or link.get('title', '')
                
                # Clean up title - remove duration info at the end
                title_clean = re.sub(r'\s+\d+\s+(hours?|minutes?|seconds?).*$', '', title)
                
                # Extract duration from aria-label if present
                duration_match = re.search(r'(\d+\s+hours?,?\s*)?(\d+\s+minutes?,?\s*)?(\d+\s+seconds?)?$', title)
                duration = duration_match.group(0) if duration_match else ''
                
                # Try to find metadata in parent elements
                parent = link.parent
                metadata_text = ""
                
                if parent:
                    # Look for view counts and dates
                    parent_text = parent.get_text(separator=' ', strip=True)
                    
                    # Extract view count
                    views_match = re.search(r'([\d.,]+[KMB]?)\s+views?', parent_text)
                    views = views_match.group(1) if views_match else ''
                    
                    # Extract date info
                    date_match = re.search(r'Streamed\s+(.+?ago|live)', parent_text)
                    if not date_match:
                        date_match = re.search(r'(\d+\s+(years?|months?|weeks?|days?|hours?)\s+ago)', parent_text)
                    date_info = date_match.group(1) if date_match else ''
                    
                    metadata_text = f"{views} views • {date_info}" if views or date_info else ""
                
                video_data = {
                    'id': video_id,
                    'url': f'https://www.youtube.com/watch?v={video_id}',
                    'title': title_clean.strip(),
                    'duration': duration.strip(),
                    'metadata': metadata_text.strip(),
                    'views': views,
                    'date_info': date_info
                }
                
                videos.append(video_data)
    
    # Method 2: Also check for any ytInitialData in script tags
    script_video_count = 0
    for script in soup.find_all('script'):
        if script.string and 'ytInitialData' in script.string:
            # Extract video IDs from the JSON data
            video_ids_in_script = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', script.string)
            
            for vid in video_ids_in_script:
                if vid not in video_ids_seen:
                    video_ids_seen.add(vid)
                    script_video_count += 1
                    
                    # For these, we only have the ID
                    videos.append({
                        'id': vid,
                        'url': f'https://www.youtube.com/watch?v={vid}',
                        'title': '',  # Will need to be filled from other sources
                        'duration': '',
                        'metadata': '',
                        'views': '',
                        'date_info': ''
                    })
    
    print(f"📊 Extracted {len(videos)} videos ({len(videos) - script_video_count} with titles, {script_video_count} IDs only)")
    
    return videos

def categorize_videos(videos):
    """
    Categorize videos by type based on title patterns
    """
    
    categories = {
        'hearings': [],
        'markups': [],
        'opening_statements': [],
        'press_conferences': [],
        'field_hearings': [],
        'member_days': [],
        'roundtables': [],
        'other': []
    }
    
    for video in videos:
        title_lower = video['title'].lower()
        
        if 'markup' in title_lower:
            categories['markups'].append(video)
        elif 'opening statement' in title_lower:
            categories['opening_statements'].append(video)
        elif 'press conference' in title_lower or 'host press' in title_lower:
            categories['press_conferences'].append(video)
        elif 'field hearing' in title_lower:
            categories['field_hearings'].append(video)
        elif 'member day' in title_lower:
            categories['member_days'].append(video)
        elif 'roundtable' in title_lower:
            categories['roundtables'].append(video)
        elif 'hearing' in title_lower or 'oversight' in title_lower:
            categories['hearings'].append(video)
        else:
            categories['other'].append(video)
    
    return categories

def main():
    # Get committee name and HTML file from command line or use defaults
    if len(sys.argv) >= 3:
        committee_name = sys.argv[1]
        html_file = sys.argv[2]
    else:
        # Default to Energy & Commerce for backward compatibility
        committee_name = "energy_commerce"
        html_file = "../House Committee on Energy and Commerce - YouTube.html"
    
    print(f"🎬 {committee_name.replace('_', ' ').title()} YouTube Channel Complete Dataset Extraction")
    print("=" * 70)
    
    # Check if HTML file exists
    if not os.path.exists(html_file):
        print(f"❌ Error: HTML file not found: {html_file}")
        print("\nUsage: python parse_ec_html_complete.py <committee_name> <html_file>")
        print("Example: python parse_ec_html_complete.py judiciary ../judiciary_youtube.html")
        return
    
    # Extract all videos
    videos = extract_video_data_from_html(html_file)
    
    # Filter to only videos with titles
    videos_with_titles = [v for v in videos if v['title']]
    
    print(f"\n📹 Videos with titles: {len(videos_with_titles)}")
    print(f"🆔 Videos with IDs only: {len(videos) - len(videos_with_titles)}")
    
    # Categorize videos
    categories = categorize_videos(videos_with_titles)
    
    print("\n📊 Video Categories:")
    for category, vids in categories.items():
        if vids:
            print(f"  {category.replace('_', ' ').title()}: {len(vids)} videos")
    
    # Search for specific patterns
    print("\n🔍 Searching for key hearings:")
    
    # FTC hearings
    ftc_videos = [v for v in videos_with_titles if 'ftc' in v['title'].lower() or 'federal trade commission' in v['title'].lower()]
    print(f"\n📌 FTC-related: {len(ftc_videos)} videos")
    for v in ftc_videos[:5]:
        print(f"  - {v['title'][:80]}...")
        print(f"    ID: {v['id']}")
    
    # Privacy hearings
    privacy_videos = [v for v in videos_with_titles if 'privacy' in v['title'].lower()]
    print(f"\n🔒 Privacy-related: {len(privacy_videos)} videos")
    for v in privacy_videos[:5]:
        print(f"  - {v['title'][:80]}...")
        print(f"    ID: {v['id']}")
    
    # Save complete dataset
    output = {
        'metadata': {
            'source': 'saved_youtube_html',
            'committee': committee_name.replace('_', ' ').title(),
            'extraction_date': datetime.now().isoformat(),
            'total_videos': len(videos),
            'videos_with_titles': len(videos_with_titles)
        },
        'categories': {cat: len(vids) for cat, vids in categories.items()},
        'videos': videos_with_titles,
        'all_video_ids': [v['id'] for v in videos]
    }
    
    # Save main dataset with committee-specific name
    complete_filename = f'../data/{committee_name}_youtube_complete_dataset.json'
    with open(complete_filename, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n💾 Complete dataset saved to: {complete_filename}")
    
    # Also save a simplified version for matching
    simplified = []
    for v in videos_with_titles:
        # Parse the relative date
        approximate_date = parse_relative_date(v.get('date_info', ''))
        
        simplified.append({
            'video_id': v['id'],
            'title': v['title'],
            'url': v['url'],
            'date_info': v.get('date_info', ''),
            'approximate_date': approximate_date,
            'views': v.get('views', '')
        })
    
    simplified_filename = f'../data/{committee_name}_youtube_videos_for_matching.json'
    with open(simplified_filename, 'w') as f:
        json.dump(simplified, f, indent=2)
    
    print(f"💾 Simplified dataset saved to: {simplified_filename}")
    
    # Show sample of data
    print("\n📋 Sample videos:")
    for v in videos_with_titles[:5]:
        print(f"\nTitle: {v['title']}")
        print(f"ID: {v['id']}")
        print(f"URL: {v['url']}")
        if v.get('metadata'):
            print(f"Metadata: {v['metadata']}")

if __name__ == "__main__":
    main()
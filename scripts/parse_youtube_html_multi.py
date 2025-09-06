#!/usr/bin/env python3
"""
Parse saved YouTube channel HTML for all active committees in the YAML config
"""

from bs4 import BeautifulSoup
import json
import re
from datetime import datetime, timedelta
import sys
import os
import yaml

def load_committee_config():
    """Load committee configuration from YAML file"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'committees_config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

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
    
    # Calculate approximate date
    if unit == 'hour':
        delta = timedelta(hours=amount)
    elif unit == 'day':
        delta = timedelta(days=amount)
    elif unit == 'week':
        delta = timedelta(weeks=amount)
    elif unit == 'month':
        delta = timedelta(days=amount * 30)  # Approximate
    elif unit == 'year':
        delta = timedelta(days=amount * 365)  # Approximate
    else:
        return None
    
    approx_date = today - delta
    return approx_date.strftime('%Y-%m-%d')

def extract_video_data_from_html(file_path):
    """Extract video data from saved YouTube HTML"""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    videos = []
    
    # Find all video renderer elements
    # YouTube uses different element names that might vary
    video_elements = soup.find_all(['ytd-grid-video-renderer', 'ytd-rich-item-renderer'])
    
    for elem in video_elements:
        video_data = {}
        
        # Try to extract video ID from various possible locations
        video_id = None
        
        # Method 1: From thumbnail link
        thumbnail_link = elem.find('a', {'id': 'thumbnail'})
        if thumbnail_link and 'href' in thumbnail_link.attrs:
            href = thumbnail_link['href']
            if '/watch?v=' in href:
                video_id = href.split('/watch?v=')[1].split('&')[0]
        
        # Method 2: From video-id attribute
        if not video_id:
            video_id_elem = elem.find(attrs={'video-id': True})
            if video_id_elem:
                video_id = video_id_elem.get('video-id')
        
        # Method 3: From href in any link
        if not video_id:
            for link in elem.find_all('a', href=True):
                href = link['href']
                if '/watch?v=' in href:
                    video_id = href.split('/watch?v=')[1].split('&')[0]
                    break
        
        if video_id:
            video_data['id'] = video_id
            video_data['url'] = f"https://www.youtube.com/watch?v={video_id}"
            
            # Extract title
            title_elem = elem.find('h3')
            if not title_elem:
                title_elem = elem.find(id='video-title')
            if not title_elem:
                title_elem = elem.find('a', {'id': 'video-title-link'})
            
            if title_elem:
                # Get text, handling both direct text and aria-label
                title = title_elem.get('title') or title_elem.get('aria-label') or title_elem.get_text(strip=True)
                video_data['title'] = title
            else:
                video_data['title'] = ''
            
            # Extract metadata (views, date)
            metadata_line = elem.find('div', {'id': 'metadata-line'})
            if metadata_line:
                spans = metadata_line.find_all('span')
                metadata_parts = [span.get_text(strip=True) for span in spans]
                video_data['metadata'] = ' • '.join(metadata_parts)
                
                # Try to extract date and views
                for part in metadata_parts:
                    if 'ago' in part.lower() or 'streamed' in part.lower():
                        video_data['date_info'] = part
                    elif 'view' in part.lower():
                        video_data['views'] = part
            
            # Try alternative metadata extraction
            if 'date_info' not in video_data:
                for span in elem.find_all('span'):
                    text = span.get_text(strip=True).lower()
                    if ('ago' in text or 'streamed' in text) and 'date_info' not in video_data:
                        video_data['date_info'] = span.get_text(strip=True)
            
            videos.append(video_data)
    
    # Also try to find videos in script tags (sometimes YouTube loads data this way)
    script_videos = []
    for script in soup.find_all('script'):
        if script.string and 'var ytInitialData' in script.string:
            # Extract video IDs using regex
            video_id_matches = re.findall(r'"videoId":"([^"]+)"', script.string)
            for vid_id in video_id_matches:
                if vid_id and len(vid_id) == 11:  # YouTube video IDs are 11 characters
                    if not any(v['id'] == vid_id for v in videos):
                        script_videos.append({
                            'id': vid_id,
                            'url': f"https://www.youtube.com/watch?v={vid_id}",
                            'title': '',  # We can't easily extract titles from script
                            'from_script': True
                        })
    
    videos.extend(script_videos)
    
    # Remove duplicates based on video ID
    seen_ids = set()
    unique_videos = []
    for video in videos:
        if video['id'] not in seen_ids:
            seen_ids.add(video['id'])
            unique_videos.append(video)
    
    return unique_videos

def categorize_videos(videos):
    """Categorize videos based on their titles"""
    
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
        title_lower = video['title'].lower() if video.get('title') else ''
        
        if 'opening statement' in title_lower:
            categories['opening_statements'].append(video)
        elif 'field hearing' in title_lower:
            categories['field_hearings'].append(video)
        elif 'press conference' in title_lower or 'news conference' in title_lower:
            categories['press_conferences'].append(video)
        elif 'member day' in title_lower:
            categories['member_days'].append(video)
        elif 'roundtable' in title_lower:
            categories['roundtables'].append(video)
        elif 'markup' in title_lower:
            categories['markups'].append(video)
        elif 'hearing' in title_lower or 'oversight' in title_lower or 'examining' in title_lower or 'review' in title_lower:
            categories['hearings'].append(video)
        else:
            categories['other'].append(video)
    
    return categories

def process_committee(committee_id, committee_info, root_dir):
    """Process YouTube HTML for a single committee"""
    
    # Check if we already have the output files
    complete_filename = os.path.join(root_dir, "data", f'{committee_id}_youtube_complete_dataset.json')
    simplified_filename = os.path.join(root_dir, "data", f'{committee_id}_youtube_videos_for_matching.json')
    
    if os.path.exists(complete_filename) and os.path.exists(simplified_filename):
        print(f"  ✅ YouTube data already exists for {committee_info['short_name']} - skipping HTML parsing")
        print(f"     To force re-parsing, delete: {complete_filename}")
        
        # Load the complete dataset to get proper counts and categories
        with open(complete_filename, 'r') as f:
            complete_data = json.load(f)
        
        # Return the same structure as if we had processed it
        return {
            'committee_id': committee_id,
            'committee_name': committee_info['short_name'],
            'videos_count': complete_data['metadata']['videos_with_titles'],
            'categories': complete_data.get('categories', {})
        }
    
    html_file = os.path.join(root_dir, committee_info['youtube_html_filename'])
    
    # Check if HTML file exists
    if not os.path.exists(html_file):
        print(f"  ❌ HTML file not found: {html_file}")
        print(f"     Please download from YouTube and save as: {committee_info['youtube_html_filename']}")
        return None
    
    print(f"  ✅ Processing: {committee_info['youtube_html_filename']}")
    
    # Extract all videos
    videos = extract_video_data_from_html(html_file)
    
    # Filter to only videos with titles
    videos_with_titles = [v for v in videos if v['title']]
    
    print(f"     📹 Videos with titles: {len(videos_with_titles)}")
    print(f"     🆔 Videos with IDs only: {len(videos) - len(videos_with_titles)}")
    
    # Categorize videos
    categories = categorize_videos(videos_with_titles)
    
    # Prepare output data
    output = {
        'metadata': {
            'source': 'saved_youtube_html',
            'committee_id': committee_id,
            'committee_name': committee_info['full_name'],
            'committee_short': committee_info['short_name'],
            'extraction_date': datetime.now().isoformat(),
            'total_videos': len(videos),
            'videos_with_titles': len(videos_with_titles)
        },
        'categories': {cat: len(vids) for cat, vids in categories.items()},
        'videos': videos_with_titles,
        'all_video_ids': [v['id'] for v in videos]
    }
    
    # Save main dataset with committee-specific name
    complete_filename = os.path.join(root_dir, "data", f'{committee_id}_youtube_complete_dataset.json')
    with open(complete_filename, 'w') as f:
        json.dump(output, f, indent=2)
    
    # Also save a simplified version for matching
    simplified = []
    for v in videos_with_titles:
        # Parse the relative date
        approximate_date = parse_relative_date(v.get('date_info', ''))
        
        simplified.append({
            'committee_id': committee_id,
            'committee_name': committee_info['short_name'],
            'video_id': v['id'],
            'title': v['title'],
            'url': v['url'],
            'date_info': v.get('date_info', ''),
            'approximate_date': approximate_date,
            'views': v.get('views', '')
        })
    
    simplified_filename = os.path.join(root_dir, "data", f'{committee_id}_youtube_videos_for_matching.json')
    with open(simplified_filename, 'w') as f:
        json.dump(simplified, f, indent=2)
    
    return {
        'committee_id': committee_id,
        'committee_name': committee_info['short_name'],
        'videos_count': len(videos_with_titles),
        'categories': categories
    }

def main():
    # Check if PyYAML is installed
    try:
        import yaml
    except ImportError:
        print("ERROR: PyYAML is required. Please run: pip install pyyaml")
        sys.exit(1)
    
    # Load committee configuration
    config = load_committee_config()
    active_committees = config['active_committees']
    committees_info = config['committees']
    
    print("🎬 YouTube Channel Dataset Extraction")
    print("=" * 70)
    print(f"Active committees: {', '.join(active_committees)}")
    print()
    
    # Get the root directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    
    # Create data directory if it doesn't exist
    os.makedirs(os.path.join(root_dir, "data"), exist_ok=True)
    
    # Process each active committee
    all_results = []
    all_videos = []
    
    for committee_id in active_committees:
        if committee_id not in committees_info:
            print(f"❌ Committee '{committee_id}' not found in configuration")
            continue
        
        committee_info = committees_info[committee_id]
        print(f"\n📂 Processing: {committee_info['full_name']}")
        
        result = process_committee(committee_id, committee_info, root_dir)
        if result:
            all_results.append(result)
            
            # Load the videos for combined output
            simplified_file = os.path.join(root_dir, "data", f'{committee_id}_youtube_videos_for_matching.json')
            with open(simplified_file, 'r') as f:
                videos = json.load(f)
                all_videos.extend(videos)
    
    # If multiple committees, create a combined dataset
    if len(active_committees) > 1 and all_videos:
        combined_filename = os.path.join(root_dir, "data", 'all_committees_youtube_videos.json')
        with open(combined_filename, 'w') as f:
            json.dump(all_videos, f, indent=2)
        print(f"\n💾 Combined dataset saved to: {combined_filename}")
    
    # Summary
    print("\n📊 Summary:")
    total_videos = 0
    for result in all_results:
        print(f"\n  {result['committee_name']}:")
        print(f"    Total videos: {result['videos_count']}")
        total_videos += result['videos_count']
        
        # Show categories
        for cat_name, value in result['categories'].items():
            if value:
                # Handle both list (from fresh parsing) and int (from loaded data)
                count = len(value) if isinstance(value, list) else value
                print(f"    {cat_name.replace('_', ' ').title()}: {count}")
    
    if len(all_results) > 1:
        print(f"\n  Total videos across all committees: {total_videos}")

if __name__ == "__main__":
    main()
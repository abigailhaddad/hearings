#!/usr/bin/env python3
"""
Parse YouTube channel HTML that was manually saved after scrolling to load all videos
"""

from bs4 import BeautifulSoup
import json
import re
from datetime import datetime

def parse_youtube_html(html_file):
    """Parse saved YouTube HTML file to extract video information"""
    
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    videos = []
    video_ids = set()
    
    # Find all video links - YouTube uses different selectors
    # Try multiple approaches
    
    # Method 1: Look for watch links
    for link in soup.find_all('a', href=True):
        href = link['href']
        if '/watch?v=' in href:
            video_id_match = re.search(r'v=([a-zA-Z0-9_-]{11})', href)
            if video_id_match:
                video_id = video_id_match.group(1)
                
                if video_id not in video_ids:
                    video_ids.add(video_id)
                    
                    # Try to get title
                    title = link.get('title', '')
                    if not title:
                        # Try to find title in aria-label
                        title = link.get('aria-label', '')
                    
                    # Try to get metadata from nearby elements
                    parent = link.parent
                    metadata = ""
                    if parent:
                        # Look for view count, date, etc.
                        for elem in parent.find_all(['span', 'div']):
                            text = elem.get_text(strip=True)
                            if any(keyword in text.lower() for keyword in ['views', 'streamed', 'ago', 'year', 'month']):
                                metadata += text + " "
                    
                    videos.append({
                        'id': video_id,
                        'url': f'https://www.youtube.com/watch?v={video_id}',
                        'title': title.strip(),
                        'metadata': metadata.strip()
                    })
    
    # Method 2: Look for video renderer data in script tags
    for script in soup.find_all('script'):
        if script.string and 'var ytInitialData' in script.string:
            # Extract JSON data
            match = re.search(r'var ytInitialData = ({.*?});', script.string, re.DOTALL)
            if match:
                try:
                    yt_data = json.loads(match.group(1))
                    # Parse the complex YouTube data structure
                    # This would require navigating the nested JSON
                    print("Found ytInitialData in page")
                except:
                    pass
    
    return videos

def search_for_hearing(videos, search_terms):
    """Search for specific hearings in the video list"""
    
    results = []
    
    for video in videos:
        title_lower = video['title'].lower()
        
        # Check if all search terms are in the title
        if all(term.lower() in title_lower for term in search_terms):
            results.append(video)
    
    return results

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python parse_saved_html.py <saved_html_file>")
        print("\nTo save HTML from YouTube:")
        print("1. Go to https://www.youtube.com/@energyandcommerce/streams")
        print("2. Scroll down to load all videos")
        print("3. Save the page (Ctrl+S or Cmd+S)")
        print("4. Run this script with the saved HTML file")
        return
    
    html_file = sys.argv[1]
    print(f"🔍 Parsing YouTube HTML from: {html_file}")
    
    videos = parse_youtube_html(html_file)
    
    print(f"\n✅ Found {len(videos)} unique videos")
    
    # Save all videos
    output = {
        'source': 'saved_html',
        'timestamp': datetime.now().isoformat(),
        'total_videos': len(videos),
        'videos': videos
    }
    
    with open('parsed_youtube_videos.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"💾 Saved to: parsed_youtube_videos.json")
    
    # Search for specific hearings
    print("\n🔍 Searching for FTC and privacy hearings...")
    
    # FTC hearings
    ftc_videos = search_for_hearing(videos, ['ftc'])
    if not ftc_videos:
        ftc_videos = search_for_hearing(videos, ['federal trade commission'])
    
    print(f"\n📌 Found {len(ftc_videos)} FTC-related videos:")
    for v in ftc_videos[:10]:
        print(f"  - {v['title'][:80]}...")
        print(f"    {v['url']}")
    
    # Privacy hearings
    privacy_videos = search_for_hearing(videos, ['privacy'])
    
    print(f"\n🔒 Found {len(privacy_videos)} privacy-related videos:")
    for v in privacy_videos[:10]:
        print(f"  - {v['title'][:80]}...")
        print(f"    {v['url']}")
    
    # Specific hearing
    target_terms = ['oversight', 'federal trade commission', 'privacy', 'data']
    specific_videos = search_for_hearing(videos, target_terms)
    
    if specific_videos:
        print(f"\n✅ Found potential matches for FTC oversight hearing:")
        for v in specific_videos:
            print(f"  - {v['title']}")
            print(f"    {v['url']}")
            print(f"    {v.get('metadata', '')}")

if __name__ == "__main__":
    main()
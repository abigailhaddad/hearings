#!/usr/bin/env python3
"""
Extract date information from YouTube HTML
"""

from bs4 import BeautifulSoup
import json
import re

def extract_youtube_dates():
    """Extract dates from the saved YouTube HTML"""
    
    print("📅 Extracting dates from YouTube HTML...")
    
    # Read the HTML file
    with open("House Committee on Energy and Commerce - YouTube.html", 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Find all script tags that might contain video data
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Look for ytInitialData script tag
    dates_found = []
    
    for script in soup.find_all('script'):
        if script.string and 'ytInitialData' in script.string:
            # Extract video IDs and any associated date information
            content = script.string
            
            # Find patterns like "3 days ago", "2 weeks ago", etc.
            date_patterns = re.findall(r'(\d+\s+(?:hours?|days?|weeks?|months?|years?)\s+ago)', content, re.IGNORECASE)
            
            # Also look for "Streamed" patterns
            stream_patterns = re.findall(r'Streamed\s+(\d+\s+(?:hours?|days?|weeks?|months?|years?)\s+ago)', content, re.IGNORECASE)
            
            # Look for structured patterns with video IDs
            # This pattern looks for videoId followed by date information
            video_date_patterns = re.findall(r'"videoId":"([^"]+)".*?"simpleText":"(\d+\s+(?:hours?|days?|weeks?|months?|years?)\s+ago)"', content)
            
            print(f"\n🔍 Found {len(date_patterns)} date patterns")
            print(f"🔍 Found {len(stream_patterns)} stream date patterns")
            print(f"🔍 Found {len(video_date_patterns)} video-date pairs")
            
            # Extract the full video data structure if possible
            try:
                # Look for video renderer objects
                video_renderers = re.findall(r'"videoRenderer":\s*({[^}]+(?:"thumbnail"[^}]+}[^}]+)+})', content)
                print(f"\n📹 Found {len(video_renderers)} video renderer objects")
                
                # Try to extract specific fields from each
                for i, renderer in enumerate(video_renderers[:5]):  # First 5 for testing
                    video_id_match = re.search(r'"videoId":"([^"]+)"', renderer)
                    title_match = re.search(r'"title":{[^}]*"text":"([^"]+)"', renderer)
                    
                    if video_id_match:
                        print(f"\n  Video {i+1}:")
                        print(f"    ID: {video_id_match.group(1)}")
                        if title_match:
                            print(f"    Title: {title_match.group(1)[:50]}...")
                
            except Exception as e:
                print(f"⚠️  Error parsing video renderers: {e}")
            
            # Save raw patterns for analysis
            with open('youtube_date_patterns.json', 'w') as f:
                json.dump({
                    'date_patterns': date_patterns[:50],  # First 50
                    'stream_patterns': stream_patterns[:50],
                    'video_date_pairs': video_date_patterns[:50]
                }, f, indent=2)
            
            print(f"\n💾 Saved date patterns to youtube_date_patterns.json")
            
            # Try a different approach - look for aria-label patterns
            aria_patterns = re.findall(r'aria-label="([^"]*(?:\d+\s+(?:hours?|days?|weeks?|months?|years?)\s+ago)[^"]*)"', content)
            print(f"\n🏷️  Found {len(aria_patterns)} aria-label patterns")
            for pattern in aria_patterns[:5]:
                print(f"  - {pattern}")
            
            break
    
    # Also check for metadata in the HTML directly
    print("\n🔍 Checking HTML elements for date information...")
    
    # Look for time elements
    time_elements = soup.find_all('time')
    print(f"Found {len(time_elements)} time elements")
    
    # Look for elements with date-related classes
    date_divs = soup.find_all('div', class_=re.compile(r'date|time|published|uploaded', re.I))
    print(f"Found {len(date_divs)} divs with date-related classes")
    
    # Look for metadata spans
    metadata_spans = soup.find_all('span', string=re.compile(r'\d+\s+(hours?|days?|weeks?|months?|years?)\s+ago'))
    print(f"Found {len(metadata_spans)} spans with date text")

if __name__ == "__main__":
    extract_youtube_dates()
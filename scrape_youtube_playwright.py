#!/usr/bin/env python3
"""
Scrape YouTube channel using Playwright to handle infinite scroll
"""

import json
import time
from playwright.sync_api import sync_playwright

def scrape_youtube_channel_full(channel_url, max_scrolls=2000):
    """
    Scrape YouTube channel with scrolling to load all videos
    """
    
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=False)  # Visible browser for debugging
        page = browser.new_page()
        
        print(f"Loading: {channel_url}")
        page.goto(channel_url, wait_until='networkidle')
        
        # Wait for initial content to load
        page.wait_for_timeout(5000)
        
        # Accept cookies if needed
        try:
            cookie_button = page.query_selector('button[aria-label*="Accept"]')
            if cookie_button:
                cookie_button.click()
                page.wait_for_timeout(1000)
        except:
            pass
        
        video_ids = set()
        previous_count = 0
        scroll_count = 0
        
        print("Scrolling to load more videos...")
        
        no_new_videos_count = 0
        seen_reset = False
        first_video_id = None
        
        while scroll_count < max_scrolls:
            # Extract video IDs from current page
            video_links = page.query_selector_all('a#video-title-link')
            
            current_page_ids = []
            for i, link in enumerate(video_links):
                href = link.get_attribute('href')
                if href and '/watch?v=' in href:
                    video_id = href.split('v=')[1].split('&')[0]
                    current_page_ids.append(video_id)
                    
                    # Store the first video ID we see
                    if first_video_id is None and i == 0:
                        first_video_id = video_id
                    
                    # Check if we've cycled back to the beginning
                    if video_id == first_video_id and len(video_ids) > 100:
                        if not seen_reset:
                            print(f"\n🔄 Detected content reset after {len(video_ids)} videos!")
                            seen_reset = True
                    
                    video_ids.add(video_id)
            
            current_count = len(video_ids)
            print(f"Scroll {scroll_count + 1}: Found {current_count} videos total")
            
            # Check if we should stop
            if seen_reset:
                print("Stopping due to content reset - we've captured all available videos")
                break
                
            # If no new videos found in last scroll
            if current_count == previous_count:
                no_new_videos_count += 1
                print(f"No new videos (attempt {no_new_videos_count}/20) - Keep scrolling...")
                
                # Try 20 times before giving up (YouTube loads in batches)
                if no_new_videos_count >= 20:
                    print("No new videos after 20 attempts, reached the end")
                    break
            else:
                no_new_videos_count = 0  # Reset counter
            
            previous_count = current_count
            
            # Scroll down
            page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            
            # Force scroll multiple times
            for _ in range(5):
                page.evaluate('window.scrollBy(0, 2000)')
                page.wait_for_timeout(300)
            
            # Wait longer for content to load
            page.wait_for_timeout(8000)
            
            # Extra wait if we haven't found new videos
            if no_new_videos_count > 5:
                print("   Waiting extra time for more videos to load...")
                page.wait_for_timeout(5000)
            
            # Check for "Show more" button
            try:
                show_more = page.query_selector('button[aria-label*="Show more"]')
                if show_more and show_more.is_visible():
                    show_more.click()
                    page.wait_for_timeout(2000)
            except:
                pass
            
            scroll_count += 1
        
        # Extract video metadata
        print("\nExtracting video metadata...")
        videos = []
        
        video_elements = page.query_selector_all('#dismissible')
        
        for element in video_elements:
            try:
                # Get video ID
                link = element.query_selector('a#video-title-link')
                if not link:
                    continue
                    
                href = link.get_attribute('href')
                if not href or '/watch?v=' not in href:
                    continue
                
                video_id = href.split('v=')[1].split('&')[0]
                
                # Get title
                title = link.get_attribute('title') or link.inner_text()
                
                # Get metadata
                metadata_element = element.query_selector('#metadata-line')
                metadata_text = metadata_element.inner_text() if metadata_element else ''
                
                # Get thumbnail
                thumbnail_element = element.query_selector('img')
                thumbnail_url = thumbnail_element.get_attribute('src') if thumbnail_element else ''
                
                videos.append({
                    'id': video_id,
                    'title': title.strip(),
                    'url': f'https://www.youtube.com/watch?v={video_id}',
                    'metadata': metadata_text,
                    'thumbnail': thumbnail_url
                })
                
            except Exception as e:
                print(f"Error extracting video data: {e}")
                continue
        
        browser.close()
        
        return videos

def main():
    print("🎭 YouTube Channel Scraper with Playwright")
    print("=" * 60)
    
    # Focus on streams/live videos only
    urls_to_try = [
        "https://www.youtube.com/@energyandcommerce/streams"
    ]
    
    # First check if playwright is installed
    try:
        import playwright
    except ImportError:
        print("\n❌ Playwright not installed!")
        print("Install it with: pip install playwright")
        print("Then run: playwright install chromium")
        return
    
    all_videos = []
    
    for channel_url in urls_to_try:
        print(f"\nScraping all videos from: {channel_url}")
        print("This may take a few minutes...\n")
        
        videos = scrape_youtube_channel_full(channel_url, max_scrolls=50)
        all_videos.extend(videos)
    
    print(f"\n✅ Found {len(all_videos)} videos total")
    
    # Save results
    output = {
        'channel': {
            'url': channel_url,
            'name': 'House Energy and Commerce Committee'
        },
        'scrape_time': time.strftime('%Y-%m-%d %H:%M:%S'),
        'total_videos': len(all_videos),
        'videos': all_videos
    }
    
    with open('youtube_channel_complete.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n💾 Saved to: youtube_channel_complete.json")
    
    # Search for FTC and privacy hearings
    print("\n🔍 Searching for FTC and privacy-related hearings...")
    
    ftc_videos = [v for v in all_videos if 'ftc' in v['title'].lower() or 'federal trade commission' in v['title'].lower()]
    privacy_videos = [v for v in all_videos if 'privacy' in v['title'].lower() or 'data' in v['title'].lower()]
    
    if ftc_videos:
        print(f"\n📌 Found {len(ftc_videos)} FTC-related videos:")
        for v in ftc_videos:
            print(f"  - {v['title']}")
            print(f"    URL: {v['url']}")
    
    if privacy_videos:
        print(f"\n🔒 Found {len(privacy_videos)} privacy/data-related videos:")
        for v in privacy_videos[:10]:  # Show first 10
            print(f"  - {v['title']}")
            print(f"    URL: {v['url']}")
        if len(privacy_videos) > 10:
            print(f"  ... and {len(privacy_videos) - 10} more")
    
    # Specific search
    target_hearing = "Oversight of the Federal Trade Commission: Strengthening Protections for Americans' Privacy and Data"
    specific_match = [v for v in all_videos if target_hearing.lower() in v['title'].lower()]
    
    if specific_match:
        print(f"\n✅ FOUND THE SPECIFIC HEARING:")
        for v in specific_match:
            print(f"  - {v['title']}")
            print(f"    URL: {v['url']}")
    else:
        print(f"\n❌ Specific hearing not found: '{target_hearing}'")

if __name__ == "__main__":
    main()
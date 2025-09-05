import os
import requests
import json
import csv
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')

def search_youtube_channels(search_query, max_results=10):
    """Search YouTube for channels"""
    if not YOUTUBE_API_KEY:
        print("No YouTube API key found!")
        return []
    
    results = []
    
    try:
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            'part': 'snippet',
            'q': search_query,
            'type': 'channel',
            'maxResults': max_results,
            'key': YOUTUBE_API_KEY
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            
            for item in data.get('items', []):
                channel_id = item['snippet']['channelId']
                title = item['snippet']['title']
                
                results.append({
                    'channel_id': channel_id,
                    'channel_title': title,
                    'channel_url': f"https://www.youtube.com/channel/{channel_id}",
                    'description': item['snippet']['description']
                })
        else:
            print(f"Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"Error searching for {search_query}: {e}")
    
    return results

def create_simple_html(house_channels, senate_channels):
    """Create a simple HTML table with the channels"""
    html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Congressional Committee YouTube Channels</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        
        .container {
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        h1, h2 {
            color: #333;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 30px;
        }
        
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        
        th {
            background: #f8f9fa;
            font-weight: 600;
        }
        
        tr:hover {
            background: #f8f9fa;
        }
        
        a {
            color: #007bff;
            text-decoration: none;
        }
        
        a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏛️ Congressional Committee YouTube Channels</h1>
        
        <h2>U.S. House Committees</h2>
        <table>
            <thead>
                <tr>
                    <th>Channel Name</th>
                    <th>Link</th>
                </tr>
            </thead>
            <tbody>
'''
    
    for channel in house_channels:
        html_content += f'''                <tr>
                    <td>{channel['channel_title']}</td>
                    <td><a href="{channel['channel_url']}" target="_blank">View Channel</a></td>
                </tr>
'''
    
    html_content += '''            </tbody>
        </table>
        
        <h2>U.S. Senate Committees</h2>
        <table>
            <thead>
                <tr>
                    <th>Channel Name</th>
                    <th>Link</th>
                </tr>
            </thead>
            <tbody>
'''
    
    for channel in senate_channels:
        html_content += f'''                <tr>
                    <td>{channel['channel_title']}</td>
                    <td><a href="{channel['channel_url']}" target="_blank">View Channel</a></td>
                </tr>
'''
    
    html_content += '''            </tbody>
        </table>
    </div>
</body>
</html>'''
    
    with open('committee_channels_simple.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print("✅ Created committee_channels_simple.html")

def main():
    print("🔍 Searching for Congressional Committee YouTube Channels")
    print("=" * 60)
    
    # Search for House committees
    print("\n📋 Searching for U.S. House Committee channels...")
    house_channels = search_youtube_channels("U.S. House Committee", 10)
    print(f"Found {len(house_channels)} House committee channels")
    
    # Search for Senate committees  
    print("\n📋 Searching for U.S. Senate Committee channels...")
    senate_channels = search_youtube_channels("U.S. Senate Committee", 10)
    print(f"Found {len(senate_channels)} Senate committee channels")
    
    # Save as CSV
    all_channels = []
    for channel in house_channels:
        all_channels.append({**channel, 'chamber': 'House'})
    for channel in senate_channels:
        all_channels.append({**channel, 'chamber': 'Senate'})
    
    with open('committee_channels_simple.csv', 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['chamber', 'channel_title', 'channel_url']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for channel in all_channels:
            writer.writerow({
                'chamber': channel['chamber'],
                'channel_title': channel['channel_title'],
                'channel_url': channel['channel_url']
            })
    
    print("\n✅ Saved results to committee_channels_simple.csv")
    
    # Create HTML
    create_simple_html(house_channels, senate_channels)
    
    # Also save as JSON
    with open('committee_channels_simple.json', 'w') as f:
        json.dump({
            'metadata': {
                'generated': datetime.now().isoformat(),
                'search_queries': ['U.S. House Committee', 'U.S. Senate Committee']
            },
            'house_channels': house_channels,
            'senate_channels': senate_channels
        }, f, indent=2)
    
    print("✅ Saved results to committee_channels_simple.json")

if __name__ == "__main__":
    main()
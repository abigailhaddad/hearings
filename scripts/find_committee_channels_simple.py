import os
import requests
import json
import csv
from dotenv import load_dotenv
from datetime import datetime
import time

load_dotenv()
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')
CONGRESS_API_KEY = os.environ.get('CONGRESS_API_KEY')

def get_all_committees():
    """Get list of all House and Senate committees from Congress API"""
    committees = []
    
    for chamber in ['house', 'senate']:
        url = f"https://api.congress.gov/v3/committee/{chamber}?api_key={CONGRESS_API_KEY}&limit=100"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            for comm in data.get('committees', []):
                # Skip subcommittees for now
                if 'subcommittee' not in comm.get('name', '').lower():
                    committees.append({
                        'name': comm.get('name'),
                        'chamber': chamber.title(),
                        'systemCode': comm.get('systemCode'),
                        'committeeCode': comm.get('committeeCode')
                    })
    
    return committees

def search_youtube_channels(committee_name, chamber):
    """Search YouTube for committee channels"""
    if not YOUTUBE_API_KEY:
        return []
    
    results = []
    
    # Simple search - just the committee
    search_terms = [
        f"{chamber} {committee_name}",
        f"{committee_name}"
    ]
    
    seen_channels = set()
    
    for term in search_terms:
        try:
            url = "https://www.googleapis.com/youtube/v3/search"
            params = {
                'part': 'snippet',
                'q': term,
                'type': 'channel',
                'maxResults': 10,  # Get more to have good options
                'key': YOUTUBE_API_KEY
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                for item in data.get('items', []):
                    channel_id = item['snippet']['channelId']
                    
                    if channel_id not in seen_channels:
                        seen_channels.add(channel_id)
                        
                        # Check if it looks like an official committee channel
                        title = item['snippet']['title']
                        desc = item['snippet']['description'].lower()
                        
                        # Score based on how likely it is to be official
                        score = 0
                        title_lower = title.lower()
                        
                        if chamber.lower() in title_lower:
                            score += 2
                        if 'committee' in title_lower:
                            score += 2
                        if any(word in committee_name.lower() for word in title_lower.split()):
                            score += 1
                        if 'official' in desc:
                            score += 2
                        if 'congress' in desc or 'senate' in desc or 'house' in desc:
                            score += 1
                        
                        results.append({
                            'channel_id': channel_id,
                            'channel_title': title,
                            'description': item['snippet']['description'][:200] + '...' if len(item['snippet']['description']) > 200 else item['snippet']['description'],
                            'search_term': term,
                            'score': score,
                            'channel_url': f"https://www.youtube.com/channel/{channel_id}"
                        })
            
            time.sleep(0.1)  # Rate limit
            
        except Exception as e:
            print(f"Error searching for {term}: {e}")
    
    # Sort by score
    results.sort(key=lambda x: x['score'], reverse=True)
    
    return results

def create_html_table(results):
    """Create an HTML table with committee YouTube channels"""
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
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        h1 {
            color: #333;
            margin-bottom: 20px;
        }
        
        .filters {
            margin-bottom: 20px;
        }
        
        .filters input {
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            width: 300px;
            margin-right: 10px;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }
        
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        
        th {
            background: #f8f9fa;
            font-weight: 600;
            position: sticky;
            top: 0;
            z-index: 10;
        }
        
        tr:hover {
            background: #f8f9fa;
        }
        
        .chamber-house {
            color: #2e7d32;
            font-weight: bold;
        }
        
        .chamber-senate {
            color: #1565c0;
            font-weight: bold;
        }
        
        .channel-link {
            color: #007bff;
            text-decoration: none;
        }
        
        .channel-link:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏛️ Congressional Committee YouTube Channels</h1>
        
        <div class="filters">
            <input type="text" id="search" placeholder="Search committees or channels..." onkeyup="filterTable()">
            <select id="chamber-filter" onchange="filterTable()">
                <option value="">All Chambers</option>
                <option value="House">House</option>
                <option value="Senate">Senate</option>
            </select>
        </div>
        
        <table id="committee-table">
            <thead>
                <tr>
                    <th>Chamber</th>
                    <th>Committee</th>
                    <th>Channel Name</th>
                    <th>Link</th>
                </tr>
            </thead>
            <tbody>
'''
    
    # Group results by committee
    committee_groups = {}
    for result in results:
        key = (result['chamber'], result['committee_name'])
        if key not in committee_groups:
            committee_groups[key] = []
        committee_groups[key].append(result)
    
    # Build table rows
    for (chamber, committee), channels in sorted(committee_groups.items()):
        # Sort channels by score
        channels.sort(key=lambda x: x['score'], reverse=True)
        
        for i, channel in enumerate(channels[:4]):  # Show top 4 per committee
            html_content += f'''                <tr>
                    <td><span class="chamber-{chamber.lower()}">{chamber}</span></td>
                    <td>{committee if i == 0 else ''}</td>
                    <td>{channel['channel_title']}</td>
                    <td>
                        <a href="{channel['channel_url']}" target="_blank" class="channel-link">View Channel</a>
                    </td>
                </tr>
'''
    
    html_content += '''            </tbody>
        </table>
    </div>
    
    <script>
        function filterTable() {
            const searchTerm = document.getElementById('search').value.toLowerCase();
            const chamberFilter = document.getElementById('chamber-filter').value;
            const rows = document.querySelectorAll('#committee-table tbody tr');
            
            rows.forEach(row => {
                const chamber = row.cells[0].textContent;
                const committee = row.cells[1].textContent;
                const channel = row.cells[2].textContent;
                
                const matchesSearch = !searchTerm || 
                    committee.toLowerCase().includes(searchTerm) ||
                    channel.toLowerCase().includes(searchTerm);
                
                const matchesChamber = !chamberFilter || chamber === chamberFilter;
                
                row.style.display = matchesSearch && matchesChamber ? '' : 'none';
            });
        }
    </script>
</body>
</html>'''
    
    with open('committee_channels.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print("\n✅ Created committee_channels.html")

def main():
    print("🔍 Finding YouTube Channels for Congressional Committees")
    print("=" * 60)
    
    # Get all committees
    print("\n📋 Fetching committee list...")
    committees = get_all_committees()
    print(f"Found {len(committees)} committees")
    
    # Search for each committee
    all_results = []
    
    for i, committee in enumerate(committees):
        print(f"\n[{i+1}/{len(committees)}] Searching for: {committee['chamber']} {committee['name']}")
        
        channels = search_youtube_channels(committee['name'], committee['chamber'])
        
        # Keep top 4 results per committee
        for channel in channels[:4]:
            all_results.append({
                'committee_name': committee['name'],
                'chamber': committee['chamber'],
                'committee_code': committee['systemCode'],
                **channel
            })
        
        if channels:
            print(f"  ✅ Found {len(channels)} potential channels")
            print(f"  Top match: {channels[0]['channel_title']} (score: {channels[0]['score']})")
        else:
            print(f"  ❌ No channels found")
        
        time.sleep(0.5)  # Be nice to API
    
    # Save results as CSV
    output_file = 'committee_youtube_channels.csv'
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'chamber', 'committee_name', 'committee_code', 
            'channel_title', 'channel_url', 'score', 'description'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for result in all_results:
            writer.writerow({
                'chamber': result['chamber'],
                'committee_name': result['committee_name'],
                'committee_code': result['committee_code'],
                'channel_title': result['channel_title'],
                'channel_url': result['channel_url'],
                'score': result['score'],
                'description': result['description']
            })
    
    print(f"\n✅ Saved {len(all_results)} results to {output_file}")
    
    # Also save as JSON for easier processing
    with open('committee_youtube_channels.json', 'w') as f:
        json.dump({
            'metadata': {
                'generated': datetime.now().isoformat(),
                'total_committees': len(committees),
                'total_results': len(all_results)
            },
            'results': all_results
        }, f, indent=2)
    
    # Create HTML table
    create_html_table(all_results)

if __name__ == "__main__":
    main()
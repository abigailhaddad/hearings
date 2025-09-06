#!/usr/bin/env python3
"""Generate a static HTML viewer with embedded data for GitHub Pages"""

import json
import os
from datetime import datetime

def generate_static_html():
    """Generate index.html with embedded data"""
    
    # Get the root directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    
    # Load data files
    print("Loading data files...")
    matches_file = os.path.join(root_dir, 'data', 'youtube_congress_matches.json')
    with open(matches_file, 'r') as f:
        match_data = json.load(f)
    
    congress_file = os.path.join(root_dir, 'outputs', 'ec_filtered_index.json')
    with open(congress_file, 'r') as f:
        ec_index = json.load(f)
    
    # Categorize unmatched videos based on whether we have congressional data nearby
    unmatched_with_data = []  # Videos where we have Congress events within 2 weeks
    unmatched_no_data = []    # Videos where we have no Congress events nearby
    
    for video in match_data['unmatched']:
        if video.get('youtube_date'):
            try:
                video_date = datetime.fromisoformat(video['youtube_date'][:10])
                has_nearby_congress = False
                
                # Check if any congressional event is within 14 days
                for event in ec_index:
                    if event.get('date'):
                        try:
                            event_date = datetime.fromisoformat(event['date'][:10])
                            days_diff = abs((video_date - event_date).days)
                            if days_diff <= 14:
                                has_nearby_congress = True
                                break
                        except:
                            continue
                
                if has_nearby_congress:
                    unmatched_with_data.append(video)
                else:
                    unmatched_no_data.append(video)
            except:
                # If date parsing fails, put in no data category
                unmatched_no_data.append(video)
    
    # HTML template
    html_template = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Energy & Commerce YouTube-Congress Matches</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        
        .container {
            max-width: 1600px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        h1 {
            color: #2c3e50;
            font-size: 24px;
            margin-bottom: 10px;
        }
        
        .tabs {
            margin-bottom: 20px;
            border-bottom: 2px solid #ecf0f1;
        }
        
        .tab-button {
            background: none;
            border: none;
            padding: 12px 24px;
            font-size: 16px;
            cursor: pointer;
            color: #7f8c8d;
        }
        
        .tab-button.active {
            color: #3498db;
            border-bottom: 3px solid #3498db;
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            font-size: 14px;
        }
        
        th {
            background: #f8f9fa;
            padding: 10px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #dee2e6;
        }
        
        td {
            padding: 10px;
            border-bottom: 1px solid #ecf0f1;
        }
        
        tr:hover {
            background: #f8f9fa;
        }
        
        .date {
            white-space: nowrap;
            font-family: monospace;
            font-size: 12px;
            color: #666;
        }
        
        .youtube-link {
            color: #c4302b;
            text-decoration: none;
        }
        
        .youtube-link:hover {
            text-decoration: underline;
        }
        
        .committee-badge {
            display: inline-block;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 11px;
            background: #e3f2fd;
            color: #1565c0;
        }
        
        .unmatched-video {
            margin-bottom: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #dc3545;
        }
        
        .suggestion {
            margin: 10px 0;
            padding: 10px;
            background: white;
            border-radius: 4px;
            font-size: 13px;
        }
        
        .suggestion-score {
            color: #666;
            font-size: 12px;
        }
        
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ecf0f1;
            text-align: center;
            color: #666;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 Energy & Commerce YouTube-Congress Matches</h1>
        
        <div class="tabs">
            <button class="tab-button active" onclick="showTab('matched', this)">Matched Videos (''' + str(len(match_data['matches'])) + ''')</button>
            <button class="tab-button" onclick="showTab('unmatched-with-data', this)">Unmatched - Could Match (''' + str(len(unmatched_with_data)) + ''')</button>
            <button class="tab-button" onclick="showTab('unmatched-no-data', this)">Unmatched - No Congress Data (''' + str(len(unmatched_no_data)) + ''')</button>
        </div>
        
        <div class="tab-content active" id="matched">
            <table>
                <thead>
                    <tr>
                        <th>YouTube Date</th>
                        <th>Congress Date</th>
                        <th>YouTube Title</th>
                        <th>Congress Title</th>
                        <th>Committee</th>
                        <th>Links</th>
                    </tr>
                </thead>
                <tbody>
'''
    
    # Add matched rows
    seen = set()
    for match in sorted(match_data['matches'], key=lambda x: x.get('youtube_date') or '', reverse=True):
        # Skip duplicates
        key = f"{match['youtube_id']}_{match.get('eventId', 'none')}"
        if key in seen:
            continue
        seen.add(key)
        
        yt_date = match.get('youtube_date', 'N/A')
        cg_date = match.get('congress_date', 'N/A')
        committee = match.get('committee', 'House Energy and Commerce')
        
        html_template += f'''                    <tr>
                        <td class="date">{yt_date}</td>
                        <td class="date">{cg_date}</td>
                        <td>{match['youtube_title']}</td>
                        <td>{match['congress_title']}</td>
                        <td><span class="committee-badge">{committee}</span></td>
                        <td>
                            <a href="{match.get('youtube_url', '')}" target="_blank" class="youtube-link">YouTube</a>
                            {' | <a href="' + match['congress_url'] + '" target="_blank">Congress</a>' if match.get('congress_url') else ''}
                        </td>
                    </tr>
'''
    
    html_template += '''                </tbody>
            </table>
        </div>
        
        <div class="tab-content" id="unmatched-with-data">
            <p style="color: #666; margin-bottom: 20px;">
                These ''' + str(len(unmatched_with_data)) + ''' videos have congressional events within 2 weeks but didn't match.
                This suggests potential matching improvements needed.
            </p>
'''
    
    # Process unmatched videos with suggestions
    for video in unmatched_with_data:
        html_template += f'''
            <div class="unmatched-video">
                <h3 style="margin-top: 0;">
                    <a href="https://youtube.com/watch?v={video['youtube_id']}" target="_blank" class="youtube-link">
                        {video['youtube_title']}
                    </a>
                </h3>
                <p style="color: #666; margin: 5px 0;">Date: {video['youtube_date']}</p>
                <h4>Top 3 Potential Matches:</h4>
'''
        
        # Calculate suggestions
        suggestions = []
        for event in ec_index:
            score = 0
            
            # Date similarity
            if video.get('youtube_date') and event.get('date'):
                try:
                    yt_date = datetime.fromisoformat(video['youtube_date'][:10])
                    cg_date = datetime.fromisoformat(event['date'][:10])
                    days_diff = abs((yt_date - cg_date).days)
                    
                    if days_diff == 0:
                        score += 50
                    elif days_diff <= 1:
                        score += 30
                    elif days_diff <= 7:
                        score += 10
                except:
                    pass
            
            # Title word matching
            yt_words = set(video['youtube_title'].lower().split())
            cg_words = set(event.get('title', '').lower().split())
            common_words = [w for w in yt_words & cg_words if len(w) > 3]
            score += len(common_words) * 10
            
            if score > 0:
                suggestions.append((event, score))
        
        # Sort and take top 3
        suggestions.sort(key=lambda x: x[1], reverse=True)
        top_suggestions = suggestions[:3]
        
        if top_suggestions:
            for i, (event, score) in enumerate(top_suggestions):
                html_template += f'''
                <div class="suggestion">
                    {i + 1}. {event['title']}
                    <br><span class="suggestion-score">Date: {event['date'][:10]} | Score: {score}</span>
                </div>
'''
        else:
            html_template += '<p style="color: #999;">No potential matches found</p>'
        
        html_template += '            </div>\n'
    
    html_template += '''        </div>
        
        <div class="tab-content" id="unmatched-no-data">
            <p style="color: #666; margin-bottom: 20px;">
                These ''' + str(len(unmatched_no_data)) + ''' videos don't have congressional events within 2 weeks.
                This likely means Congress.gov is missing data for these time periods.
            </p>
'''
    
    # Group videos by year to show patterns
    videos_by_year = {}
    for video in unmatched_no_data:
        if video.get('youtube_date'):
            year = video['youtube_date'][:4]
            if year not in videos_by_year:
                videos_by_year[year] = []
            videos_by_year[year].append(video)
    
    # Show videos grouped by year
    for year in sorted(videos_by_year.keys(), reverse=True):
        year_videos = videos_by_year[year]
        html_template += f'''
            <h3>{year} ({len(year_videos)} videos)</h3>
'''
        for video in sorted(year_videos, key=lambda x: x.get('youtube_date', ''), reverse=True):
            html_template += f'''
            <div style="margin-bottom: 15px; padding: 10px; background: #f8f9fa; border-radius: 4px;">
                <a href="https://youtube.com/watch?v={video['youtube_id']}" target="_blank" class="youtube-link">
                    {video['youtube_title']}
                </a>
                <span style="color: #666; margin-left: 10px;">({video['youtube_date']})</span>
            </div>
'''
    
    html_template += '''        </div>
        
        <div class="footer">
            <p>Generated: ''' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '''</p>
            <p>View the <a href="https://github.com/abigailhaddad/youtube">source code on GitHub</a></p>
        </div>
    </div>

    <script>
        function showTab(tabName, button) {
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Remove active from all buttons
            document.querySelectorAll('.tab-button').forEach(btn => {
                btn.classList.remove('active');
            });
            
            // Show selected tab
            document.getElementById(tabName).classList.add('active');
            button.classList.add('active');
        }
    </script>
</body>
</html>'''
    
    # Write to file
    output_path = os.path.join(root_dir, 'index.html')
    with open(output_path, 'w') as f:
        f.write(html_template)
    
    print(f"✅ Generated static viewer: {output_path}")
    print(f"   - Embedded {len(match_data['matches'])} matches")
    print(f"   - Embedded {len(unmatched_with_data)} unmatched videos (could match)")
    print(f"   - Embedded {len(unmatched_no_data)} unmatched videos (no congress data)")
    print(f"   - File size: {os.path.getsize(output_path) / 1024:.1f} KB")

if __name__ == "__main__":
    generate_static_html()
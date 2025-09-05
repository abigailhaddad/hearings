#!/usr/bin/env python3
"""Generate a static HTML viewer with embedded data for GitHub Pages"""

import json
import os
from datetime import datetime

def generate_static_html():
    """Generate index.html with embedded data"""
    
    # Load data files
    print("Loading data files...")
    with open('../outputs/youtube_congress_expanded_matches.json', 'r') as f:
        match_data = json.load(f)
    
    with open('../outputs/ec_filtered_index.json', 'r') as f:
        ec_index = json.load(f)
    
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
        
        .summary {
            font-size: 18px;
            color: #666;
            margin-bottom: 30px;
        }
        
        .success { color: #27ae60; font-weight: bold; }
        .error { color: #e74c3c; font-weight: bold; }
        
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
        <p class="summary">Generated: ''' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '''</p>
        
        <div class="tabs" id="tabs">
            <button class="tab-button active" onclick="showTab('matched')">Matched Videos (''' + str(match_data['metadata']['matched']) + ''')</button>
            ''' + (f'<button class="tab-button" onclick="showTab(\'unmatched\')">Unmatched Videos ({match_data["metadata"]["unmatched"]})</button>' if match_data['metadata']['unmatched'] > 0 else '') + '''
        </div>
        
        <div class="tab-content active" id="matched">
            <table id="matched-table">
                <thead>
                    <tr>
                        <th>YouTube Date</th>
                        <th>Congress Date</th>
                        <th>YouTube Title</th>
                        <th>Congress Title</th>
                        <th>Committee</th>
                        <th>Event ID</th>
                        <th>Links</th>
                    </tr>
                </thead>
                <tbody>
'''
    
    # Add matched rows
    seen = set()
    for match in sorted(match_data['matches'], key=lambda x: x.get('youtube_date') or '', reverse=True):
        # Skip duplicates
        key = f"{match['youtube_id']}_{match['eventId']}"
        if key in seen:
            continue
        seen.add(key)
        
        yt_date = match['youtube_date'].split('T')[0] if match.get('youtube_date') else 'N/A'
        cg_date = match.get('congress_date', 'Unknown')
        committee = match.get('committee', 'House Energy and Commerce')
        
        html_template += f'''                    <tr>
                        <td class="date">{yt_date}</td>
                        <td class="date">{cg_date}</td>
                        <td>{match['youtube_title']}</td>
                        <td>{match['congress_title']}</td>
                        <td><span class="committee-badge">{committee}</span></td>
                        <td>{match['eventId']}</td>
                        <td>
                            <a href="https://youtube.com/watch?v={match['youtube_id']}" target="_blank" class="youtube-link">YouTube</a>
                            {' | <a href="' + match['congress_url'] + '" target="_blank" style="color: #2c5aa0;">Congress.gov</a>' if match.get('congress_url') else ''}
                        </td>
                    </tr>
'''
    
    html_template += '''                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p>View the <a href="https://github.com/abigailhaddad/hearings">source code on GitHub</a></p>
            <p>This is a work in progress. Currently tracking recent videos from the House Energy & Commerce Committee.</p>
        </div>
    </div>

    <script>
        // Embed data for potential use
        const matchData = ''' + json.dumps(match_data) + ''';
        const ecIndex = ''' + json.dumps(ec_index) + ''';
        
        function showTab(tabName) {
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            document.querySelectorAll('.tab-button').forEach(button => {
                button.classList.remove('active');
            });
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
        }
    </script>
</body>
</html>'''
    
    # Write to file
    output_path = '../index.html'
    with open(output_path, 'w') as f:
        f.write(html_template)
    
    print(f"✅ Generated static viewer: {output_path}")
    print(f"   - Embedded {len(match_data['matches'])} matches")
    print(f"   - File size: {os.path.getsize(output_path) / 1024:.1f} KB")

if __name__ == "__main__":
    generate_static_html()
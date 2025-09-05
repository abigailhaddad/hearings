import json
import csv
from datetime import datetime

def export_to_csv():
    """Export matches to CSV format"""
    
    # Load matches
    with open('youtube_congress_matches.json', 'r') as f:
        data = json.load(f)
    
    # Create CSV for matches
    with open('youtube_congress_matches.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow([
            'YouTube ID',
            'YouTube Title', 
            'YouTube Date',
            'YouTube URL',
            'Congress Event ID',
            'Congress Title',
            'Match Score',
            'Match Reasons',
            'Status'
        ])
        
        # Write matches
        for match in data['matches']:
            writer.writerow([
                match['youtube_id'],
                match['youtube_title'],
                match['youtube_date'],
                f"https://www.youtube.com/watch?v={match['youtube_id']}",
                match['eventId'],
                match['congress_title'],
                f"{match['score']:.2f}",
                ' | '.join(match['reasons']),
                'Matched'
            ])
        
        # Write unmatched
        for unmatched in data['unmatched']:
            writer.writerow([
                unmatched['youtube_id'],
                unmatched['youtube_title'],
                unmatched.get('youtube_date', ''),
                f"https://www.youtube.com/watch?v={unmatched['youtube_id']}",
                '',
                '',
                f"{unmatched.get('best_score', 0):.2f}",
                '',
                'Unmatched'
            ])
    
    print(f"✅ Exported to youtube_congress_matches.csv")
    print(f"   Total rows: {len(data['matches']) + len(data['unmatched']) + 1}")

if __name__ == "__main__":
    export_to_csv()
#!/bin/bash

# Script to rebuild committee data based on committees_config.yaml
# Now with INCREMENTAL processing - only fetches/processes what's needed

echo "🔄 Rebuilding YouTube-Congress data based on committees_config.yaml"
echo "================================================================="

# Check if PyYAML is installed
python -c "import yaml" 2>/dev/null || {
    echo "❌ Error: PyYAML not found. Please run: pip install pyyaml"
    exit 1
}

# Show active committees
echo "📋 Active committees from committees_config.yaml:"
python -c "
import yaml
with open('committees_config.yaml', 'r') as f:
    config = yaml.safe_load(f)
    active = config['active_committees']
    committees = config['committees']
    for comm_id in active:
        if comm_id in committees:
            print(f'   - {committees[comm_id][\"short_name\"]} ({comm_id})')
"

# Move to scripts directory
cd scripts

# Step 0: Fetch master Congress data (if needed)
echo -e "\n🏛️ Step 0: Checking master Congress.gov data..."
if [ -f "../outputs/all_house_meetings_master.json" ]; then
    # Check age of master file
    AGE_DAYS=$(python -c "
import os
from datetime import datetime
age = (datetime.now().timestamp() - os.path.getmtime('../outputs/all_house_meetings_master.json')) / 86400
print(int(age))
")
    echo "   Master dataset exists (${AGE_DAYS} days old)"
    if [ $AGE_DAYS -gt 7 ]; then
        echo "   Dataset is older than 7 days, consider refreshing with:"
        echo "   python fetch_all_congress_meetings.py"
    fi
else
    echo "   No master dataset found. Fetching ALL House meetings..."
    echo "   This is a one-time operation that takes several minutes..."
    python fetch_all_congress_meetings.py
fi

# Step 1: Filter committees from master data
echo -e "\n🔍 Step 1: Filtering committee data from master dataset..."
python filter_committee_from_master.py

# Step 2: Parse YouTube HTML for all active committees
echo -e "\n📺 Step 2: Parsing YouTube HTML for active committees..."
python parse_youtube_html_multi.py

# Step 2.5: Update videos with exact dates using yt-dlp
echo -e "\n📅 Step 2.5: Getting exact dates for YouTube videos..."
echo "This may take a while on first run (fetches metadata for each video)"
python update_video_dates_ytdlp.py

# Step 3: Run LLM matching
echo -e "\n🤖 Step 3: Running LLM-assisted matching..."
echo "Note: Requires litellm to be installed (pip install litellm)"
if python match_with_llm.py; then
    echo "✅ Matching completed successfully"
    
    # Step 4: Generate static viewer
    echo -e "\n🌐 Step 4: Generating static HTML viewer..."
    if python generate_static_viewer.py; then
        echo "✅ Static viewer generated successfully"
    else
        echo "❌ Failed to generate static viewer"
        exit 1
    fi
else
    echo "❌ Matching failed - skipping HTML generation"
    echo "   Check that litellm is installed and configured"
    echo "   Make sure you have an API key in your .env file:"
    echo "   OPENAI_API_KEY=your-key-here"
    exit 1
fi

# Move back
cd ..

echo -e "\n✅ Complete! Data has been regenerated based on active committees"
echo ""
echo "Generated files:"
python -c "
import yaml
with open('committees_config.yaml', 'r') as f:
    config = yaml.safe_load(f)
    active = config['active_committees']
    suffix = '_'.join(active)
    
    print('   YouTube data:')
    for comm_id in active:
        print(f'   - data/{comm_id}_youtube_complete_dataset.json')
        print(f'   - data/{comm_id}_youtube_videos_for_matching.json')
    
    if len(active) > 1:
        print('   - data/all_committees_youtube_videos.json')
    
    print(f'\\n   Congressional data:')
    print(f'   - outputs/all_house_meetings_master.json (master dataset)')
    for comm_id in active:
        print(f'   - outputs/{comm_id}_filtered_index.json')
    print(f'   - outputs/{suffix}_filtered_index.json (combined)')
    
    print(f'\\n   Matches:')
    print(f'   - data/youtube_congress_matches.json')
    
    print(f'\\n   HTML viewer:')
    print(f'   - index.html')
"
echo ""
echo "💡 To add more committees:"
echo "   1. Edit committees_config.yaml and add to active_committees"
echo "   2. Download their YouTube HTML"
echo "   3. Run ./rebuild_all.sh again (it will only process new data)"
echo ""
echo "You can now serve index.html to view the results!"
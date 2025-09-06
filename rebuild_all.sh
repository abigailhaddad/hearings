#!/bin/bash

# Script to rebuild all committee data based on committees_config.yaml
# Usage: ./rebuild_all.sh

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

# Step 1: Parse YouTube HTML for all active committees
echo -e "\n📺 Step 1: Parsing YouTube HTML for active committees..."
python parse_youtube_html_multi.py

# Step 2: Build Congress.gov index for active committees
echo -e "\n🏛️ Step 2: Fetching congressional data from Congress.gov API..."

# Get the output filename based on active committees
OUTPUT_FILE=$(python -c "
import yaml
with open('../committees_config.yaml', 'r') as f:
    config = yaml.safe_load(f)
    suffix = '_'.join(config['active_committees'])
    print(f'../outputs/{suffix}_filtered_index.json')
")

if [ -f "$OUTPUT_FILE" ]; then
    echo "   Found existing congressional data file with $(grep -c '"eventId"' "$OUTPUT_FILE" || echo 0) events"
    echo "   Skipping download (delete $OUTPUT_FILE to re-fetch)"
else
    echo "This will take several minutes as it fetches data from multiple congresses..."
    python build_committee_index.py
fi

# Step 3: Run LLM matching
echo -e "\n🤖 Step 3: Running LLM-assisted matching..."
echo "Note: Requires litellm to be installed (pip install litellm)"
if python match_with_llm_multi.py; then
    echo "✅ Matching completed successfully"
    
    # Step 4: Generate static viewer
    echo -e "\n🌐 Step 4: Generating static HTML viewer..."
    if python generate_static_viewer_multi.py; then
        echo "✅ Static viewer generated successfully"
    else
        echo "❌ Failed to generate static viewer"
        exit 1
    fi
else
    echo "❌ Matching failed - skipping HTML generation"
    echo "   Check that litellm is installed and configured"
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
    print(f'   - outputs/{suffix}_filtered_index.json')
    
    print(f'\\n   Matches:')
    print(f'   - data/youtube_congress_matches.json')
    
    print(f'\\n   HTML viewer:')
    print(f'   - index.html')
"
echo ""
echo "You can now serve index.html to view the results!"
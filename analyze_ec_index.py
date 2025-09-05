import json

# Load the index
data = json.load(open('ec_filtered_index.json'))

print(f'Total E&C events found: {len(data)}')

# Analyze by type
types = {}
for e in data:
    t = e.get('type', 'Unknown')
    types[t] = types.get(t, 0) + 1

print('\nEvent types:')
for k, v in sorted(types.items(), key=lambda x: x[1], reverse=True):
    print(f'  {k}: {v}')

# Analyze by committee
committees = {}
for e in data:
    c = e.get('committeeName', 'Unknown')
    committees[c] = committees.get(c, 0) + 1

print('\nBy committee:')
for k, v in sorted(committees.items(), key=lambda x: x[1], reverse=True):
    print(f'  {k}: {v}')

# Date range
dates = [e['date'][:10] for e in data if e.get('date')]
if dates:
    dates.sort()
    print(f'\nDate range: {dates[0]} to {dates[-1]}')

# Sample events
print('\nSample recent events:')
for e in data[:5]:
    print(f"- {e.get('date', 'No date')[:10]}: {e['title'][:60]}...")
    print(f"  Committee: {e.get('committeeName', 'Unknown')}")
    print(f"  Type: {e.get('type', 'Unknown')}, Status: {e.get('meetingStatus', 'Unknown')}")
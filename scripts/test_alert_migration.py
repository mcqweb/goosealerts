import json, os
from datetime import datetime, timezone
from virgin_goose import already_alerted, save_state

os.makedirs('state', exist_ok=True)
file='state/test_alert_state.json'
# Create legacy raw key with en-dash
raw_key = '351000_Jean–Pierre Muani'
state = {'alerted': {raw_key: datetime.now(timezone.utc).isoformat()}}
with open(file,'w',encoding='utf-8') as f:
    json.dump(state,f)
print('Raw state written:', raw_key)

print('Check already_alerted with ascii hyphen name:')
print(already_alerted('Jean-Pierre Muani', '351000', file))
print('Now call save_state to migrate:')
save_state('Jean-Pierre Muani', '351000', file)
with open(file,'r',encoding='utf-8') as f:
    s=json.load(f)
print('Post-save keys:', list(s.get('alerted',{}).keys()))

import json
from collections import defaultdict

with open('accafreeze_opportunities.json', 'r', encoding='utf-8') as f:
    ops = json.load(f)

lt = []
le = []
for o in ops:
    bo = o.get('back_odds')
    try:
        bof = float(bo)
    except Exception:
        continue
    if bof < 1.5:
        lt.append(o)
    if bof <= 1.5:
        le.append(o)

print(f"Total opportunities: {len(ops)}")
print(f"back_odds < 1.5: {len(lt)}")
print(f"back_odds <= 1.5: {len(le)}")

# Show examples and grouping by kickoff for <=1.5
groups = defaultdict(list)
for o in le:
    groups[o.get('kickoff_display', 'Unknown')].append(o)

for ko, items in sorted(groups.items(), key=lambda kv: kv[0]):
    print(f"KO: {ko} -> {len(items)} items")
    for it in items:
        print(f"  - {it.get('home_team')} v {it.get('away_team')}: {it.get('outcome')} @ {it.get('back_odds')}")

# Team/Fixture Tracking Enhancement

## Overview
The player name system now tracks **team** and **fixture** information to prevent suggesting mappings for players who are clearly different people playing in different matches.

## Problem Solved

### Before
```
Suggesting: "J Smith" (Man United) → "J Smith" (Liverpool) ❌
```
The system would suggest these as duplicates because the names match, even though they're clearly different players on different teams.

### After
```
Skipping: "J Smith" has conflicting team data (Man United vs Liverpool) ✓
```
The system detects conflicting team data and automatically excludes these pairs from suggestions.

---

## How It Works

### 1. Database Schema
Added two new columns to `player_tracking` table:

```sql
team_name TEXT    -- e.g., "Manchester United"
fixture TEXT      -- e.g., "Manchester United v Liverpool"
```

Both columns are:
- **Optional** (NULL allowed) - won't break if data unavailable
- **Indexed** - fast lookups for conflict detection
- **Backward compatible** - existing records have NULL values

### 2. Conflict Detection
When suggesting mappings, the system now:

1. Gets all teams for player A: `{"Man United", "England"}`
2. Gets all teams for player B: `{"Liverpool", "Spain"}`
3. Checks for overlap: `None`
4. **Skips suggestion** - conflicting team data!

If either player has no team data, suggestion proceeds (better safe than sorry).

### 3. Fixture Tracking
Even without team-specific data, tracking fixtures helps:
- Understand match context
- Future enhancements (lineup integration)
- Debugging and analysis

---

## Database Upgrade

### For Existing Databases
If you already ran the migration, upgrade your schema:

```bash
python upgrade_player_db_schema.py
```

This will:
- ✅ Backup your database
- ✅ Add `team_name` and `fixture` columns
- ✅ Create indexes
- ✅ Verify upgrade

### For New Databases
Run the standard migration - new schema included:

```bash
python migrate_player_db.py migrate
```

---

## Usage

### Option 1: Automatic (Recommended)
Use the `match_context.py` helper:

```python
from match_context import get_match_context
from player_names import track_player_name

# Get context from match data
match_context = get_match_context(match_data, player_name)

# Track with context
track_player_name(
    player_name=name,
    site_name='betfair',
    match_id=match_id,
    team_name=match_context['team_name'],   # None if unknown
    fixture=match_context['fixture']         # "Team A v Team B"
)
```

### Option 2: Manual
If you know the team/fixture explicitly:

```python
track_player_name(
    player_name="Bruno Fernandes",
    site_name='betfair',
    match_id='12345',
    team_name='Manchester United',           # Optional
    fixture='Manchester United v Liverpool'  # Optional
)
```

### Option 3: Backward Compatible
Existing code still works (team/fixture will be None):

```python
track_player_name("Bruno Fernandes", "betfair")  # Still works!
```

---

## Integration Points

### Where to Add Team Tracking

#### 1. **Betfair Player Tracking** (virgin_goose.py ~line 2053)
```python
# OLD:
track_player_name(player_name, 'betfair')

# NEW:
match_context = get_match_context(match_data)
track_player_name(
    player_name, 'betfair', 
    match_id=match_id,
    fixture=match_context['fixture']
)
```

#### 2. **Exchange Odds Tracking** (virgin_goose.py ~line 2070)
```python
# OLD:
track_player_name(player_name, site_name)

# NEW:
match_context = get_match_context(match_data)
track_player_name(
    player_name, site_name,
    match_id=match_id,
    fixture=match_context['fixture']
)
```

#### 3. **Lineup Tracking** (virgin_goose.py ~line 1807)
```python
# OLD:
track_player_name(name, 'lineup')

# NEW:
match_context = get_match_context(match_data)
track_player_name(
    name, 'lineup',
    match_id=match_id,
    team_name=team_name,  # Can extract from lineup API!
    fixture=match_context['fixture']
)
```

---

## API Reference

### New Functions

#### `player_db.get_player_teams(player_key)`
Returns set of all teams a player has been seen with.

```python
teams = db.get_player_teams("bruno fernandes")
# Returns: {"Manchester United", "Portugal"}
```

#### `player_db.get_player_fixtures(player_key)`
Returns set of all fixtures a player has been seen in.

```python
fixtures = db.get_player_fixtures("bruno fernandes")
# Returns: {"Manchester United v Liverpool", "Portugal v Spain"}
```

#### `player_db.have_conflicting_teams(player_key1, player_key2)`
Check if two players have conflicting team data.

```python
conflict = db.have_conflicting_teams("j smith", "john smith")
# Returns: True if they play for different teams, False otherwise
```

---

## Match Context Helper

### `get_match_context(match_data, player_name=None)`
Extract team/fixture info from match data.

```python
from match_context import get_match_context

match_data = {
    'home_team': 'Manchester United',
    'away_team': 'Liverpool',
    'id': '12345'
}

context = get_match_context(match_data)
# Returns: {
#   'team_name': None,  # Unknown which team player is on
#   'fixture': 'Manchester United v Liverpool'
# }
```

### `normalize_fixture(home_team, away_team)`
Create normalized fixture string.

```python
fixture = normalize_fixture("Man United", "Liverpool")
# Returns: "Man United v Liverpool"
```

---

## Benefits

### 1. **Smarter Suggestions**
- ✅ No more cross-team false positives
- ✅ Focus on genuinely duplicate names
- ✅ Less manual work skipping obvious non-matches

### 2. **Better Data Quality**
- ✅ Richer player profiles
- ✅ Team association history
- ✅ Fixture-level tracking

### 3. **Future Enhancements**
- 🔄 Lineup-based team detection
- 🔄 Team-specific player search
- 🔄 Transfer detection (player changes teams)
- 🔄 Competition-based filtering

---

## Example: Before vs After

### Before Enhancement
```
Found 50 potential matches

[1/50] POTENTIAL MATCH (Score: 85%)
1. j williams
   • Occurrences: 12, Last seen: 2026-01-28

2. john williams  
   • Occurrences: 8, Last seen: 2026-01-28

Your choice: [1/2/s/q] s  ⬅️ User has to skip manually

[2/50] POTENTIAL MATCH (Score: 82%)
...
```

### After Enhancement
```
Found 30 potential matches  ⬅️ 20 auto-filtered!

[1/30] POTENTIAL MATCH (Score: 85%)
1. j martinez
   • Occurrences: 12, Last seen: 2026-01-28
   • Teams: Manchester United

2. jorge martinez
   • Occurrences: 8, Last seen: 2026-01-28  
   • Teams: Manchester United  ⬅️ Same team = valid suggestion!

Your choice: [1/2/s/q]
```

Cross-team "J Williams" vs "John Williams" was automatically filtered out.

---

## Troubleshooting

### "No team data showing"
**Cause**: Existing tracking records don't have team data  
**Solution**: Data will populate as new sightings are tracked. Old records remain valid with NULL team data.

### "Still suggesting cross-team matches"
**Cause**: Both players have NULL team data (not tracked yet)  
**Solution**: Normal - system is conservative. As more data accumulates, filtering improves.

### "Schema upgrade failed"
**Cause**: Database in use or corrupted  
**Solution**: 
1. Stop virgin_goose.py
2. Restore from backup in `data/player_names.db.backup_*`
3. Re-run upgrade

---

## Testing

### Test Conflict Detection
```python
from player_db import get_db

db = get_db()

# Add some test data
db.track_player("j smith", "J Smith", "betfair", 
                team_name="Manchester United", 
                fixture="Manchester United v Liverpool")

db.track_player("john smith", "John Smith", "betfair",
                team_name="Liverpool",
                fixture="Manchester United v Liverpool")

# Check for conflict
has_conflict = db.have_conflicting_teams("j smith", "john smith")
print(f"Conflict: {has_conflict}")  # Should print: True
```

### Verify Schema
```bash
sqlite3 data/player_names.db "PRAGMA table_info(player_tracking);"
```

Should show `team_name` and `fixture` columns.

---

## Migration Checklist

- [ ] Backup existing database
- [ ] Run `upgrade_player_db_schema.py`
- [ ] Verify schema with `migrate_player_db.py stats`
- [ ] Update virgin_goose.py tracking calls (optional but recommended)
- [ ] Test with `suggest_player_mappings_sqlite.py`
- [ ] Monitor for reduced false positives

---

## Future Enhancements

### Phase 1 (Current)
- ✅ Schema support for team/fixture
- ✅ Conflict detection in suggestions
- ✅ Display team info in suggestions

### Phase 2 (Planned)
- 🔄 Lineup API integration for team detection
- 🔄 Update virgin_goose.py tracking calls
- 🔄 Automatic team extraction from match data

### Phase 3 (Future)
- 🔄 Transfer detection (player changes teams)
- 🔄 Team-based player search
- 🔄 Competition filtering
- 🔄 Historical team associations

---

## Summary

✅ **Smarter suggestions** - No cross-team false positives  
✅ **Richer data** - Track team and fixture context  
✅ **Backward compatible** - Existing code still works  
✅ **Future ready** - Foundation for lineup integration  
✅ **Easy upgrade** - One command, auto-backup  

The system now intelligently avoids suggesting mappings for players who clearly play for different teams, saving you time and improving data quality.

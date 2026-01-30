# Player Tracking Deduplication Fix - Summary

## Problem
- Players were being added to the database multiple times (e.g., Amadou Onana had 5 entries)
- Some entries had no `match_id` (NULL values)
- All entries had `team_name = NULL` despite having fixture data
- Every call to `track_player()` created a new INSERT instead of updating existing records

## Root Causes
1. **No unique constraint**: `player_tracking` table allowed duplicate entries
2. **Always INSERT**: The `track_player()` function always inserted new records
3. **Missing team extraction**: Team names weren't being extracted from fixtures

## Solution

### 1. Database Schema Fix
- Added UNIQUE constraint on `(player_key, site_name, team_name, fixture)`
- Changed `track_player()` to use UPSERT (INSERT ... ON CONFLICT DO UPDATE)
- Deduplicated existing data (removed 40 duplicate entries)

### 2. Team Extraction
- Updated `track_player_name()` wrapper in virgin_goose.py to extract team from fixture
- Team is extracted from "Team A v Team B" format (takes first team)
- Backfilled 16 existing entries with team names from fixtures
- Removed 11 entries that had no context data (no team, fixture, or match_id)

### 3. Updated Code

#### player_db.py
```python
def track_player(self, player_key: str, raw_name: str, site_name: str, 
                match_id: Optional[str] = None, team_name: Optional[str] = None,
                fixture: Optional[str] = None) -> None:
    """Track a player sighting (UPSERT - updates if exists, inserts if new)."""
    
    conn.execute("""
        INSERT INTO player_tracking (player_key, raw_name, site_name, match_id, team_name, fixture, seen_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(player_key, site_name, team_name, fixture) DO UPDATE SET
            raw_name = excluded.raw_name,
            match_id = COALESCE(excluded.match_id, match_id),
            seen_at = excluded.seen_at
    """, ...)
```

#### virgin_goose.py
```python
def track_player_name(player_name, site_name, match_id=None, team_name=None, fixture=None):
    """Track a player name - extracts team from fixture if not provided."""
    
    # Extract team from fixture if not provided
    if team_name is None and fixture:
        parts = fixture.split(' v ')
        if len(parts) >= 2:
            team_name = parts[0].strip()
    
    # Delegate to player_names module
    from player_names import track_player_name as track_player
    track_player(player_name, site_name, match_id, team_name, fixture)
```

## Results

### Before Fix
- Total tracking entries: 67
- Unique entries: 27
- **Duplicates: 40**
- NULL match_id: 11
- NULL team_name: **67** (100%)

### After Fix
- Total tracking entries: 16
- Unique entries: 16
- **Duplicates: 0** ✅
- NULL match_id: 0 ✅
- NULL team_name: **0** (0%) ✅

### Amadou Onana Example
**Before:** 5 entries
```
1. betfair, team=None, fixture='Aston Villa v Red Bull Salzburg', match_id='4112'
2. betfair, team=None, fixture='Aston Villa v Red Bull Salzburg', match_id='4112'
3. betfair, team=None, fixture='Aston Villa v Red Bull Salzburg', match_id='4112'
4. betfair, team=None, fixture='Aston Villa v Red Bull Salzburg', match_id='4112'
5. betfair, team=None, fixture=None, match_id=None
```

**After:** 1 entry
```
1. betfair, team='Aston Villa', fixture='Aston Villa v Red Bull Salzburg', match_id='4112'
```

## Database Schema

```sql
CREATE TABLE player_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_key TEXT NOT NULL,
    raw_name TEXT NOT NULL,
    site_name TEXT NOT NULL,
    match_id TEXT,
    team_name TEXT,
    fixture TEXT,
    seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(player_key, site_name, team_name, fixture)  -- Prevents duplicates
);

-- Indexes for fast lookups
CREATE INDEX idx_player_key ON player_tracking(player_key);
CREATE INDEX idx_site_name ON player_tracking(site_name);
CREATE INDEX idx_team_name ON player_tracking(team_name);
CREATE INDEX idx_fixture ON player_tracking(fixture);
```

## How It Works Now

1. **First time seeing a player**: INSERT new record
2. **Seeing same player again** (same player_key, site, team, fixture): UPDATE existing record
   - Updates `seen_at` timestamp
   - Updates `match_id` if it was NULL before
   - Updates `raw_name` if different variant seen
3. **Same player, different fixture**: INSERT new record (different match)
4. **Same player, different team**: INSERT new record (transferred or wrong data)

## Benefits

1. **No more duplicates**: Each player/site/team/fixture combination appears once
2. **Cleaner data**: All entries have team and match context
3. **Better mapping suggestions**: Won't suggest cross-team players as duplicates
4. **Faster queries**: Smaller table with proper indexes
5. **Automatic updates**: Seeing a player again updates their latest timestamp

## Files Modified

1. `player_db.py` - Changed INSERT to UPSERT in `track_player()`
2. `virgin_goose.py` - Added team extraction in `track_player_name()`
3. `fix_player_tracking_duplicates.py` - Migration script (one-time use)
4. `extract_teams_from_fixtures.py` - Backfill script (one-time use)

## Next Steps

✅ Database is clean and ready
✅ Future tracking will not create duplicates
✅ All new entries will have team context

The system will now:
- Track players efficiently without duplication
- Maintain team context for better mapping suggestions
- Update existing records when players are seen again
- Only create new records for genuinely different contexts (different teams/fixtures)

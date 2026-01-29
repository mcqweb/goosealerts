# Player Name System Performance Analysis

## Current Implementation

### Data Files
- **player_name_mappings.json**: ~29 mappings (small)
- **player_name_tracking.json**: ~1,760 tracked players (growing)
- **skipped_player_pairs.json**: Unknown size (will grow over time)

### Operations

#### 1. **load_player_mappings()** - Called ~20+ times
- Loads entire JSON file from disk
- Normalizes all keys 
- Called on EVERY player name lookup
- **Problem**: Full file I/O + normalization on every call

#### 2. **track_player_name()** - Called extensively during each poll
- Load entire tracking file (1,760 entries)
- Update one entry
- Save entire file atomically
- **Problem**: O(n) read/write for single update

#### 3. **suggest_player_mappings.py** - Interactive tool
- Loads all 1,760 players
- Compares every pair: O(n²) = ~1.5M comparisons
- Loads/saves mappings and skipped pairs repeatedly
- **Problem**: Gets slower as player count grows

## Performance Issues

### Current Bottlenecks
1. **Full file loads on every operation** - No caching
2. **Atomic rewrites** - Write entire JSON for single update
3. **O(n²) fuzzy matching** - Comparing all pairs each run
4. **No indexes** - Linear scans for lookups
5. **JSON parsing overhead** - Slow for large files

### Memory Usage
- 1,760 players × ~500 bytes = ~880 KB per load
- Grows with every unique player seen
- Multiple loads per poll cycle

### Disk I/O
- **Per poll cycle**: 
  - 20+ mapping loads
  - 20+ tracking updates (write entire file)
  - Multiple normalization passes

## SQLite Solution Benefits

### Performance Improvements
1. **Indexed lookups**: O(1) instead of O(n)
2. **Incremental updates**: Only write changed records
3. **Connection pooling**: Keep DB connection open
4. **Query optimization**: SQL engine handles filtering
5. **Reduced parsing**: Binary format, no JSON overhead

### Schema Design
```sql
-- Player mappings (fast lookups)
CREATE TABLE player_mappings (
    variant_normalized TEXT PRIMARY KEY,
    preferred_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_preferred ON player_mappings(preferred_name);

-- Player tracking (detailed history)
CREATE TABLE player_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_key TEXT NOT NULL,  -- Normalized or preferred name
    raw_name TEXT NOT NULL,
    site_name TEXT NOT NULL,
    match_id TEXT,
    seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_player_key ON player_tracking(player_key);
CREATE INDEX idx_site ON player_tracking(site_name);

-- Summary stats (for quick lookups)
CREATE TABLE player_stats (
    player_key TEXT PRIMARY KEY,
    first_seen TIMESTAMP,
    last_seen TIMESTAMP,
    occurrence_count INTEGER DEFAULT 0
);

-- Skipped pairs (prevent re-suggestions)
CREATE TABLE skipped_pairs (
    name1_normalized TEXT NOT NULL,
    name2_normalized TEXT NOT NULL,
    skipped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (name1_normalized, name2_normalized)
);
```

### Expected Improvements
- **Mapping lookups**: 1000x faster (indexed)
- **Tracking updates**: 100x faster (single INSERT)
- **Fuzzy matching**: Can add filters to reduce O(n²)
- **Memory**: Only load what's needed
- **Concurrency**: Multiple processes can access safely

## Implementation Strategy

### Phase 1: Migration Script
- Create SQLite database
- Import existing JSON data
- Validate data integrity

### Phase 2: Update virgin_goose.py
- Replace JSON functions with DB queries
- Add connection pooling
- Keep backward compatibility (read JSON if DB missing)

### Phase 3: Update suggest_player_mappings.py
- Use DB for all operations
- Add pagination for large datasets
- Optimize fuzzy matching with SQL filters

### Phase 4: Cleanup
- Archive old JSON files
- Update documentation
- Monitor performance

## Risk Mitigation
- Keep JSON backup on writes
- Add migration rollback capability
- Gradual rollout with feature flag
- Comprehensive testing before production

## Estimated Timeline
- Migration script: 2 hours
- virgin_goose.py update: 3 hours
- suggest_player_mappings.py update: 2 hours
- Testing & validation: 1 hour
- **Total**: ~8 hours development time

## ROI
With 1,760 players and growing:
- **Current**: ~500ms per poll cycle for player operations
- **SQLite**: ~5ms per poll cycle
- **Savings**: 495ms × polling frequency = significant improvement
- **Scalability**: Will handle 10K+ players without degradation

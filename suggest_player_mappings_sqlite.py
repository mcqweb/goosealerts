#!/usr/bin/env python3
"""
Interactive fuzzy-based player name mapping suggestion tool (SQLite version).
Finds potential player name duplicates and auto-adds approved mappings.
"""

from typing import List, Tuple, Optional, Set, Dict
from difflib import SequenceMatcher
from player_db import get_db
import time
import argparse
from collections import defaultdict

# Prefer rapidfuzz for speed; fall back to difflib.SequenceMatcher on failure
try:
    from rapidfuzz import fuzz
    HAVE_RAPIDFUZZ = True
except Exception:
    HAVE_RAPIDFUZZ = False


def fuzzy_match_score(name1: str, name2: str) -> Tuple[float, List[str]]:
    """
    Calculate fuzzy match score and return matching parts.
    Returns tuple of (score, matching_parts)
    
    Matching logic:
    - 2+ name parts match → strong match
    - Identical surnames → match
    - Overall similarity ratio
    """
    parts1 = set(name1.lower().split())
    parts2 = set(name2.lower().split())
    
    # Remove very short parts (single letters, initials)
    parts1 = {p for p in parts1 if len(p) > 1}
    parts2 = {p for p in parts2 if len(p) > 1}
    
    if not parts1 or not parts2:
        return 0.0, []
    
    # Count matching parts
    matching = sorted(list(parts1 & parts2))
    matches_count = len(matching)
    
    # Calculate match score
    total_parts = len(parts1 | parts2)
    base_score = matches_count / total_parts if total_parts > 0 else 0
    
    # Bonus scoring
    score = base_score
    
    # Strong match: 2+ parts match
    if matches_count >= 2:
        score = max(score, 0.85)
    
    # Strong match: surnames match (last parts)
    last1 = name1.lower().split()[-1] if name1.lower().split() else ""
    last2 = name2.lower().split()[-1] if name2.lower().split() else ""
    if last1 and last2 and last1 == last2 and len(last1) > 2:
        score = max(score, 0.80)
    
    # Similarity ratio fallback
    similarity = SequenceMatcher(None, name1.lower(), name2.lower()).ratio()
    if similarity > 0.75:
        score = max(score, similarity)
    
    return score, matching


def _tokenize_name(name: str) -> Set[str]:
    parts = [p for p in name.lower().split() if len(p) > 1]
    return set(parts)


def _surname(name: str) -> str:
    parts = name.lower().split()
    return parts[-1] if parts else ""


def _score_names(a: str, b: str) -> Tuple[float, List[str]]:
    """Fast scoring using rapidfuzz when available, otherwise SequenceMatcher fallback."""
    # Quick token-based matching parts
    tokens_a = _tokenize_name(a)
    tokens_b = _tokenize_name(b)
    matching = sorted(list(tokens_a & tokens_b))

    if HAVE_RAPIDFUZZ:
        # token_set_ratio is fast and robust for name comparisons
        score_raw = fuzz.token_set_ratio(a, b) / 100.0
        return score_raw, matching
    else:
        score_raw = SequenceMatcher(None, a.lower(), b.lower()).ratio()
        return score_raw, matching


def find_potential_duplicates(score_threshold: float = 0.75, max_candidates_per_name: int = 500) -> List[Tuple[str, str, float, List[str]]]:
    """
    Find potential duplicate/variant player names using database with token-blocking and in-memory caches.

    Improvements:
    - Build token and surname indices to only compare likely candidates (drastically reduces O(n^2)).
    - Preload mappings, skipped pairs, and team sets into memory to avoid per-pair DB calls.
    - Use RapidFuzz when available for fast fuzzy scoring.
    """
    db = get_db()

    start = time.time()

    # Preload players and metadata into memory
    players = db.get_all_players()  # returns dict-like mapping
    player_names = list(players.keys())
    mappings = set(db.get_all_mappings().keys())

    # Preload skipped pairs and teams
    skipped_pairs_db = db.get_all_skipped_pairs() if hasattr(db, 'get_all_skipped_pairs') else set()
    skipped_pairs = {tuple(sorted(p)) for p in skipped_pairs_db}  # normalize ordering

    # Preload teams to avoid DB hits
    teams_cache: Dict[str, Set[str]] = {}
    for name in player_names:
        try:
            teams_cache[name] = set(db.get_player_teams(name) or [])
        except Exception:
            teams_cache[name] = set()

    # Build token index and surname index
    token_index: Dict[str, Set[str]] = defaultdict(set)
    surname_index: Dict[str, Set[str]] = defaultdict(set)

    for name in player_names:
        for tok in _tokenize_name(name):
            token_index[tok].add(name)
        sname = _surname(name)
        if sname:
            surname_index[sname].add(name)

    duplicates: List[Tuple[str, str, float, List[str]]] = []
    seen_pairs = set()

    total_candidates = 0

    for i, name in enumerate(player_names):
        if name in mappings:
            continue

        # Gather candidates via shared tokens and surname
        tokens = _tokenize_name(name)
        candidates = set()
        for t in tokens:
            candidates.update(token_index.get(t, set()))
        s = _surname(name)
        if s:
            candidates.update(surname_index.get(s, set()))

        # Remove self and mapped names
        candidates.discard(name)
        candidates = {c for c in candidates if c not in mappings}

        # Limit candidate explosion for very common tokens
        if len(candidates) > max_candidates_per_name:
            # Keep only those that share at least 2 tokens if too many
            candidates = {c for c in candidates if len(_tokenize_name(c) & tokens) >= 2}

        # Convert to list and cap to reasonable number (deterministic order)
        cand_list = sorted(candidates)
        total_candidates += len(cand_list)

        for cand in cand_list:
            pair = tuple(sorted([name, cand]))
            if pair in seen_pairs or pair in skipped_pairs:
                continue
            seen_pairs.add(pair)

            # Skip if conflicting team data
            teams_a = teams_cache.get(name, set())
            teams_b = teams_cache.get(cand, set())
            if teams_a and teams_b and teams_a != teams_b:
                continue

            score, matching = _score_names(name, cand)
            if score >= score_threshold:
                duplicates.append((name, cand, score, matching))

    duplicates.sort(key=lambda x: x[2], reverse=True)

    elapsed = time.time() - start
    avg_candidates = (total_candidates / len(player_names)) if player_names else 0
    print(f"[PERF] Scanned {len(player_names)} players, total candidate checks={total_candidates}, avg per name={avg_candidates:.2f}, found {len(duplicates)} potential matches in {elapsed:.2f}s")

    return duplicates


def display_player_info(player_name: str) -> None:
    """Display info about a player from database."""
    db = get_db()
    stats = db.get_player_stats(player_name)
    
    if stats:
        count = stats['occurrence_count']
        last_seen = stats['last_seen'][:10] if stats['last_seen'] else 'N/A'  # Just the date
        print(f"  • Occurrences: {count}, Last seen: {last_seen}")
        
        # Show team information if available
        teams = db.get_player_teams(player_name)
        if teams:
            teams_str = ', '.join(sorted(teams))
            print(f"  • Teams: {teams_str}")
    else:
        print(f"  • No statistics available")


def prompt_for_approval(name1: str, name2: str, score: float, matching: List[str]) -> Tuple[Optional[bool], Optional[str]]:
    """
    Prompt user to approve a mapping and choose the preferred name.
    Returns (approved, preferred_name)
    """
    print(f"\n{'='*70}")
    print(f"POTENTIAL MATCH (Score: {score:.2%})")
    print(f"{'='*70}")
    print(f"\n1. {name1}")
    display_player_info(name1)
    print(f"\n2. {name2}")
    display_player_info(name2)
    
    if matching:
        print(f"\nMatching parts: {', '.join(matching)}")
    
    print("\nOptions:")
    print("  [1] Map '{}' → '{}'".format(name2, name1))
    print("  [2] Map '{}' → '{}'".format(name1, name2))
    print("  [s] Skip this pair")
    print("  [q] Quit")
    
    while True:
        choice = input("\nYour choice: ").strip().lower()
        
        if choice == "1":
            return True, name1
        elif choice == "2":
            return True, name2
        elif choice == "s":
            return False, None
        elif choice == "q":
            return None, None  # Special signal to quit
        else:
            print("Invalid choice. Please try again.")


def main():
    """Main interactive mapping suggestion tool."""
    parser = argparse.ArgumentParser(description="Suggest player name mappings (SQLite edition)")
    parser.add_argument('--threshold', '-t', type=float, default=0.75, help='Score threshold for suggestions (0-1)')
    parser.add_argument('--limit', '-l', type=int, default=0, help='Limit number of suggestions to display (0 = all)')
    parser.add_argument('--max-candidates', type=int, default=500, help='Max candidates per name before applying stricter filtering')
    args = parser.parse_args()

    print("\n" + "="*70)
    print("PLAYER NAME MAPPING SUGGESTION TOOL (SQLite Edition)")
    print("="*70)
    print("\nLoading player data from database...")

    db = get_db()
    stats = db.get_stats()

    print(f"Found {stats['player_stats']} unique player names")
    print(f"Loaded {stats['player_mappings']} existing mappings")

    if stats['skipped_pairs'] > 0:
        print(f"Found {stats['skipped_pairs']} previously skipped pairs")

    print("\nSearching for potential duplicates...")
    duplicates = find_potential_duplicates(score_threshold=args.threshold, max_candidates_per_name=args.max_candidates)

    if not duplicates:
        print("\n✓ No potential duplicates found!")
        print("  All player names are unique or already mapped/skipped.")
        return

    if args.limit and args.limit > 0:
        duplicates = duplicates[:args.limit]

    print(f"Found {len(duplicates)} potential matches\n")

    approved_count = 0
    skipped_count = 0

    for idx, (name1, name2, score, matching) in enumerate(duplicates, 1):
        approved, preferred = prompt_for_approval(name1, name2, score, matching)

        if approved is None:
            print("\nQuitting...")
            break

        if approved:
            variant = name2 if preferred == name1 else name1
            db.add_mapping(variant, preferred)
            print(f"✓ Added mapping: '{variant}' → '{preferred}'")
            approved_count += 1
        else:
            db.add_skipped_pair(name1, name2)
            skipped_count += 1

        if idx < len(duplicates):
            remaining = len(duplicates) - idx
            print(f"\n[{idx}/{len(duplicates)}] ({remaining} remaining)")

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Mappings added:  {approved_count}")
    print(f"Pairs skipped:   {skipped_count}")

    if approved_count > 0:
        print("\n✓ Mappings have been saved to database")
        print("  Run migrate_player_db.py export to update JSON files if needed")


if __name__ == "__main__":
    main()

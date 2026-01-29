#!/usr/bin/env python3
"""
Interactive fuzzy-based player name mapping suggestion tool (SQLite version).
Finds potential player name duplicates and auto-adds approved mappings.
"""

from typing import List, Tuple, Optional
from difflib import SequenceMatcher
from player_db import get_db


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


def find_potential_duplicates(score_threshold: float = 0.75) -> List[Tuple[str, str, float, List[str]]]:
    """
    Find potential duplicate/variant player names using database.
    Excludes pairs that have conflicting team data (different teams = different players).
    Returns list of (name1, name2, score, matching_parts) tuples.
    """
    db = get_db()
    
    # Get all players (already normalized keys)
    players = db.get_all_players()
    player_names = list(players.keys())
    
    # Get existing mappings and skipped pairs to filter
    mappings = db.get_all_mappings()
    
    duplicates = []
    seen_pairs = set()
    
    for i, name1 in enumerate(player_names):
        # Skip if name1 is already mapped
        if name1 in mappings:
            continue
        
        for name2 in player_names[i+1:]:
            if name1 == name2:
                continue
            
            # Skip if name2 is already mapped
            if name2 in mappings:
                continue
            
            # Skip if pair was already seen
            pair_key = tuple(sorted([name1, name2]))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)
            
            # Skip if pair was previously skipped
            if db.is_pair_skipped(name1, name2):
                continue
            
            # **NEW: Skip if players have conflicting team data**
            if db.have_conflicting_teams(name1, name2):
                continue
            
            score, matching = fuzzy_match_score(name1, name2)
            
            # Only include strong matches
            if score >= score_threshold:
                duplicates.append((name1, name2, score, matching))
    
    # Sort by score descending
    duplicates.sort(key=lambda x: x[2], reverse=True)
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
    duplicates = find_potential_duplicates(score_threshold=0.75)
    
    if not duplicates:
        print("\n✓ No potential duplicates found!")
        print("  All player names are unique or already mapped/skipped.")
        return
    
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

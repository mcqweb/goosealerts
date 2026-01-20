#!/usr/bin/env python3
"""
Interactive fuzzy-based player name mapping suggestion tool.
Finds potential player name duplicates and auto-adds approved mappings.
"""

import json
from pathlib import Path
from typing import Set, Tuple, List
from difflib import SequenceMatcher


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


def load_player_names() -> dict:
    """Load all tracked player names from the tracking file."""
    tracking_file = Path("data/player_name_tracking.json")
    if not tracking_file.exists():
        print(f"Error: {tracking_file} not found")
        return {}
    
    with open(tracking_file) as f:
        data = json.load(f)
    
    return data


def load_existing_mappings() -> dict:
    """Load existing player name mappings."""
    mappings_file = Path("player_name_mappings.json")
    if not mappings_file.exists():
        return {"__alias__": "prefered name"}
    
    with open(mappings_file) as f:
        return json.load(f)


def find_potential_duplicates(players: dict, score_threshold: float = 0.75) -> List[Tuple[str, str, float, List[str]]]:
    """
    Find potential duplicate/variant player names.
    Returns list of (name1, name2, score, matching_parts) tuples.
    """
    player_names = list(players.keys())
    duplicates = []
    seen_pairs = set()
    
    for i, name1 in enumerate(player_names):
        for name2 in player_names[i+1:]:
            if name1 == name2:
                continue
            
            # Skip if already seen (in reverse order)
            pair_key = tuple(sorted([name1, name2]))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)
            
            score, matching = fuzzy_match_score(name1, name2)
            
            # Only include strong matches
            if score >= score_threshold:
                duplicates.append((name1, name2, score, matching))
    
    # Sort by score descending
    duplicates.sort(key=lambda x: x[2], reverse=True)
    return duplicates


def display_player_info(player_name: str, players: dict) -> None:
    """Display info about a player."""
    player = players.get(player_name, {})
    count = player.get("occurrence_count", 0)
    last_seen = player.get("last_seen", "N/A")
    print(f"  • Occurrences: {count}, Last seen: {last_seen}")


def prompt_for_approval(name1: str, name2: str, score: float, matching: List[str], 
                        players: dict) -> Tuple[bool, str]:
    """
    Prompt user to approve a mapping and choose the preferred name.
    Returns (approved, preferred_name)
    """
    print(f"\n{'='*70}")
    print(f"POTENTIAL MATCH (Score: {score:.2%})")
    print(f"{'='*70}")
    print(f"\n1. {name1}")
    display_player_info(name1, players)
    print(f"\n2. {name2}")
    display_player_info(name2, players)
    
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


def add_mapping(mappings: dict, variant: str, preferred: str) -> None:
    """Add or update a mapping in the mappings dict."""
    mappings[variant.lower()] = preferred.lower()
    print(f"✓ Added mapping: '{variant}' → '{preferred}'")


def save_mappings(mappings: dict) -> None:
    """Save updated mappings to file."""
    mappings_file = Path("player_name_mappings.json")
    with open(mappings_file, 'w') as f:
        json.dump(mappings, f, indent=2)
    print(f"\n✓ Mappings saved to {mappings_file}")


def main():
    """Main interactive mapping suggestion tool."""
    print("\n" + "="*70)
    print("PLAYER NAME MAPPING SUGGESTION TOOL")
    print("="*70)
    print("\nLoading player data...")
    
    players = load_player_names()
    if not players:
        print("No player data found.")
        return
    
    print(f"Found {len(players)} unique player names\n")
    
    mappings = load_existing_mappings()
    existing_mappings_count = len(mappings) - 1  # Exclude __alias__
    print(f"Loaded {existing_mappings_count} existing mappings")
    
    print("\nSearching for potential duplicates...")
    duplicates = find_potential_duplicates(players, score_threshold=0.75)
    
    if not duplicates:
        print("\nNo potential duplicates found.")
        return
    
    print(f"Found {len(duplicates)} potential matches\n")
    
    approved_count = 0
    skipped_count = 0
    
    for idx, (name1, name2, score, matching) in enumerate(duplicates, 1):
        # Check if either name is already a source in an existing mapping
        if name1.lower() in mappings or name2.lower() in mappings:
            print(f"\n[{idx}/{len(duplicates)}] Skipping (already mapped)")
            continue
        
        approved, preferred = prompt_for_approval(name1, name2, score, matching, players)
        
        if approved is None:
            print("\nQuitting...")
            break
        
        if approved:
            variant = name2 if preferred == name1 else name1
            add_mapping(mappings, variant, preferred)
            approved_count += 1
        else:
            skipped_count += 1
        
        if idx < len(duplicates):
            print(f"\n[{idx}/{len(duplicates)}]")
    
    # Save if any changes were made
    if approved_count > 0:
        save_mappings(mappings)
        print(f"\nSummary: {approved_count} mappings added, {skipped_count} skipped")
    else:
        print(f"\nNo mappings were added.")


if __name__ == "__main__":
    main()

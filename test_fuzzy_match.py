"""
Test fuzzy name matching logic
"""

def fuzzy_match_names(name1: str, name2: str) -> bool:
    """
    Check if two player names are a fuzzy match.
    Returns True if at least 2 out of 3 name parts match.
    """
    # Normalize: lowercase and split into parts
    parts1 = set(name1.lower().split())
    parts2 = set(name2.lower().split())
    
    # Remove very short parts (initials, etc.) that might cause false matches
    parts1 = {p for p in parts1 if len(p) > 1}
    parts2 = {p for p in parts2 if len(p) > 1}
    
    if not parts1 or not parts2:
        return False
    
    # Count matching parts
    matches = len(parts1 & parts2)
    
    # Calculate total unique parts (union)
    total_parts = len(parts1 | parts2)
    
    if total_parts == 0:
        return False
    
    # Need at least 2 matching parts, OR >50% match rate for shorter names
    if matches >= 2:
        return True
    
    # For shorter names (2 parts total), require at least 50% match
    match_rate = matches / total_parts
    return match_rate >= 0.5


# Test cases
test_cases = [
    ("Junior Kroupi", "Eli Junior Kroupi", True),  # 2/3 match
    ("Benjamin Sesko", "Benjamin Sesko", True),    # Exact match
    ("Benjamin Sesko", "Ben Sesko", True),         # 1/2 = 50%
    ("Bruno Fernandes", "Bruno", True),            # 1/1 = 100%
    ("John Smith", "Jane Doe", False),             # 0/4 = 0%
    ("Mohamed Salah", "Mo Salah", True),           # 1/2 = 50%
]

print("Fuzzy Name Matching Tests:")
print("-" * 60)
for name1, name2, expected in test_cases:
    result = fuzzy_match_names(name1, name2)
    status = "✓" if result == expected else "✗"
    print(f"{status} '{name1}' vs '{name2}': {result} (expected {expected})")

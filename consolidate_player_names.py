#!/usr/bin/env python3
"""
Utility to consolidate player name tracking data based on manual mappings.

Run this after adding entries to player_name_mappings.json to merge tracking
entries that map to the same preferred name.

Example:
    python consolidate_player_names.py
"""

import sys
import os

# Add parent directory to path to import virgin_goose
sys.path.insert(0, os.path.dirname(__file__))

from virgin_goose import consolidate_player_tracking

if __name__ == '__main__':
    print("=" * 60)
    print("Player Name Tracking Consolidation")
    print("=" * 60)
    print()
    
    result = consolidate_player_tracking()
    
    print()
    print("=" * 60)
    print(f"Consolidation Complete!")
    print(f"  - Merged {result['merged_count']} duplicate entries")
    print(f"  - Total entries: {result['total_entries']}")
    print("=" * 60)

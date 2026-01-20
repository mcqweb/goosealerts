#!/usr/bin/env python3
"""
Quick startup demo for Kwiff integration.

This demonstrates the recommended pattern for integrating Kwiff
into the main goosealerts workflow.

Run:
    python demo_kwiff_startup.py
"""

import os
import sys
from pathlib import Path

# Ensure we're in the right directory
os.chdir(Path(__file__).parent)

print("\n" + "="*80)
print(" "*20 + "KWIFF INTEGRATION STARTUP DEMO")
print("="*80 + "\n")

# Step 1: Import the integration function
print("[1/3] Importing Kwiff integration...")
try:
    from kwiff import initialize_kwiff_sync, get_kwiff_event_mappings
    print("✅ Import successful\n")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    print("\nMake sure the kwiff module is in the same directory.")
    sys.exit(1)

# Step 2: Initialize Kwiff (fetch and map events)
print("[2/3] Initializing Kwiff integration...")
print("      (This fetches events and maps them to Betfair)\n")

try:
    result = initialize_kwiff_sync(country="GB", dry_run=False)
    
    if result['overall_success']:
        print("\n✅ Kwiff integration successful!")
    else:
        print("\n⚠️ Kwiff integration had issues:")
        print(f"   - Fetch: {'✅' if result['fetch_success'] else '❌'}")
        print(f"   - Mapping: {'✅' if result['mapping_success'] else '❌'}")
        
except Exception as e:
    print(f"\n❌ Initialization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 3: Verify mappings are available
print("\n[3/3] Verifying event mappings...")

try:
    mappings = get_kwiff_event_mappings()
    
    print(f"\n✅ {len(mappings)} event mappings available\n")
    
    if mappings:
        print("Sample mappings:")
        for i, (kwiff_id, data) in enumerate(list(mappings.items())[:5], 1):
            betfair_id = data.get('betfair_id', 'N/A')
            desc = data.get('description', 'No description')
            
            # Truncate long descriptions
            if len(desc) > 70:
                desc = desc[:67] + "..."
            
            status = "✅" if betfair_id and betfair_id != "TODO" else "⚠️"
            print(f"  {status} {i}. Kwiff {kwiff_id} → Betfair {betfair_id}")
            print(f"       {desc}")
        
        if len(mappings) > 5:
            print(f"\n  ... and {len(mappings) - 5} more")
    
except Exception as e:
    print(f"❌ Verification failed: {e}")
    sys.exit(1)

# Summary
print("\n" + "="*80)
print("STARTUP COMPLETE - Kwiff is ready to use!")
print("="*80)
print("\n📌 Next steps:")
print("   1. Use this pattern in virgin_goose.py main() function")
print("   2. Call get_betfair_id_for_kwiff_event() to lookup Betfair IDs")
print("   3. Implement WebSocket commands to request player odds (future)")
print("\n📖 Full documentation: KWIFF_INTEGRATION_GUIDE.md")
print("💡 Example code: kwiff_integration_example.py\n")

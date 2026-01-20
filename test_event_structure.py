import asyncio
import json
from kwiff import KwiffClient

async def main():
    async with KwiffClient() as client:
        # Try a current event
        details = await client.get_event_details(10748848)
        
        if details:
            # Save it
            with open("current_event_sample.json", "w") as f:
                json.dump(details, f, indent=2)
            
            print("Saved to current_event_sample.json")
            
            # Show first part
            print("\nStructure:")
            print(json.dumps(details, indent=2)[:1500])
        else:
            print("No data received")

asyncio.run(main())

#!/usr/bin/env python3
"""
Kwiff WebSocket Client - Fetch Live Football Events

This module provides a standalone Python implementation to connect to Kwiff's
WebSocket API and fetch live football event data without requiring a browser.

Key Discovery:
- Must use: from websockets.client import connect (lower-level API)
- Must pass: extra_headers parameter with list of tuples
- Connection receives: handshake (0), user details (42), namespace (40)
- Command format: 421<packet_id>["command",{...}]
- Response format: 43<packet_id>[{...}]

Usage:
    python -m kwiff.kwiff_client fetch-events --sport football --country GB
    
Or import directly:
    from kwiff_client import KwiffClient
    async with KwiffClient() as client:
        events = await client.get_football_events()
"""

import asyncio
import json
import time
import uuid
from typing import Dict, List, Any, Optional
from pathlib import Path


class KwiffClient:
    """
    WebSocket client for Kwiff betting exchange.
    
    Handles:
    - WebSocket connection with proper authentication headers
    - Socket.IO protocol (EIO=3)
    - Command sending and response parsing
    - Event data retrieval
    """
    
    BASE_URL = "wss://web-api.kwiff.com/socket.io/"
    
    # User Agent to match browser
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
    WEBAPP_VERSION = "1.0.1.1768909734556"
    
    def __init__(self, identifier: Optional[str] = None):
        """Initialize Kwiff client with optional custom identifier."""
        self.identifier = identifier or str(uuid.uuid4())
        self.ws = None
        self.packet_id = 0
        
    def _get_connection_url(self) -> str:
        """Build WebSocket connection URL."""
        return (
            f"{self.BASE_URL}?"
            f"device=web-app&"
            f"version=1.0.1&"
            f"identifier={self.identifier}&"
            f"EIO=3&"
            f"transport=websocket"
        )
    
    def _get_headers(self) -> List[tuple]:
        """Build required HTTP headers for authentication."""
        return [
            ("User-Agent", self.USER_AGENT),
            ("Origin", "https://kwiff.com"),
            ("Sec-WebSocket-Extensions", "permessage-deflate; client_max_window_bits"),
            ("Pragma", "no-cache"),
            ("Cache-Control", "no-cache"),
            ("Accept-Encoding", "gzip, deflate, br, zstd"),
            ("Accept-Language", "en-GB,en-US;q=0.9,en;q=0.8"),
            ("Cookie", f"uuid={self.identifier}"),
        ]
    
    async def connect(self) -> bool:
        """
        Establish WebSocket connection and complete handshake.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            from websockets.client import connect
        except ImportError:
            print("[ERROR] websockets library not installed")
            print("  Install with: pip install websockets")
            return False
        
        try:
            self.ws = await connect(
                self._get_connection_url(),
                extra_headers=self._get_headers()
            )
            
            # Receive handshake and initial messages
            for i in range(5):
                try:
                    msg = await asyncio.wait_for(self.ws.recv(), timeout=2.0)
                    
                    if msg == "40":  # Namespace connected
                        return True
                    
                except asyncio.TimeoutError:
                    break
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Connection failed: {e}")
            return False
    
    async def disconnect(self):
        """Close WebSocket connection."""
        if self.ws:
            await self.ws.close()
            self.ws = None
    
    async def send_command(self, message: str, payload: Dict[str, Any]) -> Optional[Dict]:
        """
        Send a command to Kwiff and wait for response.
        
        Args:
            message: Command name (e.g., 'event:list')
            payload: Command payload data
            
        Returns:
            Response data or None if no response received
        """
        if not self.ws:
            return None
        
        self.packet_id += 1
        timestamp = int(time.time() * 1000)
        
        # Build command data
        command_data = {
            "message": message,
            "payload": payload,
            "timestamp": timestamp,
            "userAgent": self.USER_AGENT,
            "webappVersion": self.WEBAPP_VERSION
        }
        
        # Format: 421<packet_id>["command",{...}]
        command_msg = f"421{self.packet_id}[\"command\",{json.dumps(command_data)}]"
        
        try:
            await self.ws.send(command_msg)
            
            # Wait for response
            for _ in range(10):
                try:
                    msg = await asyncio.wait_for(self.ws.recv(), timeout=2.0)
                    
                    if msg.startswith("43"):
                        # Extract JSON from response format 43<packet_id>[...]
                        json_start = msg.find('[')
                        if json_start > -1:
                            json_part = msg[json_start:]
                            return json.loads(json_part)
                    
                except asyncio.TimeoutError:
                    break
            
            return None
            
        except Exception as e:
            print(f"[ERROR] Command send failed: {e}")
            return None
    
    async def get_football_events(self, country: str = "GB") -> Optional[Dict]:
        """
        Fetch football events for specified country.
        
        Args:
            country: Country code (default: 'GB')
            
        Returns:
            Event data or None if request failed
        """
        payload = {
            "listId": "default",
            "sportId": 11,  # Football
            "country": country
        }
        
        response = await self.send_command("event:list", payload)
        
        if response and isinstance(response, list) and len(response) > 0:
            return response[0]  # First item contains the data
        
        return response
    
    async def __aenter__(self):
        """Async context manager entry."""
        if await self.connect():
            return self
        raise RuntimeError("Failed to connect to Kwiff")
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()


async def main():
    """Example usage."""
    print("[*] Kwiff WebSocket Client\n")
    
    try:
        async with KwiffClient() as client:
            print("[+] Connected to Kwiff!\n")
            
            print("[*] Fetching football events for GB...\n")
            events = await client.get_football_events(country="GB")
            
            if events:
                print(f"[+] Received events data")
                
                # Save to file
                output_file = Path("football_events.json")
                with open(output_file, "w") as f:
                    json.dump(events, f, indent=2)
                print(f"[+] Saved to {output_file}")
                
                # Show preview
                if "data" in events and "events" in events["data"]:
                    event_list = events["data"]["events"]
                    print(f"\n[*] Found {len(event_list)} events")
                    
                    for i, event in enumerate(event_list[:3]):
                        print(f"\n  Event {i+1}:")
                        print(f"    ID: {event.get('id')}")
                        print(f"    Competition: {event.get('competition', {}).get('name')}")
                        
                        home = event.get('homeTeam', {}).get('name', 'N/A')
                        away = event.get('awayTeam', {}).get('name', 'N/A')
                        print(f"    Match: {home} vs {away}")
                        
                        start_date = event.get('startDate', 'N/A')
                        print(f"    Start: {start_date}")
            else:
                print("[!] No events received")
                
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

"""
Generate Bet Builder Combinations
Creates the 4 standard bet builder combinations for eligible players
"""

from typing import Dict, List, Optional
import requests
import sys
import time
import json
import os
from pathlib import Path
from src.bet_builder_templates import BetBuilderTemplates, PlayerMarketChecker

# Add parent directory to path for config import
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import Config


class BetBuilderGenerator:
    """Generate bet builder combinations with selection IDs ready for pricing API"""
    
    @staticmethod
    def _fuzzy_match_names(name1: str, name2: str) -> bool:
        """
        Check if two player names are a fuzzy match.
        Returns True if at least 2 out of 3 name parts match.
        
        Examples:
            'Junior Kroupi' vs 'Eli Junior Kroupi' -> True (2/3 match)
            'Benjamin Sesko' vs 'Ben Sesko' -> True (1/2 match, 50%+)
            'John Smith' vs 'Jane Doe' -> False (0/2 match)
        
        Args:
            name1: First name to compare
            name2: Second name to compare
            
        Returns:
            True if names match closely enough
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
    
    def __init__(self, parser):
        """
        Initialize with a MarketParser instance
        
        Args:
            parser: MarketParser instance with loaded market data
        """
        self.parser = parser
        self.checker = PlayerMarketChecker(parser)
        
        # Cache configuration for price responses
        self.WH_PRICE_CACHE_DURATION = 300  # 5 minutes in seconds
        self.cache_dir = Path(__file__).parent.parent / 'cache' / 'prices'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_event_id(self) -> str:
        """
        Extract the event ID from the market data
        
        Returns:
            Event ID string
        """
        return self.parser.data.get("id", "")
    
    def create_pricing_payload(self, combo: Dict) -> Dict:
        """
        Create the payload for the pricing API from a combination
        
        Args:
            combo: Combination dictionary from generate_combo_for_player
            
        Returns:
            Dictionary formatted for pricing API POST request
        """
        if not combo.get("success"):
            return None
        
        event_id = self.get_event_id()
        
        payload = {
            "eventID": event_id,
            "selections": [
                {
                    "selectionId": sel_id,
                    "handicap": None
                }
                for sel_id in combo["selectionIds"]
            ],
            "combinationIdCheckValue": ""
        }
        
        return payload
    
    def get_combo_price(self, combo: Dict, session_cookie: Optional[str] = None, proxies: Optional[Dict] = None) -> Optional[Dict]:
        """
        Get the price for a combination from William Hill pricing API
        
        Args:
            combo: Combination dictionary from generate_combo_for_player
            session_cookie: SESSION cookie value for authentication (defaults to Config.SESSION_COOKIE)
            proxies: Proxy configuration dict (defaults to Config.get_proxies())
            
        Returns:
            API response as dictionary, or None if request fails
        """
        payload = self.create_pricing_payload(combo)
        if not payload:
            return None
        
        # Generate cache key from payload selections
        selection_ids = sorted([s['selectionId'] for s in payload.get('selections', [])])
        cache_key = '_'.join(selection_ids)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        # Try to load from cache
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached = json.load(f)
                ts = float(cached.get('ts', 0))
                if time.time() - ts <= self.WH_PRICE_CACHE_DURATION:
                    # Cache is still valid
                    return cached.get('response')
            except Exception:
                pass  # If cache read fails, continue to API request
        
        # Use config values if not provided
        cookie = session_cookie or Config.SESSION_COOKIE
        proxy_config = proxies if proxies is not None else Config.get_proxies()
        
        cookies = {
            "SESSION": cookie
        }
        
        try:
            response = requests.post(
                Config.WILLIAMHILL_PRICING_API,
                json=payload,
                headers=Config.API_HEADERS,
                cookies=cookies,
                proxies=proxy_config,
                timeout=Config.API_TIMEOUT
            )
            response.raise_for_status()
            response_data = response.json()
            
            # Save to cache
            try:
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump({'ts': time.time(), 'response': response_data}, f)
            except Exception:
                pass  # Cache write failure shouldn't break the flow
            
            return response_data
        except requests.exceptions.RequestException as e:
            print(f"Error fetching price: {e}")
            return None
    
    def _get_selection_id(self, category: str, period: str, team: str, selection_name: str) -> str:
        """
        Get the selection ID for a specific selection
        
        Args:
            category: Market category
            period: Market period
            team: Team name (or empty string)
            selection_name: Selection name (e.g., "Over 0.5" or player name)
            
        Returns:
            Selection ID string or None if not found
        """
        selections = self.parser.get_selections_for_market(category, period, team)
        
        for selection in selections:
            sel_name = selection.get("name")
            # Try exact match first
            if sel_name == selection_name:
                return selection.get("id")
        
        # If no exact match and this looks like a player market, try fuzzy matching
        # Player markets typically have category containing "PLAYER"
        if "PLAYER" in category:
            for selection in selections:
                sel_name = selection.get("name")
                if self._fuzzy_match_names(sel_name, selection_name):
                    return selection.get("id")
        
        return None
    
    def generate_combo_for_player(self, player_name: str, team: str, template_name: str) -> Dict:
        """
        Generate a bet builder combination for a specific player and template
        
        Args:
            player_name: Player name
            team: Team name
            template_name: Name of the bet builder template
            
        Returns:
            Dictionary with combination details and selection IDs
        """
        # Check if player is eligible
        availability = self.checker.check_player_availability(player_name, team, template_name)
        
        if not availability["available"]:
            return {
                "success": False,
                "error": "Player not available for this template",
                "missing_markets": availability["missing_markets"]
            }
        
        # Get template definition
        template = BetBuilderTemplates.get_template(template_name)
        
        # Build the combination with OB IDs
        selections = []
        
        for market_def in template:
            category = market_def["category"]
            period = market_def["period"]
            market_team = market_def.get("team", "").replace("{team}", team)
            selection_type = market_def["selection_type"]
            
            # Replace player placeholder if present
            if "{player}" in selection_type:
                selection_name = player_name
            else:
                selection_name = selection_type
            
            # Get selection ID
            selection_id = self._get_selection_id(category, period, market_team, selection_name)
            
            if not selection_id:
                return {
                    "success": False,
                    "error": f"Could not find selection ID for {category} > {market_team} > {period} > {selection_name}"
                }
            
            selections.append({
                "category": category,
                "team": market_team,
                "period": period,
                "selection": selection_name,
                "selectionId": selection_id
            })
        
        return {
            "success": True,
            "template": template_name,
            "player": player_name,
            "team": team,
            "selection_count": len(selections),
            "selections": selections,
            "selectionIds": [s["selectionId"] for s in selections]
        }
    
    def generate_all_combos_for_player(self, player_name: str, team: str) -> List[Dict]:
        """
        Generate all available bet builder combinations for a player
        
        Args:
            player_name: Player name
            team: Team name
            
        Returns:
            List of combination dictionaries
        """
        combos = []
        
        for template_name in BetBuilderTemplates.get_all_template_names():
            combo = self.generate_combo_for_player(player_name, team, template_name)
            if combo.get("success"):
                combos.append(combo)
        
        return combos
    
    def generate_all_combos_for_event(self) -> Dict[str, List[Dict]]:
        """
        Generate all bet builder combinations for all eligible players in the event
        
        Returns:
            Dictionary organized by template: {template_name: [combo_list]}
        """
        # Get all eligible players
        eligible_players = self.checker.get_all_eligible_players()
        
        results = {}
        
        for template_name, teams_data in eligible_players.items():
            results[template_name] = []
            
            for team, players in teams_data.items():
                for player_info in players:
                    combo = self.generate_combo_for_player(
                        player_info["name"],
                        team,
                        template_name
                    )
                    
                    if combo.get("success"):
                        results[template_name].append(combo)
        
        return results
    
    def format_combo_output(self, combo: Dict, include_payload: bool = True, price_data: Optional[Dict] = None) -> str:
        """
        Format a combination for display
        
        Args:
            combo: Combination dictionary
            include_payload: Whether to include pricing API payload
            price_data: Optional pricing data from API
        """
        if not combo.get("success"):
            return f"❌ Error: {combo.get('error')}"
        
        lines = [
            f"\n{'=' * 70}",
            f"Template: {combo['template']}",
            f"Player: {combo['player']} ({combo['team']})",
            f"Selections: {combo['selection_count']}",
        ]
        
        # Add odds if available
        if price_data and price_data.get("status") == "ok":
            price = price_data.get("selection", {}).get("price", {})
            decimal = price.get("decimal")
            fractional = f"{price.get('numerator')}/{price.get('denominator')}"
            lines.append(f"Odds: {decimal} ({fractional})")
        
        lines.append(f"{'-' * 70}")
        
        for i, sel in enumerate(combo['selections'], 1):
            team_part = f" > {sel['team']}" if sel['team'] else ""
            lines.append(f"  {i}. {sel['category']}{team_part} > {sel['period']}")
            lines.append(f"     Selection: {sel['selection']}")
            lines.append(f"     Selection ID: {sel['selectionId']}")
        
        lines.append(f"\nSelection IDs for Pricing API:")
        lines.append(f"  {combo['selectionIds']}")
        
        if include_payload:
            import json
            payload = self.create_pricing_payload(combo)
            lines.append(f"\nPricing API Payload:")
            lines.append(f"  {json.dumps(payload, indent=2)}")
        
        lines.append(f"{'=' * 70}\n")
        
        return "\n".join(lines)
    
    def get_summary_stats(self) -> Dict:
        """Get summary statistics of available combinations"""
        all_combos = self.generate_all_combos_for_event()
        
        stats = {
            "total_combinations": sum(len(combos) for combos in all_combos.values()),
            "by_template": {},
            "by_team": {}
        }
        
        for template_name, combos in all_combos.items():
            stats["by_template"][template_name] = len(combos)
            
            for combo in combos:
                team = combo["team"]
                if team not in stats["by_team"]:
                    stats["by_team"][team] = 0
                stats["by_team"][team] += 1
        
        return stats

"""
Bet Builder Templates for William Hill
Defines the 4 standard bet builder combinations with their market paths
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import re


def _normalize_name_tokens(name: str) -> set:
    """Normalize a name into a set of comparable tokens.

    Reorders "Last, First" strings and strips punctuation so WH player
    names like "Archibald, Theo" match "Theo Archibald".
    """
    if not name:
        return set()

    cleaned = str(name)

    if "," in cleaned:
        parts = [p.strip() for p in cleaned.split(",") if p.strip()]
        if len(parts) >= 2:
            cleaned = " ".join(parts[1:] + [parts[0]])

    cleaned = re.sub(r"[^\w\s\-]", " ", cleaned.lower())
    tokens = set(re.split(r"[\s\-]+", cleaned))
    return {t for t in tokens if len(t) > 1}


def _fuzzy_match_names(name1: str, name2: str) -> bool:
    """
    Check if two player names are a fuzzy match after normalization.
    Returns True if at least 2 matching parts or a 50%+ overlap exists.
    """
    parts1 = _normalize_name_tokens(name1)
    parts2 = _normalize_name_tokens(name2)
    
    if not parts1 or not parts2:
        return False
    
    matches = len(parts1 & parts2)
    total_parts = len(parts1 | parts2)
    
    if total_parts == 0:
        return False
    
    if matches >= 2:
        return True
    
    match_rate = matches / total_parts
    return match_rate >= 0.5


@dataclass
class MarketPath:
    """Represents a path to a specific market selection"""
    category: str
    team: Optional[str]
    period: str
    selection_type: str  # e.g., "Over 0.5", "player_name", etc.
    
    def __str__(self):
        if self.team:
            return f"{self.category} > {self.team} > {self.period} > {self.selection_type}"
        return f"{self.category} > {self.period} > {self.selection_type}"


class BetBuilderTemplates:
    """
    Defines the 4 standard bet builder combinations:
    1. Anytime Goalscorer
    2. First Goalscorer
    3. Score 2 or More
    4. Score a Hattrick
    """
    
    # Template definitions with their market paths
    TEMPLATES = {
        "Anytime Goalscorer": [
            {
                "category": "Total Goals",
                "team": "Both Teams Combined",
                "period": "90 Minutes",
                "selection_type": "Over 0.5"
            },
            {
                "category": "Player to Score",
                "team": "{team}",  # Will be replaced with actual team
                "period": "Anytime",
                "selection_type": "{player}"  # Will be replaced with actual player
            },
            {
                "category": "Player to Score or Assist",
                "team": "{team}",
                "period": "Anytime",
                "selection_type": "{player}"
            }
        ],
        
        "First Goalscorer": [
            {
                "category": "Total Goals",
                "team": "Both Teams Combined",
                "period": "90 Minutes",
                "selection_type": "Over 0.5"
            },
            {
                "category": "Player to Score",
                "team": "{team}",
                "period": "First",
                "selection_type": "{player}"
            },
            {
                "category": "Player to Score",
                "team": "{team}",
                "period": "Anytime",
                "selection_type": "{player}"
            }
        ],
        
        "Score 2 or More": [
            {
                "category": "Total Goals",
                "team": "Both Teams Combined",
                "period": "90 Minutes",
                "selection_type": "Over 1.5"
            },
            {
                "category": "Player to Score",
                "team": "{team}",
                "period": "Two or More",
                "selection_type": "{player}"
            },
            {
                "category": "Player to Score",
                "team": "{team}",
                "period": "Anytime",
                "selection_type": "{player}"
            }
        ],
        
        "Score a Hattrick": [
            {
                "category": "Total Goals",
                "team": "Both Teams Combined",
                "period": "90 Minutes",
                "selection_type": "Over 1.5"
            },
            {
                "category": "Player to Score",
                "team": "{team}",
                "period": "Hat-trick",
                "selection_type": "{player}"
            },
            {
                "category": "Player to Score",
                "team": "{team}",
                "period": "Anytime",
                "selection_type": "{player}"
            }
        ]
    }
    
    @classmethod
    def get_template(cls, template_name: str) -> List[Dict]:
        """Get a template by name"""
        return cls.TEMPLATES.get(template_name)
    
    @classmethod
    def get_all_template_names(cls) -> List[str]:
        """Get all available template names"""
        return list(cls.TEMPLATES.keys())
    
    @classmethod
    def get_required_markets_for_player(cls, template_name: str) -> List[Dict]:
        """
        Get the required player markets for a template.
        Returns only the markets that need a specific player.
        """
        template = cls.get_template(template_name)
        if not template:
            return []
        
        # Filter for markets that use {player} placeholder
        return [m for m in template if "{player}" in m.get("selection_type", "")]
    
    @classmethod
    def format_template_info(cls) -> str:
        """Return formatted information about all templates"""
        lines = ["Available Bet Builder Templates:", "=" * 50]
        
        for name, markets in cls.TEMPLATES.items():
            lines.append(f"\n{name}:")
            lines.append("-" * 40)
            for i, market in enumerate(markets, 1):
                team_part = f" > {market['team']}" if market.get('team') else ""
                lines.append(f"  {i}. {market['category']}{team_part} > {market['period']} > {market['selection_type']}")
        
        return "\n".join(lines)


class PlayerMarketChecker:
    """Check which players have all required markets for each template"""
    
    def __init__(self, parser):
        """
        Initialize with a MarketParser instance
        
        Args:
            parser: MarketParser instance with loaded market data
        """
        self.parser = parser
    
    def get_player_list(self, team: str, category: str = "Player to Score", period: str = "Anytime") -> List[Dict]:
        """
        Get list of all players available in a specific market
        
        Args:
            team: Team name (e.g., "Man Utd", "Bournemouth")
            category: Market category
            period: Market period
            
        Returns:
            List of player dictionaries with 'name', 'id', 'obId'
        """
        selections = self.parser.get_selections_for_market(category, period, team)
        return selections if selections else []
    
    def check_player_availability(self, player_name: str, team: str, template_name: str) -> Dict:
        """
        Check if a player has all required markets for a specific template
        
        Args:
            player_name: Player name
            team: Team name
            template_name: Name of the bet builder template
            
        Returns:
            Dictionary with availability status and missing markets
        """
        template = BetBuilderTemplates.get_template(template_name)
        if not template:
            return {"available": False, "error": f"Template '{template_name}' not found"}
        
        available_markets = []
        missing_markets = []
        matched_player_name = player_name  # Track the actual matched name in WH's system
        
        for market_def in template:
            category = market_def["category"]
            period = market_def["period"]
            market_team = market_def.get("team", "").replace("{team}", team)
            selection_type = market_def["selection_type"]
            
            # Skip player-specific markets check if it's not a player market
            if "{player}" not in selection_type:
                # Check if the fixed selection exists (e.g., "Over 0.5")
                selections = self.parser.get_selections_for_market(category, period, market_team)
                found = any(selection_type in sel.get("name", "") for sel in selections)
                
                if found:
                    available_markets.append({
                        "category": category,
                        "team": market_team,
                        "period": period,
                        "selection": selection_type
                    })
                else:
                    missing_markets.append({
                        "category": category,
                        "team": market_team,
                        "period": period,
                        "selection": selection_type
                    })
            else:
                # Check if player exists in this market (use fuzzy matching)
                selections = self.parser.get_selections_for_market(category, period, market_team)
                
                # Try exact match first
                player_selection = next((s for s in selections if s.get("name") == player_name), None)
                
                # If no exact match, try fuzzy matching
                if not player_selection:
                    player_selection = next((s for s in selections if _fuzzy_match_names(s.get("name", ""), player_name)), None)
                    if player_selection:
                        # Update to use WH's actual player name
                        matched_player_name = player_selection.get("name")
                        # Log when fuzzy match is used
                        print(f"[WH FUZZY] Matched '{player_name}' to WH player '{matched_player_name}' in {category}")
                
                if player_selection:
                    available_markets.append({
                        "category": category,
                        "team": market_team,
                        "period": period,
                        "player": player_name,
                        "selectionId": player_selection.get("id"),
                        "id": player_selection.get("id")
                    })
                else:
                    missing_markets.append({
                        "category": category,
                        "team": market_team,
                        "period": period,
                        "player": player_name
                    })
        
        return {
            "available": len(missing_markets) == 0,
            "template": template_name,
            "player": player_name,
            "matched_player_name": matched_player_name,  # The actual name used in WH's system
            "team": team,
            "available_markets": available_markets,
            "missing_markets": missing_markets
        }
    
    def get_eligible_players_for_template(self, team: str, template_name: str) -> List[Dict]:
        """
        Get all players who have all required markets for a template
        
        Args:
            team: Team name
            template_name: Name of the bet builder template
            
        Returns:
            List of player dictionaries with availability info
        """
        # Get all players from the Anytime Goalscorer market (most comprehensive)
        all_players = self.get_player_list(team, "Player to Score", "Anytime")
        
        eligible_players = []
        
        for player in all_players:
            player_name = player.get("name")
            availability = self.check_player_availability(player_name, team, template_name)
            
            if availability["available"]:
                eligible_players.append({
                    "name": player_name,
                    "team": team,
                    "template": template_name,
                    "markets": availability["available_markets"]
                })
        
        return eligible_players
    
    def get_all_eligible_players(self) -> Dict[str, Dict[str, List[Dict]]]:
        """
        Get all eligible players for all templates across all teams
        
        Returns:
            Nested dictionary: {template_name: {team_name: [player_list]}}
        """
        # Get teams from market data
        teams = []
        for group in self.parser.data.get("byoMarketGroups", []):
            if group.get("category") == "PLAYER_TO_SCORE":
                teams = group.get("teams", [])
                break
        
        results = {}
        
        for template_name in BetBuilderTemplates.get_all_template_names():
            results[template_name] = {}
            
            for team in teams:
                eligible = self.get_eligible_players_for_template(team, template_name)
                if eligible:
                    results[template_name][team] = eligible
        
        return results

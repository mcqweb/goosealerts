"""
Unified Client Interface for William Hill Bet Builder

This provides a simple, high-level interface for using the bet builder functionality
as a module in other projects.
"""

from typing import Dict, List, Optional
from pathlib import Path
import sys

# Ensure proper imports
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from src.api_client import WilliamHillAPIClient
from src.cache_manager import CacheManager
from src.market_parser import MarketParser
from src.bet_builder_generator import BetBuilderGenerator
from src.bet_builder_templates import BetBuilderTemplates, PlayerMarketChecker


class BetBuilderClient:
    """
    High-level client for William Hill Bet Builder operations
    
    Example:
        >>> from willhill_betbuilder import BetBuilderClient, Config
        >>> 
        >>> # Configure (optional)
        >>> Config.set_session_cookie("YOUR_SESSION_COOKIE")
        >>> Config.set_proxy(http_proxy="http://localhost:8080")
        >>> 
        >>> # Create client
        >>> client = BetBuilderClient()
        >>> 
        >>> # Get market data
        >>> client.load_event("OB_EV37926026")
        >>> 
        >>> # Get eligible players
        >>> players = client.get_eligible_players("Anytime Goalscorer")
        >>> 
        >>> # Generate combinations
        >>> combos = client.get_player_combinations("Joshua Zirkzee", "Man Utd", "Anytime Goalscorer")
        >>> 
        >>> # Get pricing
        >>> price = client.get_combination_price(combos[0])
        >>> print(f"Odds: {price['selection']['price']['decimal']}")
    """
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize the Bet Builder client
        
        Args:
            cache_dir: Optional custom cache directory
        """
        self.api_client = WilliamHillAPIClient()
        self.cache_manager = CacheManager(cache_dir)
        self.parser = None
        self.generator = None
        self.current_event_id = None
    
    def load_event(self, event_id: str, force_refresh: bool = False) -> bool:
        """
        Load market data for an event
        
        Args:
            event_id: Event ID (e.g., 'OB_EV37926026')
            force_refresh: Force refresh from API even if cached
            
        Returns:
            True if successful, False otherwise
        """
        self.current_event_id = event_id
        
        # Try cache first
        markets = None if force_refresh else self.cache_manager.get_cached_data(event_id)
        
        # Fetch from API if not cached
        if not markets:
            try:
                markets = self.api_client.get_event_markets(event_id)
                if markets:
                    self.cache_manager.save_to_cache(event_id, markets)
            except Exception as e:
                print(f"Error loading event data: {e}")
                return False
        
        if not markets:
            return False
        
        # Parse and initialize generator
        self.parser = MarketParser(markets)
        self.generator = BetBuilderGenerator(self.parser)
        
        return True
    
    def get_templates(self) -> List[str]:
        """
        Get list of available bet builder templates
        
        Returns:
            List of template names
        """
        return BetBuilderTemplates.get_all_template_names()
    
    def get_template_info(self, template_name: str) -> Dict:
        """
        Get information about a specific template
        
        Args:
            template_name: Name of the template
            
        Returns:
            Template configuration dictionary
        """
        return BetBuilderTemplates.get_template(template_name)
    
    def get_eligible_players(self, template_name: Optional[str] = None) -> Dict:
        """
        Get eligible players for a template or all templates
        
        Args:
            template_name: Optional specific template name
            
        Returns:
            Dictionary of eligible players by team
        """
        if not self.parser:
            raise ValueError("No event loaded. Call load_event() first.")
        
        checker = PlayerMarketChecker(self.parser)
        
        if template_name:
            # Get teams from parser
            teams = []
            for group in self.parser.data.get("byoMarketGroups", []):
                if group.get("category") == "PLAYER_TO_SCORE":
                    teams = group.get("teams", [])
                    break
            
            result = {}
            for team in teams:
                eligible = checker.get_eligible_players_for_template(team, template_name)
                if eligible:
                    result[team] = eligible
            
            return result
        else:
            return checker.get_all_eligible_players()
    
    def get_teams(self) -> List[str]:
        """
        Get list of teams in the loaded event
        
        Returns:
            List of team names
        """
        if not self.parser:
            raise ValueError("No event loaded. Call load_event() first.")
        
        teams = []
        for group in self.parser.data.get("byoMarketGroups", []):
            if group.get("category") == "PLAYER_TO_SCORE":
                teams = group.get("teams", [])
                break
        
        return teams
    
    def get_player_combinations(
        self,
        player_name: str,
        team: Optional[str] = None,
        template_name: Optional[str] = None,
        get_price: bool = False
    ) -> List[Dict]:
        """
        Generate bet builder combinations for a player
        
        Args:
            player_name: Player's name
            team: Team name (optional - will try all teams if not provided)
            template_name: Optional specific template (generates all if not provided)
            get_price: Whether to fetch prices for combinations (default: False)
            
        Returns:
            List of combination dictionaries
        """
        if not self.generator:
            raise ValueError("No event loaded. Call load_event() first.")
        
        # If no team specified, try all teams in the match
        teams_to_try = [team] if team else self.get_teams()
        all_combos = []
        
        for team_name in teams_to_try:
            if template_name:
                combo = self.generator.generate_combo_for_player(player_name, team_name, template_name)
                if combo.get("success"):
                    all_combos.append(combo)
            else:
                combos = self.generator.generate_all_combos_for_player(player_name, team_name)
                all_combos.extend([c for c in combos if c.get("success")])
            
            # If we found valid combos, stop trying other teams
            if all_combos:
                break
        
        # Fetch prices if requested
        if get_price and all_combos:
            for combo in all_combos:
                if combo.get("success"):
                    price_data = self.get_combination_price(combo)
                    combo["price_data"] = price_data
        
        return all_combos
    
    def get_all_combinations(self) -> Dict[str, List[Dict]]:
        """
        Generate all combinations for all eligible players
        
        Returns:
            Dictionary organized by template name
        """
        if not self.generator:
            raise ValueError("No event loaded. Call load_event() first.")
        
        return self.generator.generate_all_combos_for_event()
    
    def get_combination_price(self, combination: Dict) -> Optional[Dict]:
        """
        Get live pricing for a combination
        
        Args:
            combination: Combination dictionary from get_player_combinations()
            
        Returns:
            Normalized pricing data with 'success', 'odds', 'display_odds', etc. or None if failed
        """
        if not self.generator:
            raise ValueError("No event loaded. Call load_event() first.")
        
        raw_response = self.generator.get_combo_price(combination)
        
        if not raw_response:
            return {'success': False, 'error': 'No response from pricing API'}
        
        # Check if API returned an error
        if raw_response.get('status') != 'ok':
            return {'success': False, 'error': f"API status: {raw_response.get('status')}"}
        
        # Extract price data from the response
        selection = raw_response.get('selection', {})
        price = selection.get('price', {})
        
        if not price or 'decimal' not in price:
            return {'success': False, 'error': 'No price data in response'}
        
        return {
            'success': True,
            'odds': price.get('decimal'),
            'numerator': price.get('numerator'),
            'denominator': price.get('denominator'),
            'display_odds': f"{price.get('numerator')}/{price.get('denominator')}",
            'us_odds': price.get('us'),
            'market_id': selection.get('byoMarketId'),
            'trace_id': raw_response.get('traceId'),
            'raw_response': raw_response
        }
    
    def get_summary_stats(self) -> Dict:
        """
        Get summary statistics for the current event
        
        Returns:
            Dictionary with combination counts by template and team
        """
        if not self.generator:
            raise ValueError("No event loaded. Call load_event() first.")
        
        return self.generator.get_summary_stats()
    
    def format_combination(self, combination: Dict, include_payload: bool = False, price_data: Optional[Dict] = None) -> str:
        """
        Format a combination for display
        
        Args:
            combination: Combination dictionary
            include_payload: Include pricing API payload
            price_data: Optional pricing data to include
            
        Returns:
            Formatted string representation
        """
        if not self.generator:
            raise ValueError("No event loaded. Call load_event() first.")
        
        return self.generator.format_combo_output(combination, include_payload, price_data)


# Convenience functions for quick access
def configure(session_cookie: Optional[str] = None, http_proxy: Optional[str] = None, https_proxy: Optional[str] = None):
    """
    Quick configuration helper
    
    Args:
        session_cookie: William Hill session cookie
        http_proxy: HTTP proxy URL
        https_proxy: HTTPS proxy URL
    """
    if session_cookie:
        Config.set_session_cookie(session_cookie)
    if http_proxy or https_proxy:
        Config.set_proxy(http_proxy, https_proxy)


def load_config(config_file: str):
    """
    Load configuration from a JSON file
    
    Args:
        config_file: Path to configuration file
    """
    Config.load_from_file(config_file)

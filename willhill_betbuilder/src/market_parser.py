"""
Market Parser and Analyzer
Extracts and organizes available markets from API response
"""

from typing import Dict, Any, List, Set


class MarketParser:
    """Parses and analyzes market data from William Hill API"""
    
    def __init__(self, markets_data: Dict[str, Any]):
        """
        Initialize the parser with markets data
        
        Args:
            markets_data: The full API response containing market groups
        """
        self.data = markets_data
        self.market_groups = markets_data.get('byoMarketGroups', [])
    
    def get_all_categories(self) -> List[str]:
        """
        Get list of all available market categories
        
        Returns:
            List of category names
        """
        categories = []
        for group in self.market_groups:
            category = group.get('categoryName')
            if category:
                categories.append(category)
        return categories
    
    def get_markets_by_category(self, category_name: str) -> Dict[str, Any]:
        """
        Get all markets for a specific category
        
        Args:
            category_name: Name of the market category
            
        Returns:
            Market group data for that category
        """
        for group in self.market_groups:
            if group.get('categoryName') == category_name:
                return group
        return None
    
    def get_category_summary(self) -> List[Dict[str, Any]]:
        """
        Get summary of all categories with their types and periods
        
        Returns:
            List of dicts with category information
        """
        summary = []
        for group in self.market_groups:
            summary.append({
                'category': group.get('categoryName'),
                'type': group.get('byoMarketType'),
                'periods': group.get('periods', []),
                'teams': group.get('teams', []),
                'market_categories': group.get('marketCategories', []),
                'impact_sub_eligible': group.get('impactSubEligible', False)
            })
        return summary
    
    def get_selections_for_market(self, category_name: str, period: str = "90 Minutes", 
                                  team: str = None) -> List[Dict[str, Any]]:
        """
        Get all selections for a specific market
        
        Args:
            category_name: Market category name
            period: Time period (e.g., "90 Minutes", "1st Half")
            team: Team name if applicable (for team-specific markets)
            
        Returns:
            List of selection dicts
        """
        market_group = self.get_markets_by_category(category_name)
        if not market_group:
            return []
        
        markets = market_group.get('markets', {})
        
        # Navigate to the correct market
        if team and team in markets:
            market_data = markets[team].get(period, {})
        elif markets:
            # For markets without team structure
            market_data = markets.get(period, {})
        else:
            return []
        
        return market_data.get('selections', [])
    
    def print_category_summary(self):
        """Print a readable summary of all categories"""
        print("\nAvailable Market Categories:")
        print("=" * 80)
        
        summary = self.get_category_summary()
        for i, cat in enumerate(summary, 1):
            print(f"\n{i}. {cat['category']}")
            print(f"   Type: {cat['type']}")
            print(f"   Periods: {', '.join(cat['periods'])}")
            if cat['teams']:
                print(f"   Teams: {', '.join(cat['teams'])}")
            print(f"   Market Categories: {', '.join(cat['market_categories'])}")
            print(f"   Impact Sub Eligible: {cat['impact_sub_eligible']}")

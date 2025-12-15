"""
Bet Builder Combination Generator
Creates combinations of markets for bet builder bets
"""

from typing import List, Dict, Any
from itertools import combinations


class BetBuilderCombinations:
    """Generates combinations of bet builder markets"""
    
    def __init__(self, market_parser):
        """
        Initialize with a market parser
        
        Args:
            market_parser: MarketParser instance with loaded data
        """
        self.parser = market_parser
    
    def create_combination(self, markets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create a combination object from selected markets
        
        Args:
            markets: List of market selection dicts, each should have:
                - category: Market category name
                - period: Time period
                - team: Team (optional)
                - selection_id: The selection ID
                - selection_name: Name of the selection
                - ob_id: OB ID for the selection
                
        Returns:
            Combination dict with all selections
        """
        combination = {
            'selections': [],
            'count': len(markets)
        }
        
        for market in markets:
            combination['selections'].append({
                'category': market.get('category'),
                'period': market.get('period'),
                'team': market.get('team'),
                'selection_id': market.get('selection_id'),
                'selection_name': market.get('selection_name'),
                'ob_id': market.get('ob_id'),
                'type': market.get('type'),
            })
        
        return combination
    
    def generate_combinations(self, categories: List[str], 
                             period: str = "90 Minutes",
                             min_selections: int = 2,
                             max_selections: int = 5) -> List[Dict[str, Any]]:
        """
        Generate all possible combinations for given categories
        
        Args:
            categories: List of category names to combine
            period: Time period for markets
            min_selections: Minimum number of selections per combination
            max_selections: Maximum number of selections per combination
            
        Returns:
            List of combination dicts
        """
        # First, get all available selections for each category
        category_selections = {}
        for cat in categories:
            selections = self.parser.get_selections_for_market(cat, period)
            if selections:
                category_selections[cat] = selections
        
        # Generate combinations
        all_combos = []
        
        # For each combination size
        for size in range(min_selections, min(max_selections + 1, len(categories) + 1)):
            # Get all category combinations of this size
            for cat_combo in combinations(categories, size):
                # For each category in the combination, we need to pick one selection
                # This would generate a lot of combinations, so we'll just
                # show the structure here
                combo_info = {
                    'categories': list(cat_combo),
                    'size': size,
                    'period': period
                }
                all_combos.append(combo_info)
        
        return all_combos
    
    def get_popular_combinations(self) -> List[Dict[str, Any]]:
        """
        Get commonly used bet builder combinations
        
        Returns:
            List of popular combination templates
        """
        popular = [
            {
                'name': 'Result + Goals',
                'categories': ['Match Result', 'Total Goals'],
                'description': 'Match winner combined with total goals'
            },
            {
                'name': 'Both Teams to Score + Winner',
                'categories': ['Both Teams to Score', 'Match Result'],
                'description': 'BTTS with match result'
            },
            {
                'name': 'Player to Score + Result',
                'categories': ['Player to Score', 'Match Result'],
                'description': 'Specific player to score with match outcome'
            },
            {
                'name': 'Goals + Corners',
                'categories': ['Total Goals', 'Total Corners'],
                'description': 'Total goals and corners in the match'
            },
            {
                'name': 'Cards + Corners',
                'categories': ['Total Cards', 'Total Corners'],
                'description': 'Total cards and corners'
            }
        ]
        return popular
    
    def validate_combination(self, selections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate if a combination is allowed (check for conflicts)
        
        Args:
            selections: List of market selections
            
        Returns:
            Dict with 'valid' bool and 'reason' if invalid
        """
        # Basic validation checks
        if len(selections) < 2:
            return {'valid': False, 'reason': 'Need at least 2 selections'}
        
        # Check for same category conflicts
        categories_used = [s.get('category') for s in selections]
        if len(categories_used) != len(set(categories_used)):
            return {'valid': False, 'reason': 'Cannot combine multiple selections from same category'}
        
        # Check for conflicting selections (e.g., Home Win and Away Win)
        # This would need more sophisticated logic based on market types
        
        return {'valid': True, 'reason': None}

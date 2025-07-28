"""
Intelligent ticket pricing engine with market analysis and decision logging.
Provides price recommendations based on market conditions and timing.
"""

import os
import csv
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from statistics import median, stdev
import json


@dataclass
class PricingConfig:
    """Configuration for pricing engine behavior."""
    price_floor_buffer: float = 0.95  # Minimum price as % of floor
    urgency_threshold_hours: int = 48  # Hours before game to trigger urgency
    aggressiveness: float = 0.7  # 0.0 = conservative, 1.0 = aggressive
    round_to_nearest: int = 5  # Round prices to nearest $X
    max_undercut_amount: float = 15.0  # Max amount to undercut by
    volatility_threshold: float = 0.2  # Market volatility threshold
    

@dataclass
class MarketPosition:
    """Market position analysis for a listing."""
    rank: int  # 1 = cheapest in section
    total_comps: int  # Total comparable listings
    percentile: float  # Position as percentile (0-100)
    undercut_amount: float  # Amount below next cheapest
    overcut_amount: float  # Amount above next expensive


@dataclass
class PricingDecision:
    """Complete pricing decision with metadata."""
    recommended_price: float
    reasoning: str
    market_position: MarketPosition
    price_floor_applied: bool
    market_summary: Dict
    confidence: float  # 0-1 confidence in recommendation
    urgency_factor: float


class PricingEngine:
    """Main pricing engine for ticket recommendations."""
    
    def __init__(self, config: PricingConfig = None):
        """Initialize pricing engine with configuration."""
        self.config = config or PricingConfig()
        self.decision_log_path = "pricing_decisions.csv"
        self._ensure_log_file()
    
    def _ensure_log_file(self):
        """Create CSV log file with headers if it doesn't exist."""
        if not os.path.exists(self.decision_log_path):
            headers = [
                'timestamp', 'game_id', 'section', 'row', 'quantity',
                'my_price', 'recommended_price', 'final_price', 
                'market_floor', 'market_avg', 'market_ceiling',
                'total_comps', 'rank', 'percentile', 'urgency_hours',
                'reasoning', 'confidence', 'price_floor_applied'
            ]
            
            with open(self.decision_log_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
    
    def get_price_recommendation(self, my_listing: Dict, market_listings: List[Dict], 
                               game_time: datetime) -> PricingDecision:
        """
        Main function to get price recommendation for a listing.
        
        Args:
            my_listing: Dict with section, row, quantity, current_price
            market_listings: List of all market listings for this game
            game_time: Datetime of the game
            
        Returns:
            PricingDecision with recommendation and analysis
        """
        # Step 1: Find comparable listings
        comps = self.find_comps(my_listing, market_listings)
        
        # Step 2: Calculate market position
        market_position = self.calculate_market_position(my_listing, comps)
        
        # Step 3: Get time-based urgency
        urgency_hours = self.get_time_to_game(game_time)
        urgency_factor = self._calculate_urgency_factor(urgency_hours)
        
        # Step 4: Calculate market summary
        market_summary = self._calculate_market_summary(comps)
        
        # Step 5: Determine base price recommendation
        base_price = self._calculate_base_price(my_listing, market_summary, urgency_factor)
        
        # Step 6: Apply timing adjustments
        adjusted_price = self.adjust_price_by_timing(
            base_price, market_summary['floor'], urgency_factor
        )
        
        # Step 7: Apply constraints and rounding
        final_price, price_floor_applied = self.apply_constraints(
            adjusted_price, market_summary['floor']
        )
        
        # Step 8: Generate reasoning and confidence
        reasoning, confidence = self._generate_reasoning(
            my_listing, market_summary, market_position, urgency_factor, final_price
        )
        
        # Step 9: Create decision object
        decision = PricingDecision(
            recommended_price=final_price,
            reasoning=reasoning,
            market_position=market_position,
            price_floor_applied=price_floor_applied,
            market_summary=market_summary,
            confidence=confidence,
            urgency_factor=urgency_factor
        )
        
        # Step 10: Log decision
        self.log_and_return_decision(my_listing, decision, game_time)
        
        return decision
    
    def find_comps(self, my_listing: Dict, market_listings: List[Dict]) -> List[Dict]:
        """
        Find comparable listings based on section, quantity, and proximity.
        
        Args:
            my_listing: My listing details
            market_listings: All available market listings
            
        Returns:
            List of comparable listings sorted by price
        """
        comps = []
        my_section = my_listing.get('section', '').lower()
        my_quantity = my_listing.get('quantity', 1)
        my_row = my_listing.get('row', '')
        
        for listing in market_listings:
            # Skip listings without price
            if not listing.get('price'):
                continue
            
            # Exact section match (primary criteria)
            if listing.get('section', '').lower() == my_section:
                comps.append({**listing, 'match_type': 'exact_section'})
            
            # Similar quantity (within 1)
            elif abs(listing.get('quantity', 1) - my_quantity) <= 1:
                comps.append({**listing, 'match_type': 'similar_quantity'})
        
        # If no exact section matches, find similar sections
        if len(comps) < 3:
            for listing in market_listings:
                if not listing.get('price'):
                    continue
                
                section_similarity = self._calculate_section_similarity(
                    my_section, listing.get('section', '').lower()
                )
                
                if section_similarity > 0.6:  # 60% similarity threshold
                    comps.append({**listing, 'match_type': 'similar_section'})
        
        # Sort by price and remove duplicates
        comps = sorted(comps, key=lambda x: x['price'])
        seen_prices = set()
        unique_comps = []
        
        for comp in comps:
            price_key = (comp['price'], comp.get('section'), comp.get('row'))
            if price_key not in seen_prices:
                seen_prices.add(price_key)
                unique_comps.append(comp)
        
        return unique_comps[:20]  # Limit to top 20 comps
    
    def calculate_market_position(self, my_listing: Dict, comps: List[Dict]) -> MarketPosition:
        """
        Calculate where my listing stands in the market.
        
        Args:
            my_listing: My listing details
            comps: Comparable listings
            
        Returns:
            MarketPosition with rank and percentile data
        """
        if not comps:
            return MarketPosition(1, 0, 0.0, 0.0, 0.0)
        
        my_price = my_listing.get('current_price', my_listing.get('price', 0))
        comp_prices = [c['price'] for c in comps]
        
        # Add my price to the list for ranking
        all_prices = comp_prices + [my_price]
        all_prices.sort()
        
        # Find my rank (1-based)
        rank = all_prices.index(my_price) + 1
        total_comps = len(comps)
        
        # Calculate percentile
        percentile = ((rank - 1) / len(all_prices)) * 100 if len(all_prices) > 1 else 0
        
        # Calculate undercut/overcut amounts
        undercut_amount = 0.0
        overcut_amount = 0.0
        
        if rank > 1:  # Not the cheapest
            next_cheaper = all_prices[rank - 2]  # Price just below mine
            overcut_amount = my_price - next_cheaper
        
        if rank < len(all_prices):  # Not the most expensive
            next_expensive = all_prices[rank]  # Price just above mine
            undercut_amount = next_expensive - my_price
        
        return MarketPosition(
            rank=rank,
            total_comps=total_comps,
            percentile=percentile,
            undercut_amount=undercut_amount,
            overcut_amount=overcut_amount
        )
    
    def get_time_to_game(self, game_time: datetime) -> float:
        """
        Calculate hours until game time.
        
        Args:
            game_time: Datetime of the game
            
        Returns:
            Hours until game (can be negative if past)
        """
        time_diff = game_time - datetime.now()
        return time_diff.total_seconds() / 3600
    
    def adjust_price_by_timing(self, my_price: float, market_floor: float, 
                             urgency: float) -> float:
        """
        Adjust price based on time to game and market urgency.
        
        Args:
            my_price: Base price recommendation
            market_floor: Lowest price in market
            urgency: Urgency factor (0-1)
            
        Returns:
            Adjusted price
        """
        # Base adjustment factor based on urgency
        if urgency > 0.8:  # Very urgent (< 12 hours)
            adjustment = -0.15  # 15% discount
        elif urgency > 0.6:  # Urgent (< 24 hours)
            adjustment = -0.10  # 10% discount
        elif urgency > 0.4:  # Moderate urgency (< 48 hours)
            adjustment = -0.05  # 5% discount
        else:  # Not urgent
            adjustment = 0.02   # 2% premium for early pricing
        
        # Apply aggressiveness modifier
        adjustment *= self.config.aggressiveness
        
        adjusted_price = my_price * (1 + adjustment)
        
        # Don't go below market floor
        return max(adjusted_price, market_floor * 0.95)
    
    def apply_constraints(self, price: float, price_floor: float) -> Tuple[float, bool]:
        """
        Apply final constraints and rounding to price.
        
        Args:
            price: Calculated price
            price_floor: Market floor price
            
        Returns:
            Tuple of (final_price, floor_applied)
        """
        floor_applied = False
        
        # Apply price floor constraint
        min_price = price_floor * self.config.price_floor_buffer
        if price < min_price:
            price = min_price
            floor_applied = True
        
        # Round to nearest configured amount
        if self.config.round_to_nearest > 0:
            price = round(price / self.config.round_to_nearest) * self.config.round_to_nearest
        
        return price, floor_applied
    
    def log_and_return_decision(self, my_listing: Dict, decision: PricingDecision, 
                              game_time: datetime):
        """
        Log pricing decision to CSV for training data.
        
        Args:
            my_listing: Original listing details
            decision: Pricing decision
            game_time: Game datetime
        """
        try:
            row_data = [
                datetime.now().isoformat(),
                my_listing.get('game_id', 'unknown'),
                my_listing.get('section', ''),
                my_listing.get('row', ''),
                my_listing.get('quantity', 1),
                my_listing.get('current_price', my_listing.get('price', 0)),
                decision.recommended_price,
                decision.recommended_price,  # Final price (same as recommended for now)
                decision.market_summary.get('floor', 0),
                decision.market_summary.get('avg', 0),
                decision.market_summary.get('ceiling', 0),
                decision.market_position.total_comps,
                decision.market_position.rank,
                decision.market_position.percentile,
                self.get_time_to_game(game_time),
                decision.reasoning.replace(',', ';'),  # Escape commas for CSV
                decision.confidence,
                decision.price_floor_applied
            ]
            
            with open(self.decision_log_path, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(row_data)
                
        except Exception as e:
            print(f"⚠️ Failed to log decision: {e}")
    
    def _calculate_urgency_factor(self, hours_to_game: float) -> float:
        """Calculate urgency factor based on time to game."""
        if hours_to_game <= 0:
            return 1.0  # Game has passed
        elif hours_to_game <= 12:
            return 0.9  # Very urgent
        elif hours_to_game <= 24:
            return 0.7  # Urgent
        elif hours_to_game <= 48:
            return 0.5  # Moderate
        elif hours_to_game <= 168:  # 1 week
            return 0.3  # Low urgency
        else:
            return 0.1  # Very low urgency
    
    def _calculate_market_summary(self, comps: List[Dict]) -> Dict:
        """Calculate market summary statistics."""
        if not comps:
            return {'floor': 0, 'ceiling': 0, 'avg': 0, 'median': 0, 'volatility': 0}
        
        prices = [c['price'] for c in comps]
        avg_price = sum(prices) / len(prices)
        median_price = median(prices)
        
        # Calculate volatility (coefficient of variation)
        volatility = stdev(prices) / avg_price if avg_price > 0 and len(prices) > 1 else 0
        
        return {
            'floor': min(prices),
            'ceiling': max(prices),
            'avg': avg_price,
            'median': median_price,
            'volatility': volatility,
            'count': len(comps)
        }
    
    def _calculate_base_price(self, my_listing: Dict, market_summary: Dict, 
                            urgency_factor: float) -> float:
        """Calculate base price recommendation."""
        market_avg = market_summary['avg']
        market_floor = market_summary['floor']
        volatility = market_summary['volatility']
        
        # Start with market average as base
        base_price = market_avg
        
        # Adjust based on market volatility
        if volatility > self.config.volatility_threshold:
            # High volatility - be more conservative
            base_price = market_avg * 0.95
        else:
            # Low volatility - can be more aggressive
            base_price = market_avg * 1.02
        
        # Factor in aggressiveness setting
        if self.config.aggressiveness > 0.7:
            # Aggressive: target below average
            base_price = market_avg * 0.92
        elif self.config.aggressiveness < 0.3:
            # Conservative: target at or above average
            base_price = market_avg * 1.05
        
        return base_price
    
    def _calculate_section_similarity(self, section1: str, section2: str) -> float:
        """Calculate similarity between two section names."""
        if not section1 or not section2:
            return 0.0
        
        # Exact match
        if section1 == section2:
            return 1.0
        
        # Check for common keywords
        keywords1 = set(section1.lower().split())
        keywords2 = set(section2.lower().split())
        
        if not keywords1 or not keywords2:
            return 0.0
        
        # Jaccard similarity
        intersection = len(keywords1.intersection(keywords2))
        union = len(keywords1.union(keywords2))
        
        return intersection / union if union > 0 else 0.0
    
    def _generate_reasoning(self, my_listing: Dict, market_summary: Dict, 
                          market_position: MarketPosition, urgency_factor: float,
                          final_price: float) -> Tuple[str, float]:
        """Generate human-readable reasoning and confidence score."""
        reasons = []
        confidence = 0.8  # Base confidence
        
        # Market position reasoning
        if market_position.rank == 1:
            reasons.append("Currently cheapest in section")
            confidence += 0.1
        elif market_position.rank <= 3:
            reasons.append(f"Currently {market_position.rank}{'nd' if market_position.rank == 2 else 'rd'} cheapest")
            confidence += 0.05
        elif market_position.percentile > 75:
            reasons.append("Priced above 75% of market")
            confidence -= 0.1
        
        # Urgency reasoning
        if urgency_factor > 0.7:
            reasons.append("Game approaching - urgent repricing")
            confidence += 0.1
        elif urgency_factor < 0.2:
            reasons.append("Plenty of time - premium pricing")
        
        # Market volatility reasoning
        volatility = market_summary.get('volatility', 0)
        if volatility > 0.3:
            reasons.append("High market volatility")
            confidence -= 0.1
        elif volatility < 0.1:
            reasons.append("Stable market pricing")
            confidence += 0.05
        
        # Price movement reasoning
        market_avg = market_summary.get('avg', 0)
        if final_price < market_avg * 0.9:
            reasons.append("Aggressive undercut strategy")
        elif final_price > market_avg * 1.1:
            reasons.append("Premium pricing strategy")
        else:
            reasons.append("Market-competitive pricing")
        
        # Compile final reasoning
        reasoning = "; ".join(reasons) if reasons else "Standard market-based pricing"
        
        # Clamp confidence between 0.3 and 1.0
        confidence = max(0.3, min(1.0, confidence))
        
        return reasoning, confidence


# Helper functions for easy integration
def get_price_recommendation(my_listing: Dict, market_listings: List[Dict], 
                           game_time: datetime, config: PricingConfig = None) -> PricingDecision:
    """
    Convenience function to get a price recommendation.
    
    Args:
        my_listing: My listing details
        market_listings: Market listings
        game_time: Game datetime
        config: Optional pricing configuration
        
    Returns:
        PricingDecision with recommendation
    """
    engine = PricingEngine(config)
    return engine.get_price_recommendation(my_listing, market_listings, game_time)


# Example usage
if __name__ == "__main__":
    # Example usage
    my_listing = {
        'game_id': 'red-sox-vs-yankees-2024-06-15',
        'section': 'Green Monster',
        'row': '2',
        'quantity': 2,
        'current_price': 250.00
    }
    
    market_listings = [
        {'section': 'Green Monster', 'row': '1', 'quantity': 2, 'price': 275.00},
        {'section': 'Green Monster', 'row': '3', 'quantity': 2, 'price': 240.00},
        {'section': 'Green Monster', 'row': '2', 'quantity': 1, 'price': 225.00},
        {'section': 'Green Monster', 'row': '4', 'quantity': 2, 'price': 260.00},
    ]
    
    game_time = datetime.now() + timedelta(hours=36)  # Game in 36 hours
    
    # Get recommendation
    decision = get_price_recommendation(my_listing, market_listings, game_time)
    
    print(f"💰 PRICING RECOMMENDATION")
    print(f"Current Price: ${my_listing['current_price']:.2f}")
    print(f"Recommended: ${decision.recommended_price:.2f}")
    print(f"Market Rank: {decision.market_position.rank} of {decision.market_position.total_comps + 1}")
    print(f"Confidence: {decision.confidence:.0%}")
    print(f"Reasoning: {decision.reasoning}")
    print(f"Market Summary: ${decision.market_summary['floor']:.2f} - ${decision.market_summary['ceiling']:.2f}")
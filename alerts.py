"""
Alerts system for ticket listing notifications.
Analyzes market conditions and triggers alerts for pricing opportunities.
"""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
from database import TicketDatabase
from game_tracker import GameTracker


@dataclass
class Alert:
    """Data class for alert information."""
    type: str  # undercut, surge, late_game, price_drop
    severity: str  # low, medium, high, critical
    title: str
    message: str
    game_id: str
    section: str = None
    row: str = None
    current_price: float = None
    recommended_action: str = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def __str__(self):
        severity_emoji = {
            'low': '🔵',
            'medium': '🟡', 
            'high': '🟠',
            'critical': '🔴'
        }
        emoji = severity_emoji.get(self.severity, '⚪')
        return f"{emoji} {self.title}: {self.message}"


class AlertsEngine:
    """Main alerts engine for analyzing market conditions."""
    
    def __init__(self):
        """Initialize alerts engine."""
        self.db = TicketDatabase()
        self.game_tracker = GameTracker()
        
        # Alert thresholds (configurable)
        self.config = {
            'undercut_threshold': 5.0,  # Alert if undercut by more than $5
            'surge_threshold': 0.25,    # Alert if listings drop by 25%
            'late_game_hours': 48,      # Alert if < 48 hours to game
            'price_drop_threshold': 0.10,  # Alert if floor drops by 10%
            'volatility_threshold': 0.3,   # High volatility threshold
        }
    
    def check_all_alerts(self, game_id: str = None) -> List[Alert]:
        """
        Check all alert conditions for active listings.
        
        Args:
            game_id: Optional game filter
            
        Returns:
            List of triggered alerts
        """
        alerts = []
        
        # Get active listings to check
        active_listings = self.game_tracker.get_active_listings(game_id)
        
        if not active_listings:
            return alerts
        
        # Group listings by game
        games_to_check = {}
        for listing in active_listings:
            gid = listing['game_id']
            if gid not in games_to_check:
                games_to_check[gid] = []
            games_to_check[gid].append(listing)
        
        # Check alerts for each game
        for gid, listings in games_to_check.items():
            try:
                game_alerts = self._check_game_alerts(gid, listings)
                alerts.extend(game_alerts)
            except Exception as e:
                print(f"⚠️ Error checking alerts for game {gid}: {e}")
        
        # Sort alerts by severity and timestamp
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        alerts.sort(key=lambda a: (severity_order.get(a.severity, 4), a.timestamp))
        
        return alerts
    
    def _check_game_alerts(self, game_id: str, my_listings: List[Dict]) -> List[Alert]:
        """Check all alert types for a specific game."""
        alerts = []
        
        # Get market data for this game
        market_listings = self.db.get_latest_listings(game_id)
        
        if not market_listings:
            return alerts
        
        # Get game info for timing alerts
        game_summary = self.game_tracker.get_game_summary(game_id)
        if not game_summary:
            return alerts
        
        game_date = datetime.fromisoformat(game_summary['game_date'])
        hours_to_game = (game_date - datetime.now()).total_seconds() / 3600
        
        # Check each type of alert
        for my_listing in my_listings:
            # 1. Undercut alerts
            undercut_alerts = self._check_undercut_alerts(my_listing, market_listings)
            alerts.extend(undercut_alerts)
            
            # 2. Late game alerts
            late_game_alerts = self._check_late_game_alerts(my_listing, market_listings, hours_to_game)
            alerts.extend(late_game_alerts)
        
        # 3. Market-wide alerts (check once per game)
        if my_listings:  # Only if we have listings for this game
            surge_alerts = self._check_surge_alerts(game_id, my_listings)
            alerts.extend(surge_alerts)
            
            price_drop_alerts = self._check_price_drop_alerts(game_id, my_listings, market_listings)
            alerts.extend(price_drop_alerts)
        
        return alerts
    
    def _check_undercut_alerts(self, my_listing: Dict, market_listings: List[Dict]) -> List[Alert]:
        """Check for undercut alerts."""
        alerts = []
        
        my_section = my_listing['section']
        my_price = my_listing['current_price']
        
        if not my_section or not my_price:
            return alerts
        
        # Find comparable listings in same section
        section_comps = [
            l for l in market_listings 
            if l.get('section', '').lower() == my_section.lower() and l.get('price')
        ]
        
        if not section_comps:
            return alerts
        
        # Find cheapest competitor in section
        cheapest_comp = min(section_comps, key=lambda x: x['price'])
        undercut_amount = my_price - cheapest_comp['price']
        
        if undercut_amount > self.config['undercut_threshold']:
            severity = 'high' if undercut_amount > 15 else 'medium'
            
            alert = Alert(
                type='undercut',
                severity=severity,
                title=f"Undercut Alert - {my_section}",
                message=f"A new listing in {my_section} is ${undercut_amount:.0f} below your price of ${my_price:.0f}. "
                       f"New floor: ${cheapest_comp['price']:.0f}",
                game_id=my_listing['game_id'],
                section=my_section,
                row=my_listing.get('row'),
                current_price=my_price,
                recommended_action=f"Consider repricing to ${cheapest_comp['price'] - 5:.0f}"
            )
            alerts.append(alert)
        
        return alerts
    
    def _check_surge_alerts(self, game_id: str, my_listings: List[Dict]) -> List[Alert]:
        """Check for sell-through surge alerts."""
        alerts = []
        
        try:
            # Get price history for the last 24 hours
            price_history = self.db.get_price_history(game_id, days=1)
            
            if len(price_history) < 2:
                return alerts
            
            # Compare latest vs 24 hours ago
            latest = price_history[-1]
            previous = price_history[0]
            
            # Calculate percentage change in listing count
            count_change = (latest['count'] - previous['count']) / previous['count']
            
            if count_change <= -self.config['surge_threshold']:  # Negative = fewer listings
                for my_listing in my_listings:
                    section = my_listing['section']
                    
                    # Check section-specific surge
                    section_history = self.db.get_price_history(game_id, section=section, days=1)
                    
                    if len(section_history) >= 2:
                        section_latest = section_history[-1]
                        section_previous = section_history[0]
                        section_change = (section_latest['count'] - section_previous['count']) / section_previous['count']
                        
                        if section_change <= -self.config['surge_threshold']:
                            severity = 'high' if section_change <= -0.4 else 'medium'
                            
                            alert = Alert(
                                type='surge',
                                severity=severity,
                                title=f"Sell-Through Surge - {section}",
                                message=f"Listings in {section} dropped {abs(section_change):.0%} in 24h. "
                                       f"Only {section_latest['count']} listings remain. Market tightening!",
                                game_id=game_id,
                                section=section,
                                recommended_action="Consider holding current price or slight increase"
                            )
                            alerts.append(alert)
        
        except Exception as e:
            print(f"⚠️ Error checking surge alerts: {e}")
        
        return alerts
    
    def _check_late_game_alerts(self, my_listing: Dict, market_listings: List[Dict], 
                              hours_to_game: float) -> List[Alert]:
        """Check for late game timing alerts."""
        alerts = []
        
        if hours_to_game > self.config['late_game_hours']:
            return alerts
        
        my_section = my_listing['section']
        my_price = my_listing['current_price']
        
        # Find section comps and calculate my rank
        section_comps = [
            l for l in market_listings 
            if l.get('section', '').lower() == my_section.lower() and l.get('price')
        ]
        
        if not section_comps:
            return alerts
        
        # Add my listing and sort
        all_prices = [l['price'] for l in section_comps] + [my_price]
        all_prices.sort()
        
        my_rank = all_prices.index(my_price) + 1
        total_listings = len(all_prices)
        percentile = (my_rank - 1) / (total_listings - 1) * 100 if total_listings > 1 else 0
        
        # Alert if not in bottom 25% with less than 48 hours
        if percentile > 75 and hours_to_game < self.config['late_game_hours']:
            severity = 'critical' if hours_to_game < 12 else 'high'
            
            alert = Alert(
                type='late_game',
                severity=severity,
                title=f"Late Game Warning - {my_section}",
                message=f"Game in {hours_to_game:.0f}h. You're #{my_rank} of {total_listings} "
                       f"({percentile:.0f}th percentile). Risk missing sell window!",
                game_id=my_listing['game_id'],
                section=my_section,
                row=my_listing.get('row'),
                current_price=my_price,
                recommended_action=f"Consider aggressive repricing to ${all_prices[len(all_prices)//4]:.0f}"
            )
            alerts.append(alert)
        
        return alerts
    
    def _check_price_drop_alerts(self, game_id: str, my_listings: List[Dict], 
                               market_listings: List[Dict]) -> List[Alert]:
        """Check for market price drop alerts."""
        alerts = []
        
        try:
            # Get price history for the last 24 hours
            price_history = self.db.get_price_history(game_id, days=1)
            
            if len(price_history) < 2:
                return alerts
            
            # Compare latest vs 24 hours ago
            latest = price_history[-1]
            previous = price_history[0]
            
            # Calculate percentage change in floor price
            floor_change = (latest['min_price'] - previous['min_price']) / previous['min_price']
            
            if floor_change <= -self.config['price_drop_threshold']:  # Significant drop
                # Check which of my listings are affected
                for my_listing in my_listings:
                    section = my_listing['section']
                    my_price = my_listing['current_price']
                    
                    # Get current section floor
                    section_comps = [
                        l for l in market_listings 
                        if l.get('section', '').lower() == section.lower() and l.get('price')
                    ]
                    
                    if section_comps:
                        section_floor = min(l['price'] for l in section_comps)
                        
                        # Alert if my price is significantly above new floor
                        if my_price > section_floor * 1.1:  # 10% above floor
                            severity = 'medium'
                            
                            alert = Alert(
                                type='price_drop',
                                severity=severity,
                                title=f"Market Drop - {section}",
                                message=f"Section floor fell {abs(floor_change):.0%} to ${section_floor:.0f}. "
                                       f"Your price ${my_price:.0f} is {((my_price/section_floor - 1) * 100):.0f}% above floor.",
                                game_id=game_id,
                                section=section,
                                current_price=my_price,
                                recommended_action=f"Consider repricing to ${section_floor + 5:.0f}"
                            )
                            alerts.append(alert)
        
        except Exception as e:
            print(f"⚠️ Error checking price drop alerts: {e}")
        
        return alerts
    
    def get_formatted_alert_summary(self, alerts: List[Alert]) -> str:
        """Format alerts into a readable summary."""
        if not alerts:
            return "✅ No alerts - all listings look good!"
        
        summary_lines = []
        summary_lines.append(f"🚨 {len(alerts)} Alert(s) Detected")
        summary_lines.append("=" * 40)
        
        # Group by severity
        by_severity = {}
        for alert in alerts:
            if alert.severity not in by_severity:
                by_severity[alert.severity] = []
            by_severity[alert.severity].append(alert)
        
        # Display in order of severity
        for severity in ['critical', 'high', 'medium', 'low']:
            if severity in by_severity:
                severity_alerts = by_severity[severity]
                summary_lines.append(f"\n{severity.upper()} ({len(severity_alerts)}):")
                
                for alert in severity_alerts:
                    summary_lines.append(f"  • {alert.title}")
                    summary_lines.append(f"    {alert.message}")
                    if alert.recommended_action:
                        summary_lines.append(f"    💡 {alert.recommended_action}")
        
        return "\n".join(summary_lines)
    
    def send_alert_notification(self, alert: Alert):
        """Send alert notification (placeholder for email/SMS integration)."""
        # TODO: Implement actual notification sending
        # This could integrate with email, SMS, Slack, etc.
        print(f"📱 NOTIFICATION: {alert}")
        
        # Log alert to file
        self._log_alert(alert)
    
    def _log_alert(self, alert: Alert):
        """Log alert to a file for tracking."""
        try:
            import json
            
            log_file = "alerts.log"
            alert_data = {
                'timestamp': alert.timestamp.isoformat(),
                'type': alert.type,
                'severity': alert.severity,
                'title': alert.title,
                'message': alert.message,
                'game_id': alert.game_id,
                'section': alert.section,
                'row': alert.row,
                'current_price': alert.current_price,
                'recommended_action': alert.recommended_action
            }
            
            with open(log_file, 'a') as f:
                f.write(json.dumps(alert_data) + '\n')
                
        except Exception as e:
            print(f"⚠️ Failed to log alert: {e}")


# Convenience functions
def check_alerts(game_id: str = None) -> List[Alert]:
    """
    Check all alerts for active listings.
    
    Args:
        game_id: Optional game filter
        
    Returns:
        List of triggered alerts
    """
    engine = AlertsEngine()
    return engine.check_all_alerts(game_id)


def get_alert_summary(game_id: str = None) -> str:
    """
    Get formatted alert summary.
    
    Args:
        game_id: Optional game filter
        
    Returns:
        Formatted alert summary string
    """
    engine = AlertsEngine()
    alerts = engine.check_all_alerts(game_id)
    return engine.get_formatted_alert_summary(alerts)


def print_alerts(game_id: str = None):
    """Print alerts to console with nice formatting."""
    summary = get_alert_summary(game_id)
    print(summary)


# Example usage and testing
if __name__ == "__main__":
    # Test the alerts system
    print("🔍 Checking for alerts...")
    
    alerts = check_alerts()
    
    if alerts:
        print(f"\n🚨 Found {len(alerts)} alert(s):")
        for alert in alerts:
            print(f"  {alert}")
            
        print("\n" + "="*50)
        print("DETAILED SUMMARY:")
        print(get_alert_summary())
    else:
        print("✅ No alerts detected - all good!")
    
    # Example of creating test alerts
    print("\n📝 Example Alert Formats:")
    
    test_alerts = [
        Alert(
            type='undercut',
            severity='high',
            title='Section 112 Undercut',
            message='Your listing in Section 112 is now $10 above the new floor. Consider repricing.',
            game_id='test-game',
            section='Section 112',
            current_price=112.0,
            recommended_action='Reprice to $98'
        ),
        Alert(
            type='surge',
            severity='medium',
            title='Market Surge',
            message='Only 12 listings remain in your section. Sell-through has increased.',
            game_id='test-game',
            section='Green Monster'
        ),
        Alert(
            type='late_game',
            severity='critical',
            title='Game in 36h',
            message="You're priced 3rd highest out of 8. You may miss sell window.",
            game_id='test-game',
            section='Pavilion Box',
            recommended_action='Aggressive repricing recommended'
        )
    ]
    
    for alert in test_alerts:
        print(f"  {alert}")
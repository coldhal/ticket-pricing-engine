#!/usr/bin/env python3
"""
Demo script showing the Red Sox ticket pricing system architecture.
This demonstrates the complete workflow without requiring external dependencies.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List


def demo_scraper():
    """Demonstrate the scraper functionality."""
    print("🕷️ SCRAPER DEMO")
    print("-" * 30)
    
    # Simulate scraped SeatGeek listings
    mock_listings = [
        {
            'section': 'Green Monster',
            'row': '2',
            'seat_numbers': '1-2',
            'quantity': 2,
            'price': 295.00,
            'listing_id': 'sg_123456',
            'scraped_at': datetime.now().isoformat()
        },
        {
            'section': 'Green Monster', 
            'row': '3',
            'seat_numbers': '5-6',
            'quantity': 2,
            'price': 275.00,
            'listing_id': 'sg_123457',
            'scraped_at': datetime.now().isoformat()
        },
        {
            'section': 'Infield Box 15',
            'row': 'A',
            'seat_numbers': '7',
            'quantity': 1,
            'price': 185.00,
            'listing_id': 'sg_123458',
            'scraped_at': datetime.now().isoformat()
        },
        {
            'section': 'Pavilion Box 12',
            'row': '8',
            'seat_numbers': '1-4',
            'quantity': 4,
            'price': 95.00,
            'listing_id': 'sg_123459',
            'scraped_at': datetime.now().isoformat()
        }
    ]
    
    print(f"📋 Scraped {len(mock_listings)} listings:")
    for listing in mock_listings:
        print(f"  • {listing['section']} Row {listing['row']} - "
              f"Qty {listing['quantity']} - ${listing['price']:.2f}")
    
    return mock_listings


def demo_pricing_engine(my_listing: Dict, market_listings: List[Dict]):
    """Demonstrate the pricing engine."""
    print("\n💰 PRICING ENGINE DEMO")
    print("-" * 30)
    
    print(f"📊 Analyzing: {my_listing['section']} Row {my_listing['row']}")
    print(f"💵 Current Price: ${my_listing['current_price']:.2f}")
    
    # Find comparable listings
    my_section = my_listing['section'].lower()
    comps = [l for l in market_listings if l['section'].lower() == my_section]
    
    print(f"🔍 Found {len(comps)} comparable listings in {my_listing['section']}")
    
    if comps:
        prices = [c['price'] for c in comps]
        market_floor = min(prices)
        market_avg = sum(prices) / len(prices)
        market_ceiling = max(prices)
        
        # Calculate market position
        all_prices = prices + [my_listing['current_price']]
        all_prices.sort()
        my_rank = all_prices.index(my_listing['current_price']) + 1
        
        print(f"📈 Market Analysis:")
        print(f"  Floor: ${market_floor:.2f}")
        print(f"  Average: ${market_avg:.2f}")
        print(f"  Ceiling: ${market_ceiling:.2f}")
        print(f"  Your Rank: #{my_rank} of {len(all_prices)}")
        
        # Simple pricing logic
        if my_listing['current_price'] > market_avg * 1.1:
            recommended_price = market_avg * 0.98
            reasoning = "Priced above market average - recommend lowering"
        elif my_listing['current_price'] < market_floor * 1.05:
            recommended_price = market_floor + 5
            reasoning = "Already competitive - slight increase"
        else:
            recommended_price = my_listing['current_price']
            reasoning = "Price is market-competitive"
        
        confidence = 0.85 if abs(recommended_price - my_listing['current_price']) > 5 else 0.60
        
        print(f"🤖 Recommendation: ${recommended_price:.2f}")
        print(f"🎯 Confidence: {confidence:.0%}")
        print(f"💭 Reasoning: {reasoning}")
        
        return {
            'recommended_price': recommended_price,
            'confidence': confidence,
            'reasoning': reasoning,
            'market_rank': my_rank
        }
    
    return None


def demo_alerts(my_listing: Dict, market_listings: List[Dict], game_date: datetime):
    """Demonstrate the alerts system."""
    print("\n🚨 ALERTS SYSTEM DEMO")
    print("-" * 30)
    
    alerts = []
    
    # Check for undercuts
    my_section = my_listing['section'].lower()
    section_comps = [l for l in market_listings if l['section'].lower() == my_section]
    
    if section_comps:
        cheapest_comp = min(section_comps, key=lambda x: x['price'])
        undercut_amount = my_listing['current_price'] - cheapest_comp['price']
        
        if undercut_amount > 10:
            alerts.append({
                'type': 'undercut',
                'severity': 'high',
                'message': f"🟠 Undercut Alert: New listing in {my_listing['section']} "
                          f"is ${undercut_amount:.0f} below your price!"
            })
    
    # Check game timing
    hours_to_game = (game_date - datetime.now()).total_seconds() / 3600
    
    if hours_to_game < 48 and hours_to_game > 0:
        if section_comps:
            all_prices = [c['price'] for c in section_comps] + [my_listing['current_price']]
            all_prices.sort()
            my_rank = all_prices.index(my_listing['current_price']) + 1
            total = len(all_prices)
            
            if my_rank > total * 0.75:  # In top 25% (expensive)
                severity = 'critical' if hours_to_game < 12 else 'high'
                alerts.append({
                    'type': 'late_game',
                    'severity': severity,
                    'message': f"🔴 Late Game Alert: Game in {hours_to_game:.0f}h. "
                              f"You're #{my_rank} of {total} - risk missing sell window!"
                })
    
    # Check for surge (mock data)
    if len(section_comps) < 5:  # Low inventory
        alerts.append({
            'type': 'surge',
            'severity': 'medium',
            'message': f"🟡 Market Surge: Only {len(section_comps)} listings remain "
                      f"in {my_listing['section']}. Consider holding price."
        })
    
    print(f"📊 Checked {len(['undercut', 'timing', 'surge'])} alert conditions")
    
    if alerts:
        print(f"🚨 {len(alerts)} Alert(s) Generated:")
        for alert in alerts:
            print(f"  {alert['message']}")
    else:
        print("✅ No alerts - all good!")
    
    return alerts


def demo_automation_workflow():
    """Demonstrate the complete automation workflow."""
    print("\n🚀 AUTOMATION WORKFLOW DEMO")
    print("=" * 50)
    
    # Step 1: Game setup
    game_data = {
        'game_id': 'red-sox-vs-yankees-2024-06-15',
        'game_date': datetime.now() + timedelta(hours=36),
        'opponent': 'New York Yankees',
        'venue': 'Fenway Park'
    }
    
    print(f"🎮 Game: Red Sox vs {game_data['opponent']}")
    print(f"📅 Date: {game_data['game_date'].strftime('%Y-%m-%d %H:%M')}")
    print(f"⏰ Hours to game: {(game_data['game_date'] - datetime.now()).total_seconds() / 3600:.1f}")
    
    # Step 2: My listings
    my_listings = [
        {
            'section': 'Green Monster',
            'row': '2',
            'quantity': 2,
            'current_price': 285.00,
            'original_price': 300.00
        }
    ]
    
    print(f"\n🎫 My Active Listings: {len(my_listings)}")
    for listing in my_listings:
        print(f"  • {listing['section']} Row {listing['row']} - "
              f"Qty {listing['quantity']} - ${listing['current_price']:.2f}")
    
    # Step 3: Scrape market
    print(f"\n🕷️ Scraping market data...")
    market_listings = demo_scraper()
    
    # Step 4: Process each listing
    updates_made = 0
    
    for my_listing in my_listings:
        print(f"\n" + "="*40)
        print(f"Processing: {my_listing['section']} Row {my_listing['row']}")
        
        # Run pricing engine
        decision = demo_pricing_engine(my_listing, market_listings)
        
        if decision:
            price_change = decision['recommended_price'] - my_listing['current_price']
            
            # Decide whether to update
            should_update = (
                abs(price_change) >= 5.0 and  # Significant change
                decision['confidence'] >= 0.70    # High confidence
            )
            
            if should_update:
                print(f"🔄 UPDATE RECOMMENDED:")
                print(f"  ${my_listing['current_price']:.2f} → ${decision['recommended_price']:.2f}")
                print(f"  Change: ${price_change:+.2f}")
                print(f"  ✅ Would update SeatGeek listing")
                updates_made += 1
            else:
                print(f"✋ No update needed - price is optimal")
        
        # Check alerts
        alerts = demo_alerts(my_listing, market_listings, game_data['game_date'])
    
    # Step 5: Summary
    print(f"\n" + "="*50)
    print(f"📊 WORKFLOW SUMMARY")
    print(f"⏱️ Processed in ~2.5 minutes")
    print(f"🎮 Games: 1")
    print(f"🕷️ Listings Scraped: {len(market_listings)}")
    print(f"🎫 My Listings: {len(my_listings)}")
    print(f"💰 Prices Updated: {updates_made}")
    
    if updates_made > 0:
        print(f"✅ Successfully updated {updates_made} listing(s)")
    else:
        print(f"ℹ️ No price updates needed")


def demo_system_architecture():
    """Show the complete system architecture."""
    print("🏗️ RED SOX TICKET PRICING SYSTEM")
    print("=" * 50)
    
    architecture = {
        "Core Modules": [
            "📄 scraper.py - SeatGeek web scraping with Playwright",
            "📄 database.py - SQLAlchemy data storage & history tracking", 
            "📄 pricing_engine.py - Intelligent price recommendations",
            "📄 seatgeek_automation.py - Automated price updates",
            "📄 game_tracker.py - Game & listing inventory management",
            "📄 alerts.py - Market monitoring & notifications"
        ],
        "Automation": [
            "📄 auto_pricer.py - Main workflow orchestrator",
            "📄 initial_import.py - Import existing listings"
        ],
        "Configuration": [
            "📝 .env - SeatGeek credentials",
            "📝 games_config.json - Tracked games & settings",
            "📝 requirements.txt - Python dependencies"
        ],
        "Data Files": [
            "📊 ticket_data.db - SQLite database",
            "📊 pricing_decisions.csv - ML training data",
            "📊 alerts.log - Alert history",
            "📊 price_updates.log - Update attempts"
        ]
    }
    
    for category, items in architecture.items():
        print(f"\n{category}:")
        for item in items:
            print(f"  {item}")
    
    print(f"\n🔄 WORKFLOW:")
    steps = [
        "1. 🕷️ Scrape market listings from SeatGeek",
        "2. 💾 Store data with timestamps in SQLite",
        "3. 🤖 Analyze market position & generate recommendations", 
        "4. 🔍 Check alert conditions (undercuts, timing, etc.)",
        "5. 🔄 Update prices on SeatGeek when beneficial",
        "6. 📊 Log decisions for ML training"
    ]
    
    for step in steps:
        print(f"  {step}")
    
    print(f"\n📋 FEATURES:")
    features = [
        "✅ Automated market scraping with lazy-loading support",
        "✅ Intelligent pricing based on market position & timing",
        "✅ Real-time alerts for undercuts & opportunities", 
        "✅ Historical tracking for trend analysis",
        "✅ Conservative safety controls & error handling",
        "✅ Configurable aggressiveness & price floors",
        "✅ Complete audit trail for all decisions"
    ]
    
    for feature in features:
        print(f"  {feature}")


def main():
    """Run the complete demo."""
    print("🎯 Red Sox Ticket Pricing System - Demo")
    print("Demonstrating intelligent automated ticket pricing")
    print()
    
    # Show system architecture
    demo_system_architecture()
    
    print("\n" + "="*60)
    print("🎬 LIVE WORKFLOW DEMONSTRATION")
    print("="*60)
    
    # Run workflow demo
    demo_automation_workflow()
    
    print(f"\n🚀 NEXT STEPS:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Install Playwright: playwright install chromium") 
    print("3. Configure credentials in .env file")
    print("4. Import existing listings: python initial_import.py")
    print("5. Run automation: python auto_pricer.py run")
    print("6. Set up scheduling with cron or similar")
    
    print(f"\n⚠️ IMPORTANT:")
    print("• Always test with small price changes first")
    print("• Monitor the system for the first few runs")
    print("• Respect SeatGeek's terms of service")
    print("• Keep your .env credentials secure")
    
    print(f"\n📈 The system will continuously optimize your ticket prices")
    print("based on market conditions, timing, and your settings!")


if __name__ == "__main__":
    main()
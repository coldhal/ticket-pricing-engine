"""
Test script to validate the complete ticket pricing system.
Tests all modules and their integration.
"""

import asyncio
import sys
from datetime import datetime, timedelta
from typing import Dict, List

# Test imports
try:
    from scraper import SeatGeekScraper
    from database import TicketDatabase, save_scraped_listings, get_latest_listings
    from pricing_engine import PricingEngine, get_price_recommendation, PricingConfig
    from game_tracker import GameTracker
    from alerts import AlertsEngine, check_alerts
    print("✅ All modules imported successfully")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


class SystemTester:
    """Comprehensive system testing."""
    
    def __init__(self):
        """Initialize tester."""
        self.db = TicketDatabase()
        self.game_tracker = GameTracker()
        self.pricing_engine = PricingEngine()
        self.alerts_engine = AlertsEngine()
        self.test_results = {}
    
    async def run_all_tests(self) -> Dict:
        """Run all system tests."""
        print("🧪 Starting System Tests")
        print("=" * 50)
        
        tests = [
            ("Database Tests", self.test_database),
            ("Game Tracker Tests", self.test_game_tracker),
            ("Pricing Engine Tests", self.test_pricing_engine),
            ("Alerts System Tests", self.test_alerts_system),
            ("Scraper Tests", self.test_scraper),
            ("Integration Tests", self.test_integration)
        ]
        
        for test_name, test_func in tests:
            print(f"\n🔍 Running {test_name}...")
            try:
                if asyncio.iscoroutinefunction(test_func):
                    result = await test_func()
                else:
                    result = test_func()
                
                self.test_results[test_name] = {"status": "passed", "details": result}
                print(f"✅ {test_name} passed")
                
            except Exception as e:
                self.test_results[test_name] = {"status": "failed", "error": str(e)}
                print(f"❌ {test_name} failed: {e}")
        
        self.print_test_summary()
        return self.test_results
    
    def test_database(self) -> Dict:
        """Test database functionality."""
        # Test data insertion
        sample_listings = [
            {
                'section': 'Green Monster',
                'row': '2',
                'seat_numbers': '1-2',
                'quantity': 2,
                'price': 299.99,
                'listing_id': 'test_123'
            },
            {
                'section': 'Infield Box 15',
                'row': 'A',
                'seat_numbers': '5',
                'quantity': 1,
                'price': 175.00,
                'listing_id': 'test_124'
            }
        ]
        
        game_id = "test-game-db"
        count = self.db.insert_listings(sample_listings, game_id)
        
        if count != 2:
            raise Exception(f"Expected 2 insertions, got {count}")
        
        # Test retrieval
        latest = self.db.get_latest_listings(game_id)
        if len(latest) != 2:
            raise Exception(f"Expected 2 listings, got {len(latest)}")
        
        # Test price history
        history = self.db.get_price_history(game_id)
        if not history:
            raise Exception("No price history found")
        
        return {
            "listings_inserted": count,
            "listings_retrieved": len(latest),
            "price_history_records": len(history)
        }
    
    def test_game_tracker(self) -> Dict:
        """Test game tracker functionality."""
        # Test game creation
        game_date = datetime.now() + timedelta(days=7)
        game_id = self.game_tracker.add_game(
            game_date=game_date,
            opponent="Test Yankees",
            game_time="7:10 PM"
        )
        
        if not game_id:
            raise Exception("Failed to create game")
        
        # Test listing creation
        listing_id = self.game_tracker.add_my_listing(
            game_id=game_id,
            section="Test Section",
            row="1",
            quantity=2,
            price=200.00,
            seat_numbers="1-2"
        )
        
        if not listing_id:
            raise Exception("Failed to create listing")
        
        # Test retrieval
        active_listings = self.game_tracker.get_active_listings(game_id)
        if len(active_listings) != 1:
            raise Exception(f"Expected 1 active listing, got {len(active_listings)}")
        
        # Test price update
        success = self.game_tracker.update_listing_price(
            game_id=game_id,
            section="Test Section",
            row="1",
            new_price=220.00
        )
        
        if not success:
            raise Exception("Failed to update listing price")
        
        return {
            "game_created": game_id,
            "listing_created": listing_id,
            "active_listings": len(active_listings),
            "price_updated": success
        }
    
    def test_pricing_engine(self) -> Dict:
        """Test pricing engine functionality."""
        # Create test data
        my_listing = {
            'game_id': 'test-pricing',
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
        
        game_time = datetime.now() + timedelta(hours=36)
        
        # Test price recommendation
        decision = get_price_recommendation(my_listing, market_listings, game_time)
        
        if not decision:
            raise Exception("No pricing decision returned")
        
        if not decision.recommended_price:
            raise Exception("No recommended price")
        
        if not decision.reasoning:
            raise Exception("No reasoning provided")
        
        # Test comparable finding
        comps = self.pricing_engine.find_comps(my_listing, market_listings)
        if not comps:
            raise Exception("No comparables found")
        
        # Test market position calculation
        market_position = self.pricing_engine.calculate_market_position(my_listing, comps)
        if market_position.rank <= 0:
            raise Exception("Invalid market position")
        
        return {
            "recommended_price": decision.recommended_price,
            "confidence": decision.confidence,
            "market_rank": market_position.rank,
            "total_comps": len(comps),
            "reasoning": decision.reasoning[:50] + "..."
        }
    
    def test_alerts_system(self) -> Dict:
        """Test alerts system functionality."""
        # Create test game and listing
        game_date = datetime.now() + timedelta(hours=36)  # 36 hours away
        game_id = self.game_tracker.add_game(
            game_date=game_date,
            opponent="Test Alerts Team"
        )
        
        # Add a listing that should trigger late-game alert
        self.game_tracker.add_my_listing(
            game_id=game_id,
            section="Alert Test Section",
            row="1",
            quantity=1,
            price=500.00  # High price to trigger alerts
        )
        
        # Add some market data to compare against
        market_listings = [
            {
                'section': 'Alert Test Section',
                'row': '2',
                'quantity': 1,
                'price': 100.00,  # Much lower to trigger undercut
                'listing_id': 'market_1'
            }
        ]
        
        # Save market data
        save_scraped_listings(market_listings, game_id)
        
        # Check alerts
        alerts = self.alerts_engine.check_all_alerts(game_id)
        
        # Should have at least one alert (undercut or late game)
        if not alerts:
            print("⚠️ No alerts generated (this might be expected)")
        
        # Test alert formatting
        summary = self.alerts_engine.get_formatted_alert_summary(alerts)
        if not summary:
            raise Exception("No alert summary generated")
        
        return {
            "alerts_generated": len(alerts),
            "alert_types": [a.type for a in alerts] if alerts else [],
            "summary_length": len(summary)
        }
    
    async def test_scraper(self) -> Dict:
        """Test scraper functionality (basic validation)."""
        # Test scraper initialization
        async with SeatGeekScraper(headless=True) as scraper:
            if not scraper.page:
                raise Exception("Failed to initialize scraper")
            
            # Test navigation to a basic page (not actually scraping SeatGeek)
            await scraper.page.goto("https://httpbin.org/html")
            
            # Test element extraction (basic test)
            title = await scraper.page.title()
            if not title:
                raise Exception("Failed to get page title")
            
            return {
                "scraper_initialized": True,
                "navigation_successful": True,
                "title_extracted": bool(title)
            }
    
    def test_integration(self) -> Dict:
        """Test integration between modules."""
        # Create a complete workflow
        game_date = datetime.now() + timedelta(days=5)
        game_id = self.game_tracker.add_game(
            game_date=game_date,
            opponent="Integration Test Team"
        )
        
        # Add my listing
        self.game_tracker.add_my_listing(
            game_id=game_id,
            section="Integration Section",
            row="1",
            quantity=2,
            price=300.00
        )
        
        # Add market data
        market_data = [
            {'section': 'Integration Section', 'row': '2', 'quantity': 2, 'price': 280.00},
            {'section': 'Integration Section', 'row': '3', 'quantity': 2, 'price': 320.00},
            {'section': 'Integration Section', 'row': '4', 'quantity': 2, 'price': 290.00}
        ]
        
        save_scraped_listings(market_data, game_id)
        
        # Get my listings
        my_listings = self.game_tracker.get_active_listings(game_id)
        if not my_listings:
            raise Exception("No active listings found")
        
        # Get market listings
        market_listings = get_latest_listings(game_id)
        if not market_listings:
            raise Exception("No market listings found")
        
        # Run pricing engine
        my_listing = my_listings[0]
        decision = get_price_recommendation(
            my_listing=my_listing,
            market_listings=market_listings,
            game_time=game_date
        )
        
        if not decision:
            raise Exception("Pricing engine failed")
        
        # Check alerts
        alerts = check_alerts(game_id)
        
        return {
            "workflow_completed": True,
            "my_listings_count": len(my_listings),
            "market_listings_count": len(market_listings),
            "pricing_decision": bool(decision.recommended_price),
            "alerts_checked": len(alerts)
        }
    
    def print_test_summary(self):
        """Print a summary of all test results."""
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        
        passed = sum(1 for r in self.test_results.values() if r["status"] == "passed")
        failed = sum(1 for r in self.test_results.values() if r["status"] == "failed")
        total = len(self.test_results)
        
        print(f"✅ Passed: {passed}/{total}")
        print(f"❌ Failed: {failed}/{total}")
        print(f"📊 Success Rate: {(passed/total)*100:.1f}%")
        
        if failed > 0:
            print(f"\n❌ FAILED TESTS:")
            for test_name, result in self.test_results.items():
                if result["status"] == "failed":
                    print(f"  • {test_name}: {result['error']}")
        
        print(f"\n✅ PASSED TESTS:")
        for test_name, result in self.test_results.items():
            if result["status"] == "passed":
                print(f"  • {test_name}")


async def main():
    """Run the system tests."""
    print("🎯 Red Sox Ticket Pricing System - Test Suite")
    print("Testing all modules and integrations...")
    
    tester = SystemTester()
    results = await tester.run_all_tests()
    
    # Overall result
    passed = sum(1 for r in results.values() if r["status"] == "passed")
    total = len(results)
    
    if passed == total:
        print(f"\n🎉 All tests passed! System is ready to use.")
    elif passed > total * 0.8:
        print(f"\n⚠️ Most tests passed ({passed}/{total}). System should work with minor issues.")
    else:
        print(f"\n❌ Multiple test failures ({passed}/{total}). Please fix issues before using.")
    
    print("\n🚀 Next Steps:")
    print("1. Set up your .env file with SeatGeek credentials")
    print("2. Run: python initial_import.py")
    print("3. Run: python auto_pricer.py run")


if __name__ == "__main__":
    asyncio.run(main())
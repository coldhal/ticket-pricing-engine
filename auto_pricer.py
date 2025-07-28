"""
Auto-pricing script that automates the full ticket pricing workflow.
Scrapes market data, runs pricing engine, and updates SeatGeek listings.
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict
from dotenv import load_dotenv

# Import our custom modules
from scraper import scrape_seatgeek_event
from database import save_scraped_listings, get_latest_listings
from pricing_engine import get_price_recommendation, PricingConfig
from seatgeek_automation import update_ticket_price
from game_tracker import GameTracker, get_active_listings

# Load environment variables
load_dotenv()


class AutoPricer:
    """Main automation class for ticket pricing workflow."""
    
    def __init__(self, config_file: str = "games_config.json"):
        """
        Initialize auto pricer with configuration.
        
        Args:
            config_file: Path to games configuration file
        """
        self.config_file = config_file
        self.game_tracker = GameTracker()
        self.pricing_config = PricingConfig()
        self.updates_summary = []
        
        # Load or create games configuration
        self.games_config = self._load_games_config()
    
    def _load_games_config(self) -> Dict:
        """Load games configuration file or create default."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ Error loading config file: {e}")
        
        # Create default configuration
        default_config = {
            "tracked_games": [
                {
                    "game_id": "red-sox-vs-yankees-2024-06-15",
                    "url": "https://seatgeek.com/red-sox-vs-yankees-tickets/6-15-2024-boston-massachusetts-fenway-park/mlb/5678901",
                    "game_date": "2024-06-15T19:10:00",
                    "opponent": "New York Yankees",
                    "enabled": True
                },
                {
                    "game_id": "red-sox-vs-blue-jays-2024-06-22",
                    "url": "https://seatgeek.com/red-sox-vs-blue-jays-tickets/6-22-2024-boston-massachusetts-fenway-park/mlb/5678902",
                    "game_date": "2024-06-22T13:35:00",
                    "opponent": "Toronto Blue Jays",
                    "enabled": True
                }
            ],
            "pricing_settings": {
                "aggressiveness": 0.7,
                "price_floor_buffer": 0.95,
                "round_to_nearest": 5
            },
            "scraping_settings": {
                "headless": True,
                "max_retries": 3
            }
        }
        
        # Save default config
        try:
            with open(self.config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
            print(f"✅ Created default config file: {self.config_file}")
        except Exception as e:
            print(f"⚠️ Could not save config file: {e}")
        
        return default_config
    
    async def run_once(self) -> Dict:
        """
        Run the complete pricing workflow once.
        
        Returns:
            Summary dictionary with results
        """
        print("🚀 Starting Auto-Pricing Workflow")
        print("=" * 50)
        
        start_time = datetime.now()
        summary = {
            'start_time': start_time.isoformat(),
            'games_processed': 0,
            'listings_scraped': 0,
            'prices_updated': 0,
            'errors': [],
            'updates': []
        }
        
        try:
            # Step 1: Process each tracked game
            tracked_games = self.games_config.get('tracked_games', [])
            enabled_games = [g for g in tracked_games if g.get('enabled', True)]
            
            print(f"📋 Processing {len(enabled_games)} enabled games...")
            
            for game_config in enabled_games:
                try:
                    await self._process_single_game(game_config, summary)
                    summary['games_processed'] += 1
                except Exception as e:
                    error_msg = f"Error processing game {game_config.get('game_id', 'unknown')}: {e}"
                    print(f"❌ {error_msg}")
                    summary['errors'].append(error_msg)
            
            # Step 2: Print final summary
            self._print_summary(summary)
            
        except Exception as e:
            error_msg = f"Critical error in workflow: {e}"
            print(f"❌ {error_msg}")
            summary['errors'].append(error_msg)
        
        summary['end_time'] = datetime.now().isoformat()
        summary['duration_minutes'] = (datetime.now() - start_time).total_seconds() / 60
        
        return summary
    
    async def _process_single_game(self, game_config: Dict, summary: Dict):
        """Process a single game through the complete workflow."""
        game_id = game_config['game_id']
        game_url = game_config['url']
        game_date_str = game_config['game_date']
        
        print(f"\n🎮 Processing Game: {game_id}")
        print(f"📅 Date: {game_date_str}")
        
        # Parse game date
        game_date = datetime.fromisoformat(game_date_str.replace('Z', '+00:00'))
        
        # Step 1: Scrape current market listings
        print("🕷️ Scraping market listings...")
        try:
            market_listings = await scrape_seatgeek_event(game_url, headless=True)
            
            if not market_listings:
                print("⚠️ No market listings found - skipping game")
                return
            
            print(f"✅ Scraped {len(market_listings)} market listings")
            summary['listings_scraped'] += len(market_listings)
            
            # Save to database
            save_scraped_listings(market_listings, game_id, game_url)
            
        except Exception as e:
            raise Exception(f"Scraping failed: {e}")
        
        # Step 2: Get my active listings for this game
        print("📋 Getting my active listings...")
        my_listings = get_active_listings(game_id)
        
        if not my_listings:
            print("ℹ️ No active listings for this game")
            return
        
        print(f"🎫 Found {len(my_listings)} active listings")
        
        # Step 3: Process each of my listings
        for my_listing in my_listings:
            try:
                await self._process_single_listing(my_listing, market_listings, game_date, summary)
            except Exception as e:
                error_msg = f"Error processing listing {my_listing.get('section', 'unknown')}: {e}"
                print(f"❌ {error_msg}")
                summary['errors'].append(error_msg)
    
    async def _process_single_listing(self, my_listing: Dict, market_listings: List[Dict], 
                                    game_date: datetime, summary: Dict):
        """Process a single listing through pricing and updating."""
        section = my_listing['section']
        row = my_listing['row']
        current_price = my_listing['current_price']
        
        print(f"\n💰 Processing Listing: {section} Row {row}")
        print(f"💵 Current Price: ${current_price:.2f}")
        
        # Step 1: Get price recommendation
        try:
            decision = get_price_recommendation(
                my_listing=my_listing,
                market_listings=market_listings,
                game_time=game_date,
                config=self.pricing_config
            )
        except Exception as e:
            raise Exception(f"Pricing engine failed: {e}")
        
        recommended_price = decision.recommended_price
        price_change = recommended_price - current_price
        
        print(f"🤖 Recommended Price: ${recommended_price:.2f}")
        print(f"📊 Price Change: ${price_change:+.2f}")
        print(f"📈 Market Rank: {decision.market_position.rank} of {decision.market_position.total_comps + 1}")
        print(f"🎯 Confidence: {decision.confidence:.0%}")
        print(f"💭 Reasoning: {decision.reasoning}")
        
        # Step 2: Decide whether to update price
        should_update = self._should_update_price(current_price, recommended_price, decision)
        
        if not should_update:
            print("✋ No update needed - price is optimal")
            return
        
        # Step 3: Update price on SeatGeek
        print(f"🔄 Updating price to ${recommended_price:.2f}...")
        
        try:
            success = await update_ticket_price(
                listing_id=my_listing.get('listing_id'),
                new_price=recommended_price,
                section=section,
                row=row,
                quantity=my_listing.get('quantity', 1)
            )
            
            if success:
                # Update price in our database
                self.game_tracker.update_listing_price(
                    my_listing['game_id'], section, row, recommended_price
                )
                
                print(f"✅ Successfully updated price: ${current_price:.2f} → ${recommended_price:.2f}")
                summary['prices_updated'] += 1
                
                # Log the update
                update_record = {
                    'game_id': my_listing['game_id'],
                    'section': section,
                    'row': row,
                    'old_price': current_price,
                    'new_price': recommended_price,
                    'change': price_change,
                    'reasoning': decision.reasoning,
                    'confidence': decision.confidence
                }
                summary['updates'].append(update_record)
                
            else:
                raise Exception("SeatGeek update failed")
                
        except Exception as e:
            raise Exception(f"Price update failed: {e}")
    
    def _should_update_price(self, current_price: float, recommended_price: float, 
                           decision) -> bool:
        """Determine if we should update the price based on various criteria."""
        price_change = abs(recommended_price - current_price)
        
        # Don't update if change is very small
        if price_change < 2.0:  # Less than $2 change
            return False
        
        # Don't update if confidence is too low
        if decision.confidence < 0.6:  # Less than 60% confidence
            return False
        
        # Don't update if we're already ranked #1 and recommended price is higher
        if (decision.market_position.rank == 1 and 
            recommended_price > current_price):
            return False
        
        return True
    
    def _print_summary(self, summary: Dict):
        """Print a formatted summary of the workflow results."""
        print("\n" + "=" * 50)
        print("📊 AUTO-PRICING SUMMARY")
        print("=" * 50)
        
        print(f"⏱️ Duration: {summary.get('duration_minutes', 0):.1f} minutes")
        print(f"🎮 Games Processed: {summary['games_processed']}")
        print(f"🕷️ Listings Scraped: {summary['listings_scraped']}")
        print(f"💰 Prices Updated: {summary['prices_updated']}")
        print(f"❌ Errors: {len(summary['errors'])}")
        
        if summary['updates']:
            print(f"\n🔄 PRICE UPDATES:")
            for update in summary['updates']:
                change_symbol = "↗️" if update['change'] > 0 else "↘️"
                print(f"  {change_symbol} {update['section']} Row {update['row']}: "
                      f"${update['old_price']:.2f} → ${update['new_price']:.2f} "
                      f"({update['confidence']:.0%} confidence)")
        
        if summary['errors']:
            print(f"\n❌ ERRORS:")
            for error in summary['errors'][:5]:  # Show first 5 errors
                print(f"  • {error}")
            
            if len(summary['errors']) > 5:
                print(f"  ... and {len(summary['errors']) - 5} more errors")
    
    def _log_workflow_results(self, summary: Dict):
        """Log workflow results to a file for analysis."""
        try:
            log_file = "auto_pricer_log.json"
            
            # Load existing log or create new
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    log_data = json.load(f)
            else:
                log_data = []
            
            # Add this run
            log_data.append(summary)
            
            # Keep only last 100 runs
            log_data = log_data[-100:]
            
            # Save updated log
            with open(log_file, 'w') as f:
                json.dump(log_data, f, indent=2)
                
        except Exception as e:
            print(f"⚠️ Failed to log results: {e}")


# Standalone function for easy scheduling
async def run_once() -> Dict:
    """
    Run the auto-pricing workflow once.
    This function can be called by schedulers or other scripts.
    
    Returns:
        Summary dictionary with results
    """
    auto_pricer = AutoPricer()
    return await auto_pricer.run_once()


# Configuration management functions
def update_game_config(game_id: str, **kwargs):
    """Update configuration for a specific game."""
    config_file = "games_config.json"
    
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
        else:
            config = {"tracked_games": []}
        
        # Find and update the game
        for game in config['tracked_games']:
            if game['game_id'] == game_id:
                game.update(kwargs)
                break
        else:
            # Add new game if not found
            new_game = {'game_id': game_id, **kwargs}
            config['tracked_games'].append(new_game)
        
        # Save updated config
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"✅ Updated config for game: {game_id}")
        
    except Exception as e:
        print(f"❌ Failed to update config: {e}")


def disable_game(game_id: str):
    """Disable auto-pricing for a specific game."""
    update_game_config(game_id, enabled=False)


def enable_game(game_id: str):
    """Enable auto-pricing for a specific game."""
    update_game_config(game_id, enabled=True)


# Command line interface
async def main():
    """Main entry point for command line usage."""
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "run":
            summary = await run_once()
            print(f"\n🏁 Workflow completed with {summary['prices_updated']} updates")
        
        elif command == "config":
            if len(sys.argv) > 2:
                game_id = sys.argv[2]
                print(f"Game config for {game_id}:")
                # Show current config for the game
            else:
                print("Usage: python auto_pricer.py config <game_id>")
        
        elif command == "disable":
            if len(sys.argv) > 2:
                game_id = sys.argv[2]
                disable_game(game_id)
            else:
                print("Usage: python auto_pricer.py disable <game_id>")
        
        elif command == "enable":
            if len(sys.argv) > 2:
                game_id = sys.argv[2]
                enable_game(game_id)
            else:
                print("Usage: python auto_pricer.py enable <game_id>")
        
        else:
            print("Unknown command. Available commands: run, config, disable, enable")
    
    else:
        # Default: run the workflow
        print("🚀 Running auto-pricing workflow...")
        summary = await run_once()
        
        if summary['prices_updated'] > 0:
            print(f"✅ Updated {summary['prices_updated']} listing prices")
        else:
            print("ℹ️ No price updates needed")


if __name__ == "__main__":
    asyncio.run(main())
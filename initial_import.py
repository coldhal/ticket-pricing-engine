"""
Initial import script to scrape existing Red Sox listings from SeatGeek account.
Populates the game tracker database with current listings.
"""

import asyncio
import re
from datetime import datetime
from typing import List, Dict
from seatgeek_automation import SeatGeekAutomation
from game_tracker import GameTracker


class InitialImporter:
    """Imports existing listings from SeatGeek account."""
    
    def __init__(self):
        """Initialize the importer."""
        self.game_tracker = GameTracker()
        self.imported_games = {}
        self.imported_listings = []
    
    async def import_all_listings(self) -> Dict:
        """
        Import all Red Sox listings from SeatGeek account.
        
        Returns:
            Summary dictionary with import results
        """
        print("🚀 Starting Initial Import from SeatGeek")
        print("=" * 50)
        
        start_time = datetime.now()
        summary = {
            'start_time': start_time.isoformat(),
            'games_imported': 0,
            'listings_imported': 0,
            'errors': [],
            'games': {},
            'listings': []
        }
        
        try:
            async with SeatGeekAutomation(headless=True) as automation:
                # Step 1: Login to SeatGeek
                print("🔐 Logging into SeatGeek...")
                if not await automation.login():
                    raise Exception("Failed to login to SeatGeek")
                
                # Step 2: Navigate to listings page
                print("📋 Navigating to My Listings...")
                if not await automation.navigate_to_my_listings():
                    raise Exception("Failed to navigate to listings page")
                
                # Step 3: Scrape all listings
                print("🕷️ Scraping all listings...")
                raw_listings = await automation.get_all_my_listings()
                
                if not raw_listings:
                    print("⚠️ No listings found")
                    return summary
                
                print(f"✅ Found {len(raw_listings)} raw listings")
                
                # Step 4: Process and categorize listings
                print("🔍 Processing listings...")
                processed_listings = self._process_raw_listings(raw_listings)
                
                # Step 5: Filter for Red Sox games only
                red_sox_listings = self._filter_red_sox_listings(processed_listings)
                
                if not red_sox_listings:
                    print("⚠️ No Red Sox listings found")
                    return summary
                
                print(f"⚾ Found {len(red_sox_listings)} Red Sox listings")
                
                # Step 6: Import games and listings
                await self._import_games_and_listings(red_sox_listings, summary)
                
                # Step 7: Print summary
                self._print_import_summary(summary)
        
        except Exception as e:
            error_msg = f"Import failed: {e}"
            print(f"❌ {error_msg}")
            summary['errors'].append(error_msg)
        
        summary['end_time'] = datetime.now().isoformat()
        summary['duration_minutes'] = (datetime.now() - start_time).total_seconds() / 60
        
        return summary
    
    def _process_raw_listings(self, raw_listings: List[Dict]) -> List[Dict]:
        """Process raw listing data into structured format."""
        processed = []
        
        for i, raw_listing in enumerate(raw_listings):
            try:
                listing = self._extract_listing_details(raw_listing, i)
                if listing:
                    processed.append(listing)
            except Exception as e:
                print(f"⚠️ Error processing listing {i}: {e}")
        
        return processed
    
    def _extract_listing_details(self, raw_listing: Dict, index: int) -> Dict:
        """Extract structured details from raw listing data."""
        text = raw_listing.get('full_text', '')
        
        if not text:
            return None
        
        listing = {
            'index': index,
            'raw_text': text,
            'game_date': None,
            'game_time': None,
            'opponent': None,
            'venue': 'Fenway Park',
            'section': None,
            'row': None,
            'seat_numbers': None,
            'quantity': None,
            'current_price': raw_listing.get('current_price'),
            'listing_id': raw_listing.get('listing_id'),
            'parsed_successfully': False
        }
        
        # Extract game information
        game_info = self._extract_game_info(text)
        listing.update(game_info)
        
        # Extract ticket details
        ticket_info = self._extract_ticket_info(text)
        listing.update(ticket_info)
        
        # Mark as successfully parsed if we have essential info
        if (listing['game_date'] and listing['section'] and 
            listing['current_price'] and listing['quantity']):
            listing['parsed_successfully'] = True
        
        return listing
    
    def _extract_game_info(self, text: str) -> Dict:
        """Extract game date, time, and opponent from listing text."""
        info = {
            'game_date': None,
            'game_time': None,
            'opponent': None
        }
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Look for date patterns
            date_patterns = [
                r'(\w{3})\s+(\d{1,2}),?\s+(\d{4})',  # "Jun 15, 2024"
                r'(\w{3})\s+(\d{1,2})',               # "Jun 15"
                r'(\d{1,2})/(\d{1,2})/(\d{4})',      # "6/15/2024"
                r'(\d{4})-(\d{2})-(\d{2})'           # "2024-06-15"
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, line)
                if match:
                    try:
                        # Try to parse the date
                        if len(match.groups()) == 3:
                            if match.group(1).isalpha():  # Month name
                                month_str = match.group(1)
                                day = int(match.group(2))
                                year = int(match.group(3)) if match.group(3) else datetime.now().year
                                
                                # Convert month name to number
                                month_map = {
                                    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
                                    'may': 5, 'jun': 6, 'jul': 7, 'aug': 8,
                                    'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
                                }
                                month = month_map.get(month_str.lower()[:3])
                                if month:
                                    info['game_date'] = datetime(year, month, day)
                            else:  # Numeric date
                                if '/' in line:
                                    month, day, year = match.groups()
                                    info['game_date'] = datetime(int(year), int(month), int(day))
                                elif '-' in line:
                                    year, month, day = match.groups()
                                    info['game_date'] = datetime(int(year), int(month), int(day))
                    except:
                        continue
            
            # Look for time patterns
            time_match = re.search(r'(\d{1,2}):(\d{2})\s*(AM|PM)', line, re.IGNORECASE)
            if time_match:
                info['game_time'] = time_match.group(0)
            
            # Look for opponent team names
            team_patterns = [
                r'vs?\s+(.+?)(?:\s|$)',
                r'vs?\s+(\w+)',
                r'red\s*sox\s+vs?\s+(.+?)(?:\s|$)'
            ]
            
            for pattern in team_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match and 'red sox' not in match.group(1).lower():
                    potential_opponent = match.group(1).strip()
                    
                    # Filter out common non-team words
                    skip_words = ['tickets', 'fenway', 'park', 'boston', 'game', 'mlb']
                    if not any(word in potential_opponent.lower() for word in skip_words):
                        info['opponent'] = potential_opponent
        
        return info
    
    def _extract_ticket_info(self, text: str) -> Dict:
        """Extract section, row, seats, and quantity from listing text."""
        info = {
            'section': None,
            'row': None,
            'seat_numbers': None,
            'quantity': None
        }
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Extract section
            section_patterns = [
                r'section\s+([^,\n]+)',
                r'sec\s+([^,\n]+)',
                r'(green\s+monster)',
                r'(pavilion\s+box\s+\d+)',
                r'(infield\s+box\s+\d+)',
                r'(outfield\s+box\s+\d+)',
                r'(grandstand\s+\d+)',
                r'(bleacher\s+\d+)'
            ]
            
            for pattern in section_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    info['section'] = match.group(1).strip()
                    break
            
            # Extract row
            row_patterns = [
                r'row\s+([a-z0-9]+)',
                r'row:\s*([a-z0-9]+)',
                r'\brow\s+([a-z0-9]+)'
            ]
            
            for pattern in row_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    info['row'] = match.group(1).strip()
                    break
            
            # Extract seat numbers
            seat_patterns = [
                r'seats?\s+([0-9\-,\s]+)',
                r'seat:\s*([0-9\-,\s]+)',
                r'\bseat\s+([0-9\-,\s]+)'
            ]
            
            for pattern in seat_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    info['seat_numbers'] = match.group(1).strip()
                    break
            
            # Extract quantity
            qty_patterns = [
                r'(\d+)\s+tickets?',
                r'(\d+)\s+seats?',
                r'qty:?\s*(\d+)',
                r'quantity:?\s*(\d+)'
            ]
            
            for pattern in qty_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    info['quantity'] = int(match.group(1))
                    break
        
        # If no quantity found, try to infer from seat numbers
        if not info['quantity'] and info['seat_numbers']:
            seats = info['seat_numbers'].replace(' ', '').split(',')
            info['quantity'] = len(seats)
        
        # Default quantity to 1 if still not found
        if not info['quantity']:
            info['quantity'] = 1
        
        return info
    
    def _filter_red_sox_listings(self, listings: List[Dict]) -> List[Dict]:
        """Filter listings to only include Red Sox games."""
        red_sox_listings = []
        
        for listing in listings:
            if not listing.get('parsed_successfully'):
                continue
            
            # Check if this is a Red Sox game
            text = listing.get('raw_text', '').lower()
            
            # Look for Red Sox indicators
            red_sox_indicators = [
                'red sox',
                'redsox', 
                'fenway park',
                'boston'
            ]
            
            # Skip if it's clearly not a Red Sox game
            if not any(indicator in text for indicator in red_sox_indicators):
                continue
            
            # Skip if it's an away game (not at Fenway)
            away_indicators = ['@', 'at yankee stadium', 'at rogers centre']
            if any(indicator in text for indicator in away_indicators):
                continue
            
            red_sox_listings.append(listing)
        
        return red_sox_listings
    
    async def _import_games_and_listings(self, listings: List[Dict], summary: Dict):
        """Import games and listings into the database."""
        print("💾 Importing into database...")
        
        # Group listings by game
        games_dict = {}
        for listing in listings:
            game_date = listing['game_date']
            opponent = listing.get('opponent', 'Unknown Opponent')
            
            # Create game key
            if game_date:
                game_key = f"{game_date.strftime('%Y-%m-%d')}_{opponent}"
            else:
                game_key = f"unknown_{opponent}"
            
            if game_key not in games_dict:
                games_dict[game_key] = {
                    'game_date': game_date,
                    'opponent': opponent,
                    'listings': []
                }
            
            games_dict[game_key]['listings'].append(listing)
        
        # Import each game and its listings
        for game_key, game_data in games_dict.items():
            try:
                # Add game to tracker
                game_id = self.game_tracker.add_game(
                    game_date=game_data['game_date'],
                    opponent=game_data['opponent'],
                    venue='Fenway Park'
                )
                
                summary['games_imported'] += 1
                summary['games'][game_id] = {
                    'opponent': game_data['opponent'],
                    'date': game_data['game_date'].isoformat() if game_data['game_date'] else None,
                    'listings_count': len(game_data['listings'])
                }
                
                # Add listings for this game
                for listing in game_data['listings']:
                    try:
                        listing_id = self.game_tracker.add_my_listing(
                            game_id=game_id,
                            section=listing['section'],
                            row=listing.get('row', ''),
                            quantity=listing['quantity'],
                            price=listing['current_price'],
                            seat_numbers=listing.get('seat_numbers'),
                            listing_id=listing.get('listing_id')
                        )
                        
                        summary['listings_imported'] += 1
                        summary['listings'].append({
                            'game_id': game_id,
                            'section': listing['section'],
                            'row': listing.get('row'),
                            'quantity': listing['quantity'],
                            'price': listing['current_price']
                        })
                        
                    except Exception as e:
                        error_msg = f"Failed to import listing {listing['section']}: {e}"
                        print(f"❌ {error_msg}")
                        summary['errors'].append(error_msg)
                
            except Exception as e:
                error_msg = f"Failed to import game {game_data['opponent']}: {e}"
                print(f"❌ {error_msg}")
                summary['errors'].append(error_msg)
    
    def _print_import_summary(self, summary: Dict):
        """Print a formatted summary of the import results."""
        print("\n" + "=" * 50)
        print("📊 IMPORT SUMMARY")
        print("=" * 50)
        
        print(f"⏱️ Duration: {summary.get('duration_minutes', 0):.1f} minutes")
        print(f"🎮 Games Imported: {summary['games_imported']}")
        print(f"🎫 Listings Imported: {summary['listings_imported']}")
        print(f"❌ Errors: {len(summary['errors'])}")
        
        if summary['games']:
            print(f"\n📅 IMPORTED GAMES:")
            for game_id, game_info in summary['games'].items():
                date_str = game_info['date'][:10] if game_info['date'] else 'Unknown'
                print(f"  • {date_str} vs {game_info['opponent']} ({game_info['listings_count']} listings)")
        
        if summary['listings']:
            print(f"\n🎫 SAMPLE LISTINGS:")
            for listing in summary['listings'][:5]:  # Show first 5
                print(f"  • {listing['section']} Row {listing['row']} - "
                      f"Qty {listing['quantity']} - ${listing['price']:.2f}")
            
            if len(summary['listings']) > 5:
                print(f"  ... and {len(summary['listings']) - 5} more listings")
        
        if summary['errors']:
            print(f"\n❌ ERRORS:")
            for error in summary['errors'][:3]:  # Show first 3 errors
                print(f"  • {error}")
            
            if len(summary['errors']) > 3:
                print(f"  ... and {len(summary['errors']) - 3} more errors")


# Standalone function for easy execution
async def import_my_listings() -> Dict:
    """
    Import all Red Sox listings from SeatGeek account.
    
    Returns:
        Summary dictionary with import results
    """
    importer = InitialImporter()
    return await importer.import_all_listings()


# Command line interface
async def main():
    """Main entry point for command line usage."""
    print("🎫 Red Sox Ticket Import Tool")
    print("Importing your existing SeatGeek listings...")
    
    try:
        summary = await import_my_listings()
        
        if summary['listings_imported'] > 0:
            print(f"\n✅ Successfully imported {summary['listings_imported']} listings "
                  f"across {summary['games_imported']} games!")
        else:
            print("\n⚠️ No listings were imported. Check your SeatGeek account.")
            
    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        print("Please check your SeatGeek credentials and try again.")


if __name__ == "__main__":
    asyncio.run(main())
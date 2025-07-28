"""
SeatGeek automation module for managing ticket listings.
Uses Playwright to log in and update ticket prices.
"""

import os
import asyncio
from datetime import datetime
from typing import Dict, Optional, List
from playwright.async_api import async_playwright, Page, Browser
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class SeatGeekAutomation:
    """Automates SeatGeek account management and price updates."""
    
    def __init__(self, headless: bool = True):
        """
        Initialize SeatGeek automation.
        
        Args:
            headless: Whether to run browser in headless mode
        """
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.logged_in = False
        
        # Get credentials from environment
        self.email = os.getenv('SEATGEEK_EMAIL')
        self.password = os.getenv('SEATGEEK_PASSWORD')
        
        if not self.email or not self.password:
            raise ValueError("SeatGeek credentials not found in environment variables")
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.playwright = await async_playwright().__aenter__()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.page = await self.browser.new_page()
        
        # Set user agent and viewport
        await self.page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        await self.page.set_viewport_size({"width": 1280, "height": 720})
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.browser:
            await self.browser.close()
        await self.playwright.__aexit__(exc_type, exc_val, exc_tb)
    
    async def login(self) -> bool:
        """
        Log into SeatGeek account.
        
        Returns:
            True if login successful, False otherwise
        """
        try:
            print("🔐 Logging into SeatGeek...")
            
            # Navigate to login page
            await self.page.goto("https://seatgeek.com/login", wait_until="networkidle")
            
            # Wait for login form to load
            await self.page.wait_for_selector('input[type="email"], input[name="email"]', timeout=10000)
            
            # Fill in email
            email_selector = 'input[type="email"], input[name="email"], #email'
            await self.page.fill(email_selector, self.email)
            
            # Fill in password
            password_selector = 'input[type="password"], input[name="password"], #password'
            await self.page.fill(password_selector, self.password)
            
            # Submit login form
            submit_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("Log In")',
                'button:has-text("Sign In")'
            ]
            
            for selector in submit_selectors:
                try:
                    submit_button = await self.page.query_selector(selector)
                    if submit_button:
                        await submit_button.click()
                        break
                except:
                    continue
            
            # Wait for redirect after login
            await self.page.wait_for_load_state("networkidle")
            
            # Check if login was successful
            # Look for user account indicators
            success_indicators = [
                'a[href*="/account"]',
                'button:has-text("Account")',
                'a:has-text("My Tickets")',
                '[data-testid="user-menu"]'
            ]
            
            for indicator in success_indicators:
                try:
                    element = await self.page.query_selector(indicator)
                    if element:
                        self.logged_in = True
                        print("✅ Successfully logged into SeatGeek")
                        return True
                except:
                    continue
            
            # Check for error messages
            error_selectors = [
                '.error', '.alert-error', '[class*="error"]',
                'div:has-text("Invalid")', 'div:has-text("incorrect")'
            ]
            
            for selector in error_selectors:
                try:
                    error_element = await self.page.query_selector(selector)
                    if error_element:
                        error_text = await error_element.inner_text()
                        print(f"❌ Login error: {error_text}")
                        return False
                except:
                    continue
            
            print("⚠️ Login status unclear - continuing...")
            self.logged_in = True
            return True
            
        except Exception as e:
            print(f"❌ Login failed: {e}")
            return False
    
    async def navigate_to_my_listings(self) -> bool:
        """
        Navigate to the user's ticket listings page.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            print("📋 Navigating to My Listings...")
            
            # Try different URLs for listings page
            listings_urls = [
                "https://seatgeek.com/account/listings",
                "https://seatgeek.com/sell/listings",
                "https://seatgeek.com/my-tickets",
                "https://seatgeek.com/account"
            ]
            
            for url in listings_urls:
                try:
                    await self.page.goto(url, wait_until="networkidle")
                    
                    # Check if we're on a listings page
                    listings_indicators = [
                        'div:has-text("My Listings")',
                        'h1:has-text("Listings")',
                        '[data-testid="listing-card"]',
                        '.listing-card',
                        'table:has-text("Section")'
                    ]
                    
                    for indicator in listings_indicators:
                        element = await self.page.query_selector(indicator)
                        if element:
                            print(f"✅ Successfully navigated to listings page: {url}")
                            return True
                    
                except Exception as e:
                    print(f"⚠️ Failed to load {url}: {e}")
                    continue
            
            # If direct URLs don't work, try navigating through account menu
            await self._navigate_through_menu()
            return True
            
        except Exception as e:
            print(f"❌ Failed to navigate to listings: {e}")
            return False
    
    async def _navigate_through_menu(self):
        """Navigate to listings through the account menu."""
        try:
            # Look for account/user menu
            menu_selectors = [
                'button:has-text("Account")',
                'a:has-text("Account")',
                '[data-testid="user-menu"]',
                '.user-menu'
            ]
            
            for selector in menu_selectors:
                try:
                    menu = await self.page.query_selector(selector)
                    if menu:
                        await menu.click()
                        await self.page.wait_for_timeout(1000)
                        
                        # Look for listings link in dropdown
                        listings_links = [
                            'a:has-text("My Listings")',
                            'a:has-text("Listings")',
                            'a:has-text("Sell")',
                            'a[href*="listing"]'
                        ]
                        
                        for link_selector in listings_links:
                            link = await self.page.query_selector(link_selector)
                            if link:
                                await link.click()
                                await self.page.wait_for_load_state("networkidle")
                                return
                        break
                except:
                    continue
        except Exception as e:
            print(f"⚠️ Menu navigation failed: {e}")
    
    async def find_listing(self, game_date: str, section: str, row: str, 
                         quantity: int) -> Optional[Dict]:
        """
        Find a specific listing on the page.
        
        Args:
            game_date: Game date string (e.g., "Jun 15")
            section: Section name
            row: Row identifier
            quantity: Number of tickets
            
        Returns:
            Dictionary with listing element and metadata if found
        """
        try:
            print(f"🔍 Looking for listing: {section} Row {row} (Qty: {quantity})")
            
            # Wait for listings to load
            await self.page.wait_for_timeout(2000)
            
            # Find all listing elements
            listing_selectors = [
                '[data-testid="listing-card"]',
                '.listing-card',
                'tr:has-text("' + section + '")',
                'div:has-text("' + section + '")'
            ]
            
            for selector in listing_selectors:
                try:
                    listings = await self.page.query_selector_all(selector)
                    
                    for listing in listings:
                        # Extract listing details
                        listing_text = await listing.inner_text()
                        
                        # Check if this matches our criteria
                        if (section.lower() in listing_text.lower() and
                            str(quantity) in listing_text and
                            (row.lower() in listing_text.lower() or not row)):
                            
                            print(f"✅ Found matching listing")
                            return {
                                'element': listing,
                                'text': listing_text,
                                'section': section,
                                'row': row,
                                'quantity': quantity
                            }
                            
                except Exception as e:
                    print(f"⚠️ Error searching with selector {selector}: {e}")
                    continue
            
            print(f"❌ Listing not found: {section} Row {row}")
            return None
            
        except Exception as e:
            print(f"❌ Error finding listing: {e}")
            return None
    
    async def update_listing_price(self, listing_element, new_price: float) -> bool:
        """
        Update the price of a specific listing.
        
        Args:
            listing_element: The listing element found by find_listing
            new_price: New price to set
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            print(f"💰 Updating price to ${new_price:.2f}...")
            
            # Look for edit button or price field
            edit_selectors = [
                'button:has-text("Edit")',
                'a:has-text("Edit")',
                '[data-testid="edit-listing"]',
                'input[type="number"]',
                'input[name*="price"]'
            ]
            
            # Try to find edit button within the listing
            for selector in edit_selectors:
                try:
                    edit_element = await listing_element.query_selector(selector)
                    if edit_element:
                        await edit_element.click()
                        await self.page.wait_for_timeout(1000)
                        break
                except:
                    continue
            
            # Look for price input field
            price_selectors = [
                'input[type="number"]',
                'input[name*="price"]',
                'input[placeholder*="price"]',
                'input[placeholder*="Price"]'
            ]
            
            price_input = None
            for selector in price_selectors:
                try:
                    price_input = await self.page.query_selector(selector)
                    if price_input:
                        break
                except:
                    continue
            
            if not price_input:
                print("❌ Could not find price input field")
                return False
            
            # Clear and set new price
            await price_input.click()
            await price_input.fill("")  # Clear existing value
            await price_input.fill(str(new_price))
            
            # Look for save/update button
            save_selectors = [
                'button:has-text("Save")',
                'button:has-text("Update")',
                'button[type="submit"]',
                'input[type="submit"]'
            ]
            
            for selector in save_selectors:
                try:
                    save_button = await self.page.query_selector(selector)
                    if save_button:
                        await save_button.click()
                        await self.page.wait_for_timeout(2000)
                        print(f"✅ Price updated to ${new_price:.2f}")
                        return True
                except:
                    continue
            
            print("⚠️ Could not find save button - price may not be saved")
            return False
            
        except Exception as e:
            print(f"❌ Failed to update price: {e}")
            return False
    
    async def get_all_my_listings(self) -> List[Dict]:
        """
        Scrape all of the user's current listings.
        
        Returns:
            List of listing dictionaries
        """
        try:
            print("📋 Scraping all my listings...")
            
            # Navigate to listings if not already there
            if not await self.navigate_to_my_listings():
                return []
            
            # Wait for listings to load
            await self.page.wait_for_timeout(3000)
            
            listings = []
            
            # Try different selectors for listing elements
            listing_selectors = [
                '[data-testid="listing-card"]',
                '.listing-card',
                'tbody tr',  # Table rows
                '.listing-row'
            ]
            
            for selector in listing_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    
                    if elements:
                        print(f"Found {len(elements)} listings with selector: {selector}")
                        
                        for i, element in enumerate(elements):
                            listing_data = await self._extract_listing_data(element, i)
                            if listing_data:
                                listings.append(listing_data)
                        
                        break  # Use first successful selector
                        
                except Exception as e:
                    print(f"⚠️ Error with selector {selector}: {e}")
                    continue
            
            print(f"✅ Scraped {len(listings)} listings")
            return listings
            
        except Exception as e:
            print(f"❌ Failed to get listings: {e}")
            return []
    
    async def _extract_listing_data(self, element, index: int) -> Optional[Dict]:
        """Extract data from a listing element."""
        try:
            text = await element.inner_text()
            
            # Extract basic information using text parsing
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            listing_data = {
                'index': index,
                'full_text': text,
                'game_date': None,
                'opponent': None,
                'section': None,
                'row': None,
                'quantity': None,
                'current_price': None,
                'listing_id': None
            }
            
            # Try to extract structured data
            for line in lines:
                # Look for price patterns
                if '$' in line:
                    import re
                    price_match = re.search(r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)', line)
                    if price_match:
                        listing_data['current_price'] = float(price_match.group(1).replace(',', ''))
                
                # Look for section patterns
                if any(word in line.lower() for word in ['section', 'sec']):
                    listing_data['section'] = line
                
                # Look for row patterns
                if 'row' in line.lower():
                    listing_data['row'] = line
                
                # Look for quantity patterns
                if any(word in line for word in ['ticket', 'seats']):
                    import re
                    qty_match = re.search(r'(\d+)\s*(?:ticket|seat)', line.lower())
                    if qty_match:
                        listing_data['quantity'] = int(qty_match.group(1))
            
            # Try to get listing ID from element attributes
            for attr in ['data-listing-id', 'data-id', 'id']:
                try:
                    value = await element.get_attribute(attr)
                    if value:
                        listing_data['listing_id'] = value
                        break
                except:
                    continue
            
            return listing_data if listing_data['current_price'] else None
            
        except Exception as e:
            print(f"⚠️ Error extracting listing data: {e}")
            return None


async def update_ticket_price(listing_id: str, new_price: float, 
                            game_date: str = None, section: str = None, 
                            row: str = None, quantity: int = None) -> bool:
    """
    Main function to update a ticket listing price.
    
    Args:
        listing_id: SeatGeek listing ID (if available)
        new_price: New price to set
        game_date: Game date for finding listing
        section: Section for finding listing
        row: Row for finding listing  
        quantity: Quantity for finding listing
        
    Returns:
        True if update successful, False otherwise
    """
    try:
        async with SeatGeekAutomation(headless=True) as automation:
            # Login to SeatGeek
            if not await automation.login():
                return False
            
            # Navigate to listings
            if not await automation.navigate_to_my_listings():
                return False
            
            # Find the specific listing
            listing = await automation.find_listing(
                game_date or "", section or "", row or "", quantity or 1
            )
            
            if not listing:
                print(f"❌ Could not find listing to update")
                return False
            
            # Update the price
            success = await automation.update_listing_price(
                listing['element'], new_price
            )
            
            if success:
                print(f"✅ Successfully updated listing price to ${new_price:.2f}")
                
                # Log the update
                log_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'listing_id': listing_id,
                    'section': section,
                    'row': row,
                    'quantity': quantity,
                    'new_price': new_price,
                    'status': 'success'
                }
                _log_price_update(log_entry)
            
            return success
            
    except Exception as e:
        print(f"❌ Price update failed: {e}")
        
        # Log the failure
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'listing_id': listing_id,
            'section': section,
            'row': row,
            'quantity': quantity,
            'new_price': new_price,
            'status': 'failed',
            'error': str(e)
        }
        _log_price_update(log_entry)
        
        return False


def _log_price_update(log_entry: Dict):
    """Log price update attempts to a file."""
    try:
        import json
        
        log_file = "price_updates.log"
        
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
            
    except Exception as e:
        print(f"⚠️ Failed to log update: {e}")


# Example usage
if __name__ == "__main__":
    async def main():
        # Example: Update a specific listing
        success = await update_ticket_price(
            listing_id="12345",
            new_price=275.00,
            section="Green Monster",
            row="2",
            quantity=2
        )
        
        if success:
            print("✅ Price update completed")
        else:
            print("❌ Price update failed")
    
    asyncio.run(main())
"""
SeatGeek ticket scraper using Playwright.
Extracts ticket listing data from SeatGeek event pages.
"""

import asyncio
import re
from datetime import datetime
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Page, Browser
import json


class SeatGeekScraper:
    """Scraper for extracting ticket listings from SeatGeek event pages."""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.playwright = await async_playwright().__aenter__()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.page = await self.browser.new_page()
        
        # Set user agent to avoid detection
        await self.page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.browser:
            await self.browser.close()
        await self.playwright.__aexit__(exc_type, exc_val, exc_tb)
    
    async def scrape_event_listings(self, url: str) -> List[Dict]:
        """
        Scrape all ticket listings from a SeatGeek event page.
        
        Args:
            url: SeatGeek event page URL (e.g., https://seatgeek.com/red-sox-tickets)
            
        Returns:
            List of dictionaries containing listing data
        """
        print(f"🎫 Starting scrape of: {url}")
        
        # Navigate to the event page
        await self.page.goto(url, wait_until="networkidle")
        
        # Wait for listings to load
        await self.page.wait_for_selector('[data-testid="listing-card"]', timeout=10000)
        
        # Handle lazy loading by scrolling to bottom
        await self._handle_lazy_loading()
        
        # Handle pagination if present
        await self._handle_pagination()
        
        # Extract all listing data
        listings = await self._extract_listings()
        
        print(f"✅ Successfully scraped {len(listings)} listings")
        return listings
    
    async def _handle_lazy_loading(self):
        """Scroll through page to trigger lazy loading of all listings."""
        print("📜 Handling lazy-loaded content...")
        
        # Get initial page height
        last_height = await self.page.evaluate("document.body.scrollHeight")
        
        while True:
            # Scroll to bottom
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            
            # Wait for new content to load
            await self.page.wait_for_timeout(2000)
            
            # Check if page height changed (new content loaded)
            new_height = await self.page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        
        print("✅ Finished loading all content")
    
    async def _handle_pagination(self):
        """Handle pagination to load all pages of listings."""
        print("📄 Checking for pagination...")
        
        page_count = 1
        while True:
            # Look for "Next" button or pagination
            next_button = await self.page.query_selector('button[aria-label="Next page"], a[aria-label="Next"]')
            
            if not next_button:
                break
            
            # Check if next button is disabled
            is_disabled = await next_button.get_attribute("disabled")
            if is_disabled:
                break
            
            print(f"📄 Loading page {page_count + 1}...")
            
            # Click next button and wait for new content
            await next_button.click()
            await self.page.wait_for_load_state("networkidle")
            await self.page.wait_for_timeout(2000)
            
            page_count += 1
        
        print(f"✅ Loaded {page_count} page(s) total")
    
    async def _extract_listings(self) -> List[Dict]:
        """Extract listing data from all loaded listing cards."""
        print("🔍 Extracting listing data...")
        
        # Find all listing elements
        listing_elements = await self.page.query_selector_all('[data-testid="listing-card"], .listing-card, .ticket-listing')
        
        if not listing_elements:
            # Fallback: try broader selectors
            listing_elements = await self.page.query_selector_all('.listing, [class*="listing"], [class*="ticket"]')
        
        listings = []
        
        for i, element in enumerate(listing_elements):
            try:
                listing_data = await self._extract_single_listing(element, i)
                if listing_data:
                    listings.append(listing_data)
            except Exception as e:
                print(f"⚠️ Error extracting listing {i}: {e}")
                continue
        
        return listings
    
    async def _extract_single_listing(self, element, index: int) -> Optional[Dict]:
        """Extract data from a single listing element."""
        try:
            # Extract section
            section = await self._extract_text_by_selectors(element, [
                '[data-testid="section"]',
                '.section',
                '[class*="section"]',
                'span:has-text("Section")',
                'div:has-text("Sec")'
            ])
            
            # Extract row
            row = await self._extract_text_by_selectors(element, [
                '[data-testid="row"]',
                '.row',
                '[class*="row"]',
                'span:has-text("Row")',
                'div:has-text("Row")'
            ])
            
            # Extract seat numbers
            seat_numbers = await self._extract_text_by_selectors(element, [
                '[data-testid="seats"]',
                '.seats',
                '[class*="seat"]',
                'span:has-text("Seat")',
                'div:has-text("Seats")'
            ])
            
            # Extract quantity
            quantity = await self._extract_quantity(element)
            
            # Extract price
            price = await self._extract_price(element)
            
            # Extract listing ID or link
            listing_id = await self._extract_listing_id(element)
            
            # Only return if we have essential data
            if not price:
                return None
            
            listing = {
                'section': self._clean_text(section),
                'row': self._clean_text(row),
                'seat_numbers': self._clean_text(seat_numbers),
                'quantity': quantity,
                'price': price,
                'listing_id': listing_id,
                'scraped_at': datetime.now().isoformat(),
                'index': index
            }
            
            return listing
            
        except Exception as e:
            print(f"Error extracting listing data: {e}")
            return None
    
    async def _extract_text_by_selectors(self, element, selectors: List[str]) -> Optional[str]:
        """Try multiple selectors to extract text content."""
        for selector in selectors:
            try:
                sub_element = await element.query_selector(selector)
                if sub_element:
                    text = await sub_element.inner_text()
                    if text and text.strip():
                        return text.strip()
            except:
                continue
        return None
    
    async def _extract_quantity(self, element) -> Optional[int]:
        """Extract ticket quantity from listing element."""
        quantity_selectors = [
            '[data-testid="quantity"]',
            '.quantity',
            '[class*="qty"]',
            '[class*="quantity"]'
        ]
        
        quantity_text = await self._extract_text_by_selectors(element, quantity_selectors)
        
        if quantity_text:
            # Extract number from text like "2 tickets" or "1"
            numbers = re.findall(r'\d+', quantity_text)
            if numbers:
                return int(numbers[0])
        
        # Fallback: look for quantity in aria-labels or data attributes
        try:
            qty_attr = await element.get_attribute('data-quantity')
            if qty_attr:
                return int(qty_attr)
        except:
            pass
        
        return 1  # Default to 1 if not found
    
    async def _extract_price(self, element) -> Optional[float]:
        """Extract price from listing element."""
        price_selectors = [
            '[data-testid="price"]',
            '.price',
            '[class*="price"]',
            '.cost',
            '[class*="cost"]'
        ]
        
        price_text = await self._extract_text_by_selectors(element, price_selectors)
        
        if price_text:
            # Clean price text and extract number
            price_clean = re.sub(r'[^\d.,]', '', price_text)
            price_clean = price_clean.replace(',', '')
            
            try:
                return float(price_clean)
            except ValueError:
                pass
        
        return None
    
    async def _extract_listing_id(self, element) -> Optional[str]:
        """Extract listing ID or generate one from href."""
        try:
            # Try to find a link with listing ID
            link = await element.query_selector('a[href*="listing"], a[href*="ticket"]')
            if link:
                href = await link.get_attribute('href')
                if href:
                    # Extract ID from URL
                    id_match = re.search(r'listing[/-](\d+)', href)
                    if id_match:
                        return id_match.group(1)
                    return href
            
            # Fallback: check for data attributes
            for attr in ['data-listing-id', 'data-id', 'id']:
                value = await element.get_attribute(attr)
                if value:
                    return value
        except:
            pass
        
        return None
    
    def _clean_text(self, text: Optional[str]) -> Optional[str]:
        """Clean and normalize extracted text."""
        if not text:
            return None
        
        # Remove extra whitespace and normalize
        cleaned = re.sub(r'\s+', ' ', text.strip())
        
        # Remove common prefixes
        cleaned = re.sub(r'^(Section|Sec|Row|Seat|Seats?)\s*:?\s*', '', cleaned, flags=re.IGNORECASE)
        
        return cleaned if cleaned else None


async def scrape_seatgeek_event(url: str, headless: bool = True) -> List[Dict]:
    """
    Convenience function to scrape a SeatGeek event page.
    
    Args:
        url: SeatGeek event URL
        headless: Whether to run browser in headless mode
        
    Returns:
        List of listing dictionaries
    """
    async with SeatGeekScraper(headless=headless) as scraper:
        return await scraper.scrape_event_listings(url)


def print_listings_summary(listings: List[Dict]):
    """Print a summary of scraped listings."""
    if not listings:
        print("❌ No listings found")
        return
    
    print(f"\n📊 SCRAPING SUMMARY:")
    print(f"Total listings: {len(listings)}")
    
    # Price statistics
    prices = [l['price'] for l in listings if l['price']]
    if prices:
        print(f"Price range: ${min(prices):.2f} - ${max(prices):.2f}")
        print(f"Average price: ${sum(prices)/len(prices):.2f}")
    
    # Section breakdown
    sections = {}
    for listing in listings:
        section = listing.get('section', 'Unknown')
        sections[section] = sections.get(section, 0) + 1
    
    print(f"Sections found: {len(sections)}")
    for section, count in sorted(sections.items()):
        print(f"  {section}: {count} listings")


# Example usage
if __name__ == "__main__":
    async def main():
        # Example: Scrape Red Sox tickets
        url = "https://seatgeek.com/red-sox-tickets"
        
        try:
            listings = await scrape_seatgeek_event(url)
            print_listings_summary(listings)
            
            # Print first few listings as examples
            print(f"\n📋 SAMPLE LISTINGS:")
            for i, listing in enumerate(listings[:5]):
                print(f"{i+1}. Section {listing.get('section', 'N/A')} | "
                      f"Row {listing.get('row', 'N/A')} | "
                      f"Qty {listing.get('quantity', 'N/A')} | "
                      f"${listing.get('price', 'N/A')}")
                      
        except Exception as e:
            print(f"❌ Scraping failed: {e}")
    
    asyncio.run(main())
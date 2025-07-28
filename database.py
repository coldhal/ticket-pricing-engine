"""
Database module for storing scraped ticket listing data.
Uses SQLAlchemy to manage ticket listings with time tracking.
"""

import os
from datetime import datetime
from typing import List, Optional, Dict
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///ticket_data.db')

# SQLAlchemy setup
Base = declarative_base()
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class TicketListing(Base):
    """
    SQLAlchemy model for ticket listings.
    Each scrape creates new rows with timestamps for time tracking.
    """
    __tablename__ = "ticket_listings"
    
    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(String, index=True)  # SeatGeek listing ID if available
    game_id = Column(String, index=True)     # Game identifier or URL
    scraped_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Ticket details
    section = Column(String, index=True)
    row = Column(String)
    seat_numbers = Column(String)  # Comma-separated if multiple
    quantity = Column(Integer)
    price = Column(Float)
    
    # Additional metadata
    source_url = Column(Text)  # Original SeatGeek page URL
    scraper_version = Column(String, default="1.0")
    
    def __repr__(self):
        return f"<TicketListing(section={self.section}, row={self.row}, qty={self.quantity}, price=${self.price})>"


class TicketDatabase:
    """Database manager for ticket listings."""
    
    def __init__(self):
        """Initialize database connection and create tables."""
        self.engine = engine
        self.SessionLocal = SessionLocal
        
        # Create tables if they don't exist
        Base.metadata.create_all(bind=engine)
    
    def get_session(self) -> Session:
        """Get a database session."""
        return self.SessionLocal()
    
    def insert_listings(self, listings: List[Dict], game_id: str, source_url: str = None) -> int:
        """
        Insert scraped listings into database.
        
        Args:
            listings: List of listing dictionaries from scraper
            game_id: Game identifier (URL or custom ID)
            source_url: Original SeatGeek page URL
            
        Returns:
            Number of listings inserted
        """
        session = self.get_session()
        inserted_count = 0
        
        try:
            for listing_data in listings:
                # Create new TicketListing record
                ticket_listing = TicketListing(
                    listing_id=listing_data.get('listing_id'),
                    game_id=game_id,
                    section=listing_data.get('section'),
                    row=listing_data.get('row'),
                    seat_numbers=listing_data.get('seat_numbers'),
                    quantity=listing_data.get('quantity'),
                    price=listing_data.get('price'),
                    source_url=source_url,
                    scraped_at=datetime.utcnow()
                )
                
                session.add(ticket_listing)
                inserted_count += 1
            
            # Commit all insertions
            session.commit()
            print(f"✅ Inserted {inserted_count} listings for game: {game_id}")
            
        except Exception as e:
            session.rollback()
            print(f"❌ Error inserting listings: {e}")
            raise
        finally:
            session.close()
        
        return inserted_count
    
    def get_latest_listings(self, game_id: str, limit: int = None) -> List[TicketListing]:
        """
        Get the most recent listings for a given game.
        
        Args:
            game_id: Game identifier
            limit: Maximum number of listings to return
            
        Returns:
            List of TicketListing objects from most recent scrape
        """
        session = self.get_session()
        
        try:
            # Get the most recent scrape timestamp for this game
            latest_scrape = session.query(TicketListing.scraped_at)\
                .filter(TicketListing.game_id == game_id)\
                .order_by(TicketListing.scraped_at.desc())\
                .first()
            
            if not latest_scrape:
                return []
            
            latest_timestamp = latest_scrape[0]
            
            # Get all listings from that scrape
            query = session.query(TicketListing)\
                .filter(TicketListing.game_id == game_id)\
                .filter(TicketListing.scraped_at == latest_timestamp)\
                .order_by(TicketListing.price.asc())
            
            if limit:
                query = query.limit(limit)
            
            return query.all()
            
        finally:
            session.close()
    
    def get_listings_by_section(self, game_id: str, section: str) -> List[TicketListing]:
        """Get all latest listings for a specific section."""
        session = self.get_session()
        
        try:
            # Get latest scrape timestamp
            latest_scrape = session.query(TicketListing.scraped_at)\
                .filter(TicketListing.game_id == game_id)\
                .order_by(TicketListing.scraped_at.desc())\
                .first()
            
            if not latest_scrape:
                return []
            
            latest_timestamp = latest_scrape[0]
            
            return session.query(TicketListing)\
                .filter(TicketListing.game_id == game_id)\
                .filter(TicketListing.section == section)\
                .filter(TicketListing.scraped_at == latest_timestamp)\
                .order_by(TicketListing.price.asc())\
                .all()
                
        finally:
            session.close()
    
    def get_price_history(self, game_id: str, section: str = None, days: int = 7) -> List[Dict]:
        """
        Get price history for analysis and trending.
        
        Args:
            game_id: Game identifier
            section: Optional section filter
            days: Number of days to look back
            
        Returns:
            List of price statistics by timestamp
        """
        session = self.get_session()
        
        try:
            # Calculate cutoff date
            cutoff_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)
            
            # Base query
            query = session.query(TicketListing)\
                .filter(TicketListing.game_id == game_id)\
                .filter(TicketListing.scraped_at >= cutoff_date)
            
            if section:
                query = query.filter(TicketListing.section == section)
            
            listings = query.order_by(TicketListing.scraped_at.desc()).all()
            
            # Group by scrape timestamp and calculate stats
            price_history = {}
            for listing in listings:
                timestamp = listing.scraped_at.isoformat()
                
                if timestamp not in price_history:
                    price_history[timestamp] = {
                        'timestamp': timestamp,
                        'prices': [],
                        'count': 0
                    }
                
                price_history[timestamp]['prices'].append(listing.price)
                price_history[timestamp]['count'] += 1
            
            # Calculate statistics for each timestamp
            history = []
            for timestamp, data in price_history.items():
                prices = data['prices']
                history.append({
                    'timestamp': timestamp,
                    'count': len(prices),
                    'min_price': min(prices),
                    'max_price': max(prices),
                    'avg_price': sum(prices) / len(prices),
                    'median_price': sorted(prices)[len(prices) // 2]
                })
            
            return sorted(history, key=lambda x: x['timestamp'])
            
        finally:
            session.close()
    
    def get_game_stats(self, game_id: str) -> Dict:
        """Get summary statistics for a game."""
        session = self.get_session()
        
        try:
            latest_listings = self.get_latest_listings(game_id)
            
            if not latest_listings:
                return {}
            
            prices = [l.price for l in latest_listings if l.price]
            sections = list(set(l.section for l in latest_listings if l.section))
            
            return {
                'total_listings': len(latest_listings),
                'sections_available': len(sections),
                'price_range': {
                    'min': min(prices) if prices else 0,
                    'max': max(prices) if prices else 0,
                    'avg': sum(prices) / len(prices) if prices else 0
                },
                'last_updated': latest_listings[0].scraped_at.isoformat() if latest_listings else None
            }
            
        finally:
            session.close()
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Remove listing data older than specified days."""
        session = self.get_session()
        
        try:
            cutoff_date = datetime.utcnow().replace(day=datetime.utcnow().day - days_to_keep)
            
            deleted_count = session.query(TicketListing)\
                .filter(TicketListing.scraped_at < cutoff_date)\
                .delete()
            
            session.commit()
            print(f"🗑️ Cleaned up {deleted_count} old listings")
            
        except Exception as e:
            session.rollback()
            print(f"❌ Error cleaning up data: {e}")
        finally:
            session.close()


# Helper functions for easy access
def save_scraped_listings(listings: List[Dict], game_id: str, source_url: str = None) -> int:
    """
    Convenience function to save scraped listings to database.
    
    Args:
        listings: List of listing dictionaries from scraper
        game_id: Game identifier
        source_url: Original SeatGeek page URL
        
    Returns:
        Number of listings saved
    """
    db = TicketDatabase()
    return db.insert_listings(listings, game_id, source_url)


def get_latest_listings(game_id: str, limit: int = None) -> List[Dict]:
    """
    Helper function to get latest listings as dictionaries.
    
    Args:
        game_id: Game identifier
        limit: Maximum number of listings
        
    Returns:
        List of listing dictionaries
    """
    db = TicketDatabase()
    listings = db.get_latest_listings(game_id, limit)
    
    return [
        {
            'id': l.id,
            'listing_id': l.listing_id,
            'section': l.section,
            'row': l.row,
            'seat_numbers': l.seat_numbers,
            'quantity': l.quantity,
            'price': l.price,
            'scraped_at': l.scraped_at.isoformat()
        }
        for l in listings
    ]


# Example usage and testing
if __name__ == "__main__":
    # Initialize database
    db = TicketDatabase()
    
    # Example data insertion
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
    
    # Test insertion
    game_id = "red-sox-vs-yankees-2024-06-15"
    count = db.insert_listings(sample_listings, game_id, "https://seatgeek.com/red-sox-tickets")
    print(f"Inserted {count} sample listings")
    
    # Test retrieval
    latest = db.get_latest_listings(game_id)
    print(f"Retrieved {len(latest)} latest listings")
    
    for listing in latest:
        print(f"  {listing.section} Row {listing.row}: ${listing.price}")
    
    # Test statistics
    stats = db.get_game_stats(game_id)
    print(f"Game stats: {stats}")
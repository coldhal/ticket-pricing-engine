"""
Game tracker module for managing upcoming games and my ticket listings.
Tracks games, my listings, and their status using SQLite.
"""

import os
import json
from datetime import datetime, date
from typing import List, Dict, Optional
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text
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


class Game(Base):
    """SQLAlchemy model for tracking games."""
    __tablename__ = "games"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(String, unique=True, index=True)  # Unique identifier
    game_date = Column(DateTime, index=True)
    opponent = Column(String)
    venue = Column(String, default="Fenway Park")
    status = Column(String, default="active")  # active, completed, canceled
    
    # Additional game metadata
    game_time = Column(String)  # e.g., "7:10 PM"
    day_of_week = Column(String)
    is_weekend = Column(Boolean, default=False)
    is_home_game = Column(Boolean, default=True)
    
    # Tracking fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Game(id={self.game_id}, date={self.game_date}, opponent={self.opponent})>"


class MyListing(Base):
    """SQLAlchemy model for tracking my ticket listings."""
    __tablename__ = "my_listings"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(String, index=True)  # Foreign key to games.game_id
    
    # Ticket details
    section = Column(String, index=True)
    row = Column(String)
    seat_numbers = Column(String)  # Comma-separated seat numbers
    quantity = Column(Integer)
    
    # Pricing information
    original_price = Column(Float)  # Initial listing price
    current_price = Column(Float)   # Current listing price
    
    # SeatGeek information
    listing_id = Column(String, index=True)  # SeatGeek listing ID
    
    # Status tracking
    is_active = Column(Boolean, default=True)  # Is listing still active
    is_sold = Column(Boolean, default=False)   # Has been sold
    sold_date = Column(DateTime)               # When it was sold
    sold_price = Column(Float)                 # Final sale price
    
    # Tracking fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<MyListing(game={self.game_id}, section={self.section}, row={self.row}, qty={self.quantity})>"


class GameTracker:
    """Main class for managing games and listings."""
    
    def __init__(self):
        """Initialize database connection and create tables."""
        self.engine = engine
        self.SessionLocal = SessionLocal
        
        # Create tables if they don't exist
        Base.metadata.create_all(bind=engine)
    
    def get_session(self) -> Session:
        """Get a database session."""
        return self.SessionLocal()
    
    def add_game(self, game_date: datetime, opponent: str, venue: str = "Fenway Park",
                 game_time: str = None, game_id: str = None) -> str:
        """
        Add a new game to track.
        
        Args:
            game_date: Date and time of the game
            opponent: Opposing team name
            venue: Venue name (defaults to Fenway Park)
            game_time: Game time string (e.g., "7:10 PM")
            game_id: Optional custom game ID
            
        Returns:
            Game ID of the created game
        """
        session = self.get_session()
        
        try:
            # Generate game_id if not provided
            if not game_id:
                date_str = game_date.strftime("%Y-%m-%d")
                opponent_clean = opponent.lower().replace(" ", "-")
                game_id = f"red-sox-vs-{opponent_clean}-{date_str}"
            
            # Check if game already exists
            existing = session.query(Game).filter(Game.game_id == game_id).first()
            if existing:
                print(f"⚠️ Game {game_id} already exists")
                return existing.game_id
            
            # Create new game
            game = Game(
                game_id=game_id,
                game_date=game_date,
                opponent=opponent,
                venue=venue,
                game_time=game_time,
                day_of_week=game_date.strftime("%A"),
                is_weekend=game_date.weekday() >= 5,  # Saturday = 5, Sunday = 6
                status="active"
            )
            
            session.add(game)
            session.commit()
            
            print(f"✅ Added game: {game_id}")
            return game_id
            
        except Exception as e:
            session.rollback()
            print(f"❌ Error adding game: {e}")
            raise
        finally:
            session.close()
    
    def add_my_listing(self, game_id: str, section: str, row: str, quantity: int,
                      price: float, seat_numbers: str = None, listing_id: str = None) -> int:
        """
        Add a new listing for myself.
        
        Args:
            game_id: Game identifier
            section: Section name
            row: Row identifier
            quantity: Number of tickets
            price: Listing price
            seat_numbers: Comma-separated seat numbers
            listing_id: SeatGeek listing ID
            
        Returns:
            Database ID of the created listing
        """
        session = self.get_session()
        
        try:
            # Verify game exists
            game = session.query(Game).filter(Game.game_id == game_id).first()
            if not game:
                raise ValueError(f"Game {game_id} not found")
            
            # Create listing
            listing = MyListing(
                game_id=game_id,
                section=section,
                row=row,
                seat_numbers=seat_numbers,
                quantity=quantity,
                original_price=price,
                current_price=price,
                listing_id=listing_id,
                is_active=True
            )
            
            session.add(listing)
            session.commit()
            
            print(f"✅ Added listing: {section} Row {row} (Qty: {quantity}) - ${price}")
            return listing.id
            
        except Exception as e:
            session.rollback()
            print(f"❌ Error adding listing: {e}")
            raise
        finally:
            session.close()
    
    def get_active_listings(self, game_id: str = None) -> List[Dict]:
        """
        Get all active listings, optionally filtered by game.
        
        Args:
            game_id: Optional game filter
            
        Returns:
            List of listing dictionaries
        """
        session = self.get_session()
        
        try:
            query = session.query(MyListing, Game)\
                .join(Game, MyListing.game_id == Game.game_id)\
                .filter(MyListing.is_active == True)\
                .filter(MyListing.is_sold == False)
            
            if game_id:
                query = query.filter(MyListing.game_id == game_id)
            
            results = query.all()
            
            listings = []
            for listing, game in results:
                listings.append({
                    'id': listing.id,
                    'game_id': listing.game_id,
                    'game_date': game.game_date.isoformat() if game.game_date else None,
                    'opponent': game.opponent,
                    'section': listing.section,
                    'row': listing.row,
                    'seat_numbers': listing.seat_numbers,
                    'quantity': listing.quantity,
                    'original_price': listing.original_price,
                    'current_price': listing.current_price,
                    'listing_id': listing.listing_id,
                    'created_at': listing.created_at.isoformat()
                })
            
            return listings
            
        finally:
            session.close()
    
    def mark_listing_sold(self, game_id: str, section: str, row: str, 
                         sold_price: float = None) -> bool:
        """
        Mark a listing as sold.
        
        Args:
            game_id: Game identifier
            section: Section name
            row: Row identifier
            sold_price: Final sale price
            
        Returns:
            True if listing found and marked sold
        """
        session = self.get_session()
        
        try:
            listing = session.query(MyListing)\
                .filter(MyListing.game_id == game_id)\
                .filter(MyListing.section == section)\
                .filter(MyListing.row == row)\
                .filter(MyListing.is_active == True)\
                .first()
            
            if not listing:
                print(f"❌ Listing not found: {section} Row {row}")
                return False
            
            # Mark as sold
            listing.is_sold = True
            listing.is_active = False
            listing.sold_date = datetime.utcnow()
            
            if sold_price:
                listing.sold_price = sold_price
            else:
                listing.sold_price = listing.current_price
            
            session.commit()
            
            print(f"✅ Marked listing as sold: {section} Row {row} for ${listing.sold_price}")
            return True
            
        except Exception as e:
            session.rollback()
            print(f"❌ Error marking listing sold: {e}")
            return False
        finally:
            session.close()
    
    def update_listing_price(self, game_id: str, section: str, row: str,
                           new_price: float) -> bool:
        """
        Update the current price of a listing.
        
        Args:
            game_id: Game identifier
            section: Section name
            row: Row identifier
            new_price: New listing price
            
        Returns:
            True if listing found and updated
        """
        session = self.get_session()
        
        try:
            listing = session.query(MyListing)\
                .filter(MyListing.game_id == game_id)\
                .filter(MyListing.section == section)\
                .filter(MyListing.row == row)\
                .filter(MyListing.is_active == True)\
                .first()
            
            if not listing:
                print(f"❌ Listing not found: {section} Row {row}")
                return False
            
            old_price = listing.current_price
            listing.current_price = new_price
            listing.updated_at = datetime.utcnow()
            
            session.commit()
            
            print(f"✅ Updated price: {section} Row {row} ${old_price} → ${new_price}")
            return True
            
        except Exception as e:
            session.rollback()
            print(f"❌ Error updating price: {e}")
            return False
        finally:
            session.close()
    
    def get_all_upcoming_games(self, limit: int = None) -> List[Dict]:
        """
        Get all upcoming active games.
        
        Args:
            limit: Optional limit on number of games
            
        Returns:
            List of game dictionaries
        """
        session = self.get_session()
        
        try:
            query = session.query(Game)\
                .filter(Game.status == "active")\
                .filter(Game.game_date >= datetime.now())\
                .order_by(Game.game_date.asc())
            
            if limit:
                query = query.limit(limit)
            
            games = query.all()
            
            result = []
            for game in games:
                # Count active listings for this game
                listing_count = session.query(MyListing)\
                    .filter(MyListing.game_id == game.game_id)\
                    .filter(MyListing.is_active == True)\
                    .count()
                
                result.append({
                    'game_id': game.game_id,
                    'game_date': game.game_date.isoformat() if game.game_date else None,
                    'opponent': game.opponent,
                    'venue': game.venue,
                    'game_time': game.game_time,
                    'day_of_week': game.day_of_week,
                    'is_weekend': game.is_weekend,
                    'status': game.status,
                    'my_listings_count': listing_count
                })
            
            return result
            
        finally:
            session.close()
    
    def get_game_summary(self, game_id: str) -> Optional[Dict]:
        """
        Get detailed summary for a specific game.
        
        Args:
            game_id: Game identifier
            
        Returns:
            Game summary dictionary or None if not found
        """
        session = self.get_session()
        
        try:
            game = session.query(Game).filter(Game.game_id == game_id).first()
            if not game:
                return None
            
            # Get all my listings for this game
            listings = session.query(MyListing)\
                .filter(MyListing.game_id == game_id)\
                .all()
            
            active_listings = [l for l in listings if l.is_active and not l.is_sold]
            sold_listings = [l for l in listings if l.is_sold]
            
            # Calculate totals
            total_investment = sum(l.original_price * l.quantity for l in listings)
            total_current_value = sum(l.current_price * l.quantity for l in active_listings)
            total_sold_value = sum((l.sold_price or 0) * l.quantity for l in sold_listings)
            
            return {
                'game_id': game.game_id,
                'game_date': game.game_date.isoformat() if game.game_date else None,
                'opponent': game.opponent,
                'venue': game.venue,
                'status': game.status,
                'total_listings': len(listings),
                'active_listings': len(active_listings),
                'sold_listings': len(sold_listings),
                'total_investment': total_investment,
                'current_value': total_current_value,
                'sold_value': total_sold_value,
                'potential_profit': (total_current_value + total_sold_value) - total_investment
            }
            
        finally:
            session.close()
    
    def deactivate_listing(self, game_id: str, section: str, row: str) -> bool:
        """
        Deactivate a listing (e.g., removed from SeatGeek).
        
        Args:
            game_id: Game identifier
            section: Section name
            row: Row identifier
            
        Returns:
            True if listing found and deactivated
        """
        session = self.get_session()
        
        try:
            listing = session.query(MyListing)\
                .filter(MyListing.game_id == game_id)\
                .filter(MyListing.section == section)\
                .filter(MyListing.row == row)\
                .filter(MyListing.is_active == True)\
                .first()
            
            if not listing:
                print(f"❌ Listing not found: {section} Row {row}")
                return False
            
            listing.is_active = False
            listing.updated_at = datetime.utcnow()
            
            session.commit()
            
            print(f"✅ Deactivated listing: {section} Row {row}")
            return True
            
        except Exception as e:
            session.rollback()
            print(f"❌ Error deactivating listing: {e}")
            return False
        finally:
            session.close()


# Helper functions for easy access
def add_game(game_date: datetime, opponent: str, venue: str = "Fenway Park") -> str:
    """Convenience function to add a game."""
    tracker = GameTracker()
    return tracker.add_game(game_date, opponent, venue)


def add_my_listing(game_id: str, section: str, row: str, quantity: int, price: float) -> int:
    """Convenience function to add my listing."""
    tracker = GameTracker()
    return tracker.add_my_listing(game_id, section, row, quantity, price)


def get_active_listings(game_id: str = None) -> List[Dict]:
    """Convenience function to get active listings."""
    tracker = GameTracker()
    return tracker.get_active_listings(game_id)


def mark_listing_sold(game_id: str, section: str, row: str, sold_price: float = None) -> bool:
    """Convenience function to mark listing sold."""
    tracker = GameTracker()
    return tracker.mark_listing_sold(game_id, section, row, sold_price)


def get_all_upcoming_games() -> List[Dict]:
    """Convenience function to get upcoming games."""
    tracker = GameTracker()
    return tracker.get_all_upcoming_games()


# Example usage and testing
if __name__ == "__main__":
    # Initialize tracker
    tracker = GameTracker()
    
    # Add sample games
    from datetime import timedelta
    
    # Game 1: Yankees (next week)
    game1_date = datetime.now() + timedelta(days=7)
    game1_id = tracker.add_game(game1_date, "New York Yankees", game_time="7:10 PM")
    
    # Game 2: Blue Jays (2 weeks)
    game2_date = datetime.now() + timedelta(days=14)
    game2_id = tracker.add_game(game2_date, "Toronto Blue Jays", game_time="1:35 PM")
    
    # Add sample listings
    tracker.add_my_listing(game1_id, "Green Monster", "2", 2, 299.99, "1-2")
    tracker.add_my_listing(game1_id, "Infield Box 15", "A", 1, 175.00, "5")
    tracker.add_my_listing(game2_id, "Pavilion Box", "12", 4, 89.99, "9-12")
    
    # Test retrieval
    print("\n📅 UPCOMING GAMES:")
    games = tracker.get_all_upcoming_games()
    for game in games:
        print(f"  {game['game_date'][:10]} vs {game['opponent']} - {game['my_listings_count']} listings")
    
    print("\n🎫 ACTIVE LISTINGS:")
    listings = tracker.get_active_listings()
    for listing in listings:
        print(f"  {listing['game_date'][:10]} - {listing['section']} Row {listing['row']} - ${listing['current_price']}")
    
    print("\n📊 GAME SUMMARY:")
    summary = tracker.get_game_summary(game1_id)
    if summary:
        print(f"  Game: {summary['opponent']}")
        print(f"  Active Listings: {summary['active_listings']}")
        print(f"  Total Investment: ${summary['total_investment']:.2f}")
        print(f"  Current Value: ${summary['current_value']:.2f}")
        print(f"  Potential Profit: ${summary['potential_profit']:.2f}")
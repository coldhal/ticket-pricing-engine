# Red Sox Ticket Pricing System

An automated ticket pricing and management system for Red Sox tickets on SeatGeek. This system scrapes market data, analyzes pricing opportunities, and automatically updates your ticket listings for optimal pricing.

## 🎯 Features

- **Automated Market Scraping**: Scrapes SeatGeek event pages for current market listings
- **Intelligent Pricing Engine**: Analyzes market conditions and recommends optimal prices
- **Automated Price Updates**: Updates your SeatGeek listings automatically
- **Market Alerts**: Monitors for undercuts, sell-through surges, and pricing opportunities
- **Game & Listing Tracking**: Manages your ticket inventory and game schedule
- **Historical Analysis**: Tracks pricing decisions and market trends over time
- **React Dashboard**: (Optional) Web interface for monitoring and manual control

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd red-sox-pricing

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### 2. Configuration

Create a `.env` file with your SeatGeek credentials:

```bash
cp .env.example .env
# Edit .env with your credentials
```

Required environment variables:
- `SEATGEEK_EMAIL`: Your SeatGeek account email
- `SEATGEEK_PASSWORD`: Your SeatGeek account password

### 3. Initial Setup

Import your existing SeatGeek listings:

```bash
python initial_import.py
```

This will:
- Log into your SeatGeek account
- Scrape all your Red Sox listings
- Populate the game tracker database

### 4. Run Auto-Pricing

Execute the main automation workflow:

```bash
python auto_pricer.py run
```

This will:
- Scrape current market listings for each tracked game
- Analyze your listings against market conditions
- Update prices on SeatGeek when beneficial
- Generate alerts for urgent situations

## 📋 Core Modules

### `scraper.py`
Playwright-based scraper for SeatGeek event pages.

**Key Features:**
- Handles lazy-loading and pagination
- Extracts section, row, quantity, price, and listing IDs
- Resilient to page structure changes

**Usage:**
```python
from scraper import scrape_seatgeek_event

# Scrape Red Sox vs Yankees tickets
listings = await scrape_seatgeek_event("https://seatgeek.com/red-sox-tickets")
print(f"Found {len(listings)} listings")
```

### `database.py`
SQLAlchemy-based data storage with time tracking.

**Key Features:**
- Stores all scraped listings with timestamps
- Tracks price history and market trends
- Helper functions for data retrieval

**Usage:**
```python
from database import save_scraped_listings, get_latest_listings

# Save scraped data
save_scraped_listings(listings, "red-sox-vs-yankees-2024-06-15")

# Get latest listings for analysis
latest = get_latest_listings("red-sox-vs-yankees-2024-06-15")
```

### `pricing_engine.py`
Intelligent pricing recommendation engine.

**Key Features:**
- Finds comparable listings by section and quantity
- Calculates market position and percentile ranking
- Adjusts recommendations based on game timing
- Logs all decisions for machine learning training

**Usage:**
```python
from pricing_engine import get_price_recommendation
from datetime import datetime, timedelta

my_listing = {
    'section': 'Green Monster',
    'row': '2',
    'quantity': 2,
    'current_price': 250.00
}

game_time = datetime.now() + timedelta(hours=36)
decision = get_price_recommendation(my_listing, market_listings, game_time)

print(f"Recommended: ${decision.recommended_price:.2f}")
print(f"Reasoning: {decision.reasoning}")
print(f"Confidence: {decision.confidence:.0%}")
```

### `seatgeek_automation.py`
Playwright automation for SeatGeek account management.

**Key Features:**
- Automated login and navigation
- Finds and updates specific listings
- Error handling and logging

**Usage:**
```python
from seatgeek_automation import update_ticket_price

# Update a specific listing
success = await update_ticket_price(
    listing_id="12345",
    new_price=275.00,
    section="Green Monster",
    row="2",
    quantity=2
)
```

### `game_tracker.py`
Game and listing inventory management.

**Key Features:**
- Tracks upcoming games and your listings
- Manages listing status (active, sold, etc.)
- Provides summary statistics

**Usage:**
```python
from game_tracker import GameTracker
from datetime import datetime

tracker = GameTracker()

# Add a new game
game_id = tracker.add_game(
    game_date=datetime(2024, 6, 15, 19, 10),
    opponent="New York Yankees"
)

# Add your listing
tracker.add_my_listing(
    game_id=game_id,
    section="Green Monster",
    row="2",
    quantity=2,
    price=299.99
)
```

### `alerts.py`
Market monitoring and alert system.

**Key Features:**
- Undercut detection
- Sell-through surge monitoring
- Late-game timing alerts
- Market price drop notifications

**Usage:**
```python
from alerts import check_alerts, print_alerts

# Check for alerts
alerts = check_alerts()

# Print formatted summary
print_alerts()
```

### `auto_pricer.py`
Main automation orchestrator.

**Key Features:**
- Runs complete workflow for all tracked games
- Configurable game list and pricing settings
- Comprehensive logging and error handling

**Usage:**
```bash
# Run once
python auto_pricer.py run

# Disable a specific game
python auto_pricer.py disable red-sox-vs-yankees-2024-06-15

# Enable a game
python auto_pricer.py enable red-sox-vs-yankees-2024-06-15
```

## ⚙️ Configuration

### Game Configuration (`games_config.json`)

```json
{
  "tracked_games": [
    {
      "game_id": "red-sox-vs-yankees-2024-06-15",
      "url": "https://seatgeek.com/red-sox-vs-yankees-tickets/...",
      "game_date": "2024-06-15T19:10:00",
      "opponent": "New York Yankees",
      "enabled": true
    }
  ],
  "pricing_settings": {
    "aggressiveness": 0.7,
    "price_floor_buffer": 0.95,
    "round_to_nearest": 5
  }
}
```

### Pricing Engine Configuration

```python
from pricing_engine import PricingConfig

config = PricingConfig(
    price_floor_buffer=0.95,    # Don't go below 95% of market floor
    aggressiveness=0.7,         # 0.0 = conservative, 1.0 = aggressive
    round_to_nearest=5,         # Round prices to nearest $5
    urgency_threshold_hours=48  # Start urgency pricing 48h before game
)
```

## 📊 Monitoring & Alerts

### Alert Types

1. **Undercut Alert**: When competitors undercut your price by more than $5
2. **Surge Alert**: When listing count drops by 25%+ in 24 hours
3. **Late Game Alert**: When you're overpriced with < 48 hours to game
4. **Price Drop Alert**: When market floor drops by 10%+ in 24 hours

### Alert Examples

```
🟠 Undercut Alert - Green Monster: A new listing is $10 below your price of $250. New floor: $240
🟡 Sell-Through Surge - Section 112: Listings dropped 30% in 24h. Only 9 listings remain.
🔴 Late Game Warning - Pavilion Box: Game in 36h. You're #3 of 8 (75th percentile). Risk missing sell window!
```

## 🕐 Scheduling

### Cron Setup

Add to your crontab for automated execution:

```bash
# Run every 2 hours during business hours
0 8,10,12,14,16,18,20 * * * cd /path/to/red-sox-pricing && python auto_pricer.py run

# Check alerts every hour
0 * * * * cd /path/to/red-sox-pricing && python -c "from alerts import print_alerts; print_alerts()"
```

### Python Scheduler

```python
import schedule
import time
import asyncio
from auto_pricer import run_once

def job():
    asyncio.run(run_once())

# Schedule runs every 2 hours
schedule.every(2).hours.do(job)

while True:
    schedule.run_pending()
    time.sleep(60)
```

## 📈 Data & Analytics

### Pricing Decision Logs

All pricing decisions are logged to `pricing_decisions.csv` with:
- Market conditions at time of decision
- Recommended vs actual price changes
- Confidence scores and reasoning
- Game timing and urgency factors

### Market History

Historical market data is stored in SQLite with:
- Price trends over time
- Listing count changes
- Section-level analysis
- Volatility measurements

## 🚨 Safety Features

### Conservative Defaults
- Won't update prices for changes < $2
- Requires 60%+ confidence for updates
- Won't raise prices when already ranked #1
- Respects configurable price floors

### Error Handling
- Graceful failure when SeatGeek is unavailable
- Retry logic for network issues
- Comprehensive logging for debugging
- Safe fallbacks when automation fails

## 🔧 Troubleshooting

### Common Issues

**Login Failures:**
- Verify credentials in `.env` file
- Check for SeatGeek account lockouts
- Try running with `headless=False` for debugging

**Scraping Issues:**
- SeatGeek may have changed page structure
- Check selectors in `scraper.py`
- Verify event URLs are correct

**Price Update Failures:**
- Ensure listings still exist on SeatGeek
- Check that listing details match exactly
- Verify sufficient account permissions

### Debug Mode

Run with visible browser for debugging:

```python
# In your script
automation = SeatGeekAutomation(headless=False)
```

### Logs

Check these files for debugging:
- `pricing_decisions.csv` - All pricing decisions
- `price_updates.log` - SeatGeek update attempts
- `alerts.log` - Alert notifications
- `auto_pricer_log.json` - Workflow summaries

## 📝 License

This project is for educational and personal use only. Please respect SeatGeek's terms of service and rate limits when using this system.

## ⚠️ Disclaimer

This system is provided as-is without warranty. Users are responsible for:
- Complying with SeatGeek's terms of service
- Monitoring their listings and pricing decisions
- Ensuring account security and credential safety

Use automated trading tools at your own risk. Always review pricing decisions before they take effect.
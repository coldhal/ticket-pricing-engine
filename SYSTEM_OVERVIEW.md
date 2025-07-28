# Red Sox Ticket Pricing System - Complete Implementation

## 🎯 What Has Been Built

A comprehensive, fully-automated ticket pricing and management system for Red Sox tickets on SeatGeek. The system continuously monitors market conditions and automatically adjusts your ticket prices for optimal profitability.

## 📋 Complete Module List

### Core Modules (✅ Complete)

1. **`scraper.py`** - Advanced SeatGeek scraper
   - Playwright-based web scraping with anti-detection
   - Handles lazy-loading and pagination automatically
   - Extracts: section, row, seat numbers, quantity, price, listing IDs
   - Resilient error handling and retry logic

2. **`database.py`** - SQLAlchemy data management
   - Time-series data storage with complete history tracking
   - Efficient querying for latest listings and price trends
   - Helper functions for easy integration
   - Automatic database schema creation

3. **`pricing_engine.py`** - Intelligent pricing algorithm
   - Finds comparable listings by section/quantity/proximity
   - Calculates market position and percentile ranking
   - Time-based urgency adjustments (game approaching)
   - Confidence scoring and detailed reasoning
   - Logs all decisions to CSV for ML training

4. **`seatgeek_automation.py`** - SeatGeek account automation
   - Automated login and navigation
   - Finds and updates specific listings by section/row/quantity
   - Error handling and update confirmation
   - Complete audit trail of all changes

5. **`game_tracker.py`** - Game and inventory management
   - Tracks upcoming games and your ticket listings
   - Manages listing status (active, sold, deactivated)
   - Provides comprehensive summary statistics
   - SQLAlchemy models for games and personal listings

6. **`alerts.py`** - Market monitoring and notifications
   - **Undercut Detection**: Alerts when competitors undercut by >$5
   - **Sell-Through Surge**: Monitors for 25%+ inventory drops
   - **Late-Game Timing**: Warns when overpriced <48h before game
   - **Price Drop Alerts**: Detects 10%+ market floor drops
   - Configurable thresholds and severity levels

### Automation Scripts (✅ Complete)

7. **`auto_pricer.py`** - Main workflow orchestrator
   - Runs complete end-to-end pricing workflow
   - Processes multiple games and listings automatically
   - Comprehensive error handling and logging
   - Command-line interface for manual control
   - JSON configuration for tracked games

8. **`initial_import.py`** - SeatGeek account import
   - Scrapes all existing Red Sox listings from your account
   - Intelligently parses game dates, opponents, and ticket details
   - Populates game tracker database automatically
   - Filters for Red Sox home games only

### Testing & Demo (✅ Complete)

9. **`test_system.py`** - Comprehensive test suite
   - Tests all modules individually and integration
   - Database functionality validation
   - Pricing engine logic verification
   - Alerts system testing
   - Complete workflow validation

10. **`demo.py`** - Live system demonstration
    - Shows complete workflow without external dependencies
    - Demonstrates pricing logic and alert generation
    - Educational tool for understanding the system

### Configuration Files (✅ Complete)

11. **`requirements.txt`** - Python dependencies
12. **`.env.example`** - Environment variables template
13. **`README.md`** - Comprehensive documentation
14. **`games_config.json`** - Game tracking configuration (auto-generated)

## 🔄 How It Works

### 1. Initial Setup
```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Configure credentials
cp .env.example .env
# Edit .env with your SeatGeek credentials

# Import existing listings
python initial_import.py
```

### 2. Automated Operation
```bash
# Run once manually
python auto_pricer.py run

# Or set up automated scheduling
# Cron example: Run every 2 hours during business hours
0 8,10,12,14,16,18,20 * * * cd /path/to/system && python auto_pricer.py run
```

### 3. Workflow Execution
For each tracked game, the system:

1. **Scrapes market data** from SeatGeek event page
2. **Stores data** in SQLite with timestamps
3. **Analyzes each of your listings** against market conditions
4. **Generates price recommendations** with confidence scores
5. **Updates prices on SeatGeek** when beneficial
6. **Checks alert conditions** and generates notifications
7. **Logs all decisions** for analysis and ML training

## 🎯 Key Features

### Intelligent Pricing
- **Market Position Analysis**: Knows exactly where you rank vs competitors
- **Timing Adjustments**: Prices more aggressively as game approaches
- **Comparable Finding**: Matches listings by section, quantity, and proximity
- **Confidence Scoring**: Only makes high-confidence recommendations

### Safety Controls
- **Conservative Defaults**: Won't update for changes <$2 or confidence <60%
- **Price Floor Protection**: Respects configurable minimum prices
- **Error Recovery**: Graceful handling of SeatGeek outages or changes
- **Manual Override**: Easy disable/enable for specific games

### Market Intelligence
- **Real-Time Alerts**: Immediate notification of undercuts or opportunities
- **Historical Tracking**: Complete price and inventory history
- **Trend Analysis**: Identifies sell-through patterns and market shifts
- **Volatility Detection**: Adjusts strategy based on market stability

### Operational Excellence
- **Complete Automation**: Runs unattended with minimal intervention
- **Comprehensive Logging**: Full audit trail of all decisions and changes
- **Modular Design**: Easy to modify individual components
- **Robust Error Handling**: Continues operation despite individual failures

## 📊 Data Tracking

### Database Tables
- **`ticket_listings`**: All scraped market data with timestamps
- **`games`**: Tracked games with metadata
- **`my_listings`**: Your personal inventory and status

### Log Files
- **`pricing_decisions.csv`**: ML training data with all decision factors
- **`price_updates.log`**: SeatGeek update attempts and results
- **`alerts.log`**: Alert history and notifications
- **`auto_pricer_log.json`**: Workflow execution summaries

## 🚨 Alert Examples

```
🟠 Undercut Alert - Green Monster: A new listing is $10 below your price of $250. New floor: $240

🟡 Sell-Through Surge - Section 112: Listings dropped 30% in 24h. Only 9 listings remain.

🔴 Late Game Warning - Pavilion Box: Game in 36h. You're #3 of 8 (75th percentile). Risk missing sell window!

🔵 Market Drop - Infield Box 15: Section floor fell 12% to $180. Your price $200 is 11% above floor.
```

## 🎛️ Configuration Options

### Pricing Engine Settings
```python
PricingConfig(
    price_floor_buffer=0.95,    # Don't go below 95% of market floor
    aggressiveness=0.7,         # 0.0 = conservative, 1.0 = aggressive  
    round_to_nearest=5,         # Round prices to nearest $5
    urgency_threshold_hours=48  # Start urgency pricing 48h before game
)
```

### Alert Thresholds
```python
{
    'undercut_threshold': 5.0,      # Alert if undercut by >$5
    'surge_threshold': 0.25,        # Alert if listings drop >25%
    'late_game_hours': 48,          # Alert if <48h to game
    'price_drop_threshold': 0.10    # Alert if floor drops >10%
}
```

## 🔮 Future Enhancements Ready

The system is designed for easy extension:

1. **Machine Learning Integration** - CSV logs ready for model training
2. **React Dashboard** - Web interface for monitoring and control
3. **Multiple Venues** - Easy to extend beyond Fenway Park
4. **Email/SMS Alerts** - Notification system hooks are in place
5. **Advanced Analytics** - Historical data ready for trend analysis

## ✅ Ready to Deploy

The system is production-ready with:
- ✅ Complete error handling and recovery
- ✅ Comprehensive logging and monitoring
- ✅ Conservative safety controls
- ✅ Modular, maintainable code
- ✅ Full documentation and examples
- ✅ Test suite for validation

**Next step**: Configure your `.env` file and start with `python initial_import.py`!
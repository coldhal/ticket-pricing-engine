from dotenv import load_dotenv
import os

load_dotenv()

SEATGEEK_EMAIL = os.getenv("SEATGEEK_EMAIL")
SEATGEEK_PASSWORD = os.getenv("SEATGEEK_PASSWORD")

if not SEATGEEK_EMAIL or not SEATGEEK_PASSWORD:
    raise ValueError("Missing SeatGeek credentials in .env file")

print("✅ SeatGeek credentials loaded successfully")
#!/usr/bin/env python3
"""
Test script to demonstrate credential loading using load_env.py
This shows how other modules can import credentials safely.
"""

try:
    # Import credentials from load_env module
    from load_env import SEATGEEK_EMAIL, SEATGEEK_PASSWORD
    
    print("🔐 Credential Test")
    print("=" * 30)
    print(f"Email: {SEATGEEK_EMAIL[:5]}...@{SEATGEEK_EMAIL.split('@')[1]}")
    print(f"Password: [HIDDEN - {len(SEATGEEK_PASSWORD)} characters]")
    print("✅ Credentials loaded successfully!")
    
    # Test that credentials are not empty
    assert SEATGEEK_EMAIL and "@" in SEATGEEK_EMAIL, "Invalid email format"
    assert SEATGEEK_PASSWORD and len(SEATGEEK_PASSWORD) > 5, "Password too short"
    
    print("✅ Credential validation passed!")
    
    print("\n📋 Usage in other modules:")
    print("from load_env import SEATGEEK_EMAIL, SEATGEEK_PASSWORD")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Install dependencies: pip install python-dotenv")
    
except ValueError as e:
    print(f"❌ Configuration error: {e}")
    print("💡 Check your .env file contains valid credentials")
    
except Exception as e:
    print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    print("\n🚀 Ready to use in automation scripts!")
    print("Next steps:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Run: python initial_import.py")
    print("3. Run: python auto_pricer.py run")
"""
Quick test script to verify the app is working
Run this after starting the Flask app to test basic functionality
"""
import requests
import json

BASE_URL = "http://localhost:5000"

def test_health():
    """Test health endpoint."""
    print("Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_status():
    """Test status endpoint."""
    print("Testing status endpoint...")
    response = requests.get(f"{BASE_URL}/api/status")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

if __name__ == "__main__":
    print("=" * 50)
    print("Multi-Supplier Scraper App - Quick Test")
    print("=" * 50)
    print()
    
    try:
        test_health()
        test_status()
        print("✅ Basic endpoints are working!")
        print()
        print("Next steps:")
        print("1. Make sure your .env file is configured")
        print("2. Visit: http://localhost:5000/auth/shopify?shop=YOUR-STORE.myshopify.com")
        print("3. Complete the OAuth flow")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to the app.")
        print("Make sure the Flask app is running: python app.py")
    except Exception as e:
        print(f"❌ Error: {e}")

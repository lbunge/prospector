#!/usr/bin/env python3
"""
Test script to diagnose SSL and Google Maps API connectivity issues.
Run this before using the main prospector tool.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

print("="*70)
print("Business Prospector - Connection Test")
print("="*70)

# Test 1: Python version
print(f"\n1. Python Version Check")
print(f"   Python {sys.version}")
python_version = sys.version_info
if python_version.major == 3 and python_version.minor >= 8:
    print("   ✓ Python version is compatible")
else:
    print("   ✗ Python 3.8+ required")

# Test 2: SSL/TLS support
print(f"\n2. SSL/TLS Support")
try:
    import ssl
    print(f"   OpenSSL version: {ssl.OPENSSL_VERSION}")
    print(f"   ✓ SSL support available")
except Exception as e:
    print(f"   ✗ SSL error: {e}")

# Test 3: Required packages
print(f"\n3. Required Packages")
packages = {
    'requests': 'HTTP library',
    'googlemaps': 'Google Maps API client',
    'certifi': 'SSL certificates',
    'urllib3': 'HTTP client',
    'beautifulsoup4': 'Web scraping',
    'pandas': 'Data processing',
}

missing = []
for package, description in packages.items():
    try:
        __import__(package)
        print(f"   ✓ {package}: {description}")
    except ImportError:
        print(f"   ✗ {package}: {description} - NOT INSTALLED")
        missing.append(package)

if missing:
    print(f"\n   To install missing packages:")
    print(f"   pip install {' '.join(missing)}")

# Test 4: Environment configuration
print(f"\n4. Environment Configuration")
try:
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv('GOOGLE_MAPS_API_KEY')
    if api_key:
        print(f"   ✓ GOOGLE_MAPS_API_KEY found (length: {len(api_key)})")
        # Don't print the actual key
        print(f"   Key starts with: {api_key[:10]}...")
    else:
        print(f"   ✗ GOOGLE_MAPS_API_KEY not set in .env file")
        print(f"   Please create a .env file and add your API key")
except Exception as e:
    print(f"   ✗ Error loading .env: {e}")

# Test 5: Basic HTTPS connection
print(f"\n5. HTTPS Connection Test")
try:
    import requests
    print("   Testing connection to Google...")
    response = requests.get('https://www.google.com', timeout=10)
    if response.status_code == 200:
        print(f"   ✓ HTTPS connection works")
    else:
        print(f"   ✗ Unexpected status code: {response.status_code}")
except Exception as e:
    print(f"   ✗ Connection failed: {e}")
    print(f"   This might be a network/proxy/firewall issue")

# Test 6: Google Maps API connectivity
print(f"\n6. Google Maps API Test")
try:
    api_key = os.getenv('GOOGLE_MAPS_API_KEY')
    if not api_key:
        print(f"   ⚠ Skipping (no API key configured)")
    else:
        print("   Testing Google Maps API connection...")
        import googlemaps
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        from urllib3.util.ssl_ import create_urllib3_context
        import ssl

        # Custom SSL adapter (same as in maps_scraper.py)
        class SSLAdapter(HTTPAdapter):
            def init_poolmanager(self, *args, **kwargs):
                ctx = create_urllib3_context()
                ctx.minimum_version = ssl.TLSVersion.TLSv1_2
                ctx.options |= 0x4  # OP_LEGACY_SERVER_CONNECT
                kwargs['ssl_context'] = ctx
                return super().init_poolmanager(*args, **kwargs)

        # Create session with SSL handling
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = SSLAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)

        # Test geocoding
        client = googlemaps.Client(key=api_key, requests_session=session)
        result = client.geocode("Seattle, WA")

        if result:
            print(f"   ✓ Google Maps API is working!")
            print(f"   Test geocode result: {result[0]['formatted_address']}")
        else:
            print(f"   ✗ API returned no results")

except ImportError as e:
    print(f"   ⚠ Skipping (missing package: {e})")
except Exception as e:
    error_msg = str(e)
    print(f"   ✗ API test failed: {error_msg}")

    # Provide specific help based on error
    if "SSL" in error_msg or "ssl" in error_msg:
        print(f"\n   SSL ERROR DETECTED - Try these fixes:")
        print(f"   1. Update certifi: pip install --upgrade certifi")
        print(f"   2. Update urllib3: pip install --upgrade urllib3")
        print(f"   3. Update requests: pip install --upgrade requests")
        print(f"   4. If using corporate network, check proxy settings")
    elif "API key" in error_msg or "REQUEST_DENIED" in error_msg:
        print(f"\n   API KEY ERROR - Check:")
        print(f"   1. Is your API key correct in .env?")
        print(f"   2. Have you enabled Places API in Google Cloud Console?")
        print(f"   3. Have you enabled Geocoding API in Google Cloud Console?")
    elif "OVER_QUERY_LIMIT" in error_msg:
        print(f"\n   QUOTA ERROR - You've exceeded your API quota")
        print(f"   Check usage at: https://console.cloud.google.com/")

# Summary
print(f"\n{'='*70}")
print("Summary")
print("="*70)

if not missing and api_key:
    print("✓ System appears ready to use!")
    print("\nTry running:")
    print('  python prospector.py "Seattle, WA" --radius 2000')
else:
    print("✗ Please fix the issues above before running prospector")
    if missing:
        print(f"\n1. Install missing packages:")
        print(f"   pip install -r requirements.txt")
    if not api_key:
        print(f"\n2. Set up your Google Maps API key:")
        print(f"   - Copy .env.example to .env")
        print(f"   - Add your API key to .env")

print()

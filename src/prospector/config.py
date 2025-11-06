"""Configuration management for the prospector tool."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration."""

    # API Keys
    GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
    YELP_API_KEY = os.getenv('YELP_API_KEY')
    HUNTER_API_KEY = os.getenv('HUNTER_API_KEY')
    ZEROBOUNCE_API_KEY = os.getenv('ZEROBOUNCE_API_KEY')
    HUBSPOT_API_KEY = os.getenv('HUBSPOT_API_KEY')

    # User agent for web scraping
    USER_AGENT = os.getenv(
        'USER_AGENT',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )

    # Output directory
    OUTPUT_DIR = Path('output')

    # Request timeouts
    REQUEST_TIMEOUT = 10  # seconds

    # Rate limiting
    REQUESTS_PER_SECOND = 2

    # Email scraping
    MAX_PAGES_PER_WEBSITE = 10  # Max pages to crawl per business website
    MAX_DEPTH_PER_WEBSITE = 2  # How many levels deep to crawl links

    # Search thoroughness
    USE_GRID_SEARCH = True  # Break large areas into grid for complete coverage
    GRID_SIZE_METERS = 2000  # Size of each grid cell
    MAX_RESULTS_PER_SEARCH = 60  # Google Places API limit

    # Website discovery
    FALLBACK_WEBSITE_SEARCH = True  # Use Google search if no website found
    SEARCH_SOCIAL_FOR_WEBSITE = True  # Check social media for website links

    # Data enrichment
    ENRICH_WITH_GOOGLE_SEARCH = True  # Search Google for additional info
    ENRICH_WITH_LINKEDIN = True  # Try to find LinkedIn company page
    ENRICH_WITH_YELP = True  # Use Yelp API for additional data
    DETECT_FRANCHISES = True  # Detect franchise/corporate vs local businesses
    DETECT_TECHNOLOGY = True  # Detect website technology stack
    ANALYZE_REVIEWS = True  # Analyze review sentiment and themes

    # Email enrichment
    FIND_EMPLOYEE_EMAILS = True  # Try to find employee/decision-maker emails
    VALIDATE_EMAILS = True  # Validate email deliverability
    PERMUTE_EMAILS = True  # Generate email permutations (firstname@, firstlast@, etc.)
    USE_HUNTER_API = True  # Use Hunter.io for email finding/validation
    USE_ZEROBOUNCE_API = True  # Use ZeroBounce for email verification

    # Phone validation
    VALIDATE_PHONES = True  # Validate and format phone numbers
    ENRICH_PHONE_DATA = True  # Get carrier, line type, etc.

    # Lead scoring
    ENABLE_LEAD_SCORING = True  # Calculate lead score (0-100)
    PRIORITIZE_LOCAL_CONTACTS = True  # Prefer local over corporate contacts

    # Aggressive mode (finds more data but slower)
    AGGRESSIVE_MODE = False  # Enable all advanced features

    # Batch processing and performance
    USE_BATCH_PROCESSING = False  # Enable batch processing with checkpoints
    BATCH_SIZE = 10  # Number of businesses to process before checkpointing
    ENABLE_RESUME = True  # Allow resuming from checkpoints after interruption
    MAX_CONCURRENT_REQUESTS = 3  # Max concurrent API requests (experimental)

    @classmethod
    def validate(cls):
        """Validate required configuration."""
        if not cls.GOOGLE_MAPS_API_KEY:
            raise ValueError(
                "GOOGLE_MAPS_API_KEY is required. "
                "Please set it in your .env file."
            )

    @classmethod
    def set_aggressive_mode(cls, enabled: bool = True):
        """Enable aggressive mode for maximum data collection."""
        cls.AGGRESSIVE_MODE = enabled
        if enabled:
            # Search settings
            cls.MAX_PAGES_PER_WEBSITE = 15
            cls.MAX_DEPTH_PER_WEBSITE = 3
            cls.USE_GRID_SEARCH = True
            cls.FALLBACK_WEBSITE_SEARCH = True
            cls.SEARCH_SOCIAL_FOR_WEBSITE = True

            # Enrichment
            cls.ENRICH_WITH_GOOGLE_SEARCH = True
            cls.ENRICH_WITH_LINKEDIN = True
            cls.ENRICH_WITH_YELP = True
            cls.DETECT_FRANCHISES = True
            cls.DETECT_TECHNOLOGY = True
            cls.ANALYZE_REVIEWS = True

            # Email enrichment
            cls.FIND_EMPLOYEE_EMAILS = True
            cls.VALIDATE_EMAILS = True
            cls.PERMUTE_EMAILS = True
            cls.USE_HUNTER_API = True
            cls.USE_ZEROBOUNCE_API = True

            # Phone validation
            cls.VALIDATE_PHONES = True
            cls.ENRICH_PHONE_DATA = True

            # Lead scoring
            cls.ENABLE_LEAD_SCORING = True
            cls.PRIORITIZE_LOCAL_CONTACTS = True

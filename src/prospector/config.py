"""Configuration management for the prospector tool."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration."""

    # Google Maps API
    GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')

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

    # Aggressive mode (finds more data but slower)
    AGGRESSIVE_MODE = False  # Enable all advanced features

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
            cls.MAX_PAGES_PER_WEBSITE = 15
            cls.MAX_DEPTH_PER_WEBSITE = 3
            cls.USE_GRID_SEARCH = True
            cls.FALLBACK_WEBSITE_SEARCH = True
            cls.SEARCH_SOCIAL_FOR_WEBSITE = True
            cls.ENRICH_WITH_GOOGLE_SEARCH = True
            cls.ENRICH_WITH_LINKEDIN = True

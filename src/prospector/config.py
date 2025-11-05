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
    MAX_PAGES_PER_WEBSITE = 5  # Max pages to crawl per business website

    @classmethod
    def validate(cls):
        """Validate required configuration."""
        if not cls.GOOGLE_MAPS_API_KEY:
            raise ValueError(
                "GOOGLE_MAPS_API_KEY is required. "
                "Please set it in your .env file."
            )

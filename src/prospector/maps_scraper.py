"""Google Maps Places API integration for business discovery."""

import googlemaps
import time
import ssl
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib3.util.ssl_ import create_urllib3_context
from typing import List, Dict, Optional, Tuple
from .config import Config


class SSLAdapter(HTTPAdapter):
    """Custom SSL adapter to handle SSL/TLS issues on Windows."""

    def init_poolmanager(self, *args, **kwargs):
        """Initialize pool manager with custom SSL context."""
        # Create a custom SSL context that's more permissive
        ctx = create_urllib3_context()
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.options |= 0x4  # OP_LEGACY_SERVER_CONNECT
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)


class GoogleMapsScaper:
    """Scraper for finding businesses using Google Maps Places API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Google Maps scraper.

        Args:
            api_key: Google Maps API key. If not provided, uses config.
        """
        self.api_key = api_key or Config.GOOGLE_MAPS_API_KEY
        if not self.api_key:
            raise ValueError("Google Maps API key is required")

        # Create a session with retry logic and SSL handling
        session = self._create_session()

        # Initialize Google Maps client with custom session
        self.client = googlemaps.Client(
            key=self.api_key,
            requests_session=session,
            retry_timeout=30
        )

    def _create_session(self) -> requests.Session:
        """
        Create a requests session with retry logic and SSL handling.

        Returns:
            Configured requests Session
        """
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=5,  # Total retries
            backoff_factor=1,  # Wait 1, 2, 4, 8, 16 seconds between retries
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )

        # Mount SSL adapter with retry strategy
        adapter = SSLAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        return session

    def search_businesses(
        self,
        location: str,
        radius: int = 5000,
        business_type: Optional[str] = None,
        keyword: Optional[str] = None
    ) -> List[Dict]:
        """
        Search for businesses in a specific area.

        Args:
            location: Address or coordinates (e.g., "downtown Seattle" or "47.6062,-122.3321")
            radius: Search radius in meters (default 5000m = ~3 miles)
            business_type: Business type filter (e.g., "restaurant", "retail", "lawyer")
            keyword: Additional keyword to filter results

        Returns:
            List of business dictionaries with basic information
        """
        # Geocode the location to get coordinates
        geocode_result = self.client.geocode(location)
        if not geocode_result:
            raise ValueError(f"Could not geocode location: {location}")

        location_coords = geocode_result[0]['geometry']['location']
        lat_lng = (location_coords['lat'], location_coords['lng'])

        print(f"Searching businesses near {location} ({lat_lng})")
        print(f"Radius: {radius}m, Type: {business_type or 'any'}, Keyword: {keyword or 'none'}")

        # Search for places
        all_results = []
        next_page_token = None

        while True:
            if next_page_token:
                # Wait before requesting next page (required by API)
                time.sleep(2)
                places_result = self.client.places_nearby(
                    location=lat_lng,
                    page_token=next_page_token
                )
            else:
                places_result = self.client.places_nearby(
                    location=lat_lng,
                    radius=radius,
                    type=business_type,
                    keyword=keyword
                )

            all_results.extend(places_result.get('results', []))

            # Check if there are more results
            next_page_token = places_result.get('next_page_token')
            if not next_page_token:
                break

        print(f"Found {len(all_results)} businesses")
        return all_results

    def get_business_details(self, place_id: str) -> Dict:
        """
        Get detailed information about a specific business.

        Args:
            place_id: Google Maps place ID

        Returns:
            Dictionary with detailed business information
        """
        details = self.client.place(
            place_id=place_id,
            fields=[
                'name',
                'formatted_address',
                'formatted_phone_number',
                'international_phone_number',
                'website',
                'url',  # Google Maps URL
                'business_status',
                'types',
                'price_level',
                'rating',
                'user_ratings_total',
                'opening_hours',
                'vicinity',
                'geometry',
                'plus_code',
                'utc_offset',
                'reviews',
                'photos',
                'editorial_summary'
            ]
        )

        return details.get('result', {})

    def extract_business_info(self, basic_info: Dict, detailed_info: Optional[Dict] = None) -> Dict:
        """
        Extract and format business information from API response.

        Args:
            basic_info: Basic info from places_nearby search
            detailed_info: Detailed info from place details API

        Returns:
            Formatted business information dictionary
        """
        # Start with basic info
        business = {
            'place_id': basic_info.get('place_id'),
            'name': basic_info.get('name'),
            'address': basic_info.get('vicinity'),
            'location': basic_info.get('geometry', {}).get('location', {}),
            'rating': basic_info.get('rating'),
            'user_ratings_total': basic_info.get('user_ratings_total'),
            'types': basic_info.get('types', []),
            'business_status': basic_info.get('business_status'),
            'price_level': basic_info.get('price_level'),
        }

        # Add detailed info if available
        if detailed_info:
            business.update({
                'formatted_address': detailed_info.get('formatted_address'),
                'phone': detailed_info.get('formatted_phone_number'),
                'international_phone': detailed_info.get('international_phone_number'),
                'website': detailed_info.get('website'),
                'google_maps_url': detailed_info.get('url'),
                'opening_hours': detailed_info.get('opening_hours', {}).get('weekday_text', []),
                'is_open_now': detailed_info.get('opening_hours', {}).get('open_now'),
                'editorial_summary': detailed_info.get('editorial_summary', {}).get('overview'),
            })

            # Extract categories/industry
            types = detailed_info.get('types', business.get('types', []))
            business['industry'] = self._extract_primary_category(types)
            business['categories'] = types

            # Determine if popular (high rating + many reviews)
            rating = detailed_info.get('rating', business.get('rating'))
            reviews = detailed_info.get('user_ratings_total', business.get('user_ratings_total'))
            business['is_popular'] = self._is_popular(rating, reviews)

        return business

    def _extract_primary_category(self, types: List[str]) -> str:
        """
        Extract primary business category from types list.

        Args:
            types: List of Google Maps types

        Returns:
            Primary category string
        """
        # Remove generic types
        exclude = {'point_of_interest', 'establishment', 'finance', 'health', 'food'}
        filtered = [t for t in types if t not in exclude]

        if filtered:
            # Convert snake_case to Title Case
            return filtered[0].replace('_', ' ').title()
        elif types:
            return types[0].replace('_', ' ').title()
        else:
            return 'Unknown'

    def _is_popular(self, rating: Optional[float], reviews: Optional[int]) -> bool:
        """
        Determine if a business is popular based on rating and review count.

        Args:
            rating: Average rating (0-5)
            reviews: Number of reviews

        Returns:
            True if considered popular
        """
        if rating is None or reviews is None:
            return False

        # Consider popular if rating >= 4.0 and has at least 50 reviews
        return rating >= 4.0 and reviews >= 50

    def search_and_enrich(
        self,
        location: str,
        radius: int = 5000,
        business_type: Optional[str] = None,
        keyword: Optional[str] = None,
        get_details: bool = True
    ) -> List[Dict]:
        """
        Search for businesses and optionally enrich with detailed info.

        Args:
            location: Search location
            radius: Search radius in meters
            business_type: Filter by business type
            keyword: Filter by keyword
            get_details: Whether to fetch detailed info for each business

        Returns:
            List of enriched business dictionaries
        """
        # Get basic business list
        businesses = self.search_businesses(location, radius, business_type, keyword)

        enriched = []
        for idx, business in enumerate(businesses, 1):
            print(f"Processing business {idx}/{len(businesses)}: {business.get('name')}")

            detailed_info = None
            if get_details:
                try:
                    detailed_info = self.get_business_details(business['place_id'])
                    time.sleep(0.1)  # Small delay to respect rate limits
                except Exception as e:
                    print(f"  Warning: Could not get details - {e}")

            enriched_business = self.extract_business_info(business, detailed_info)
            enriched.append(enriched_business)

        return enriched

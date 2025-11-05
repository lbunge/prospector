"""Google Maps Places API integration for business discovery."""

import googlemaps
import time
import ssl
import requests
import math
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib3.util.ssl_ import create_urllib3_context
from typing import List, Dict, Optional, Tuple, Set
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

    def _generate_grid_points(
        self,
        center_lat: float,
        center_lng: float,
        radius: int,
        grid_size: int = None
    ) -> List[Tuple[float, float]]:
        """
        Generate a grid of points to search for comprehensive coverage.

        Args:
            center_lat: Center latitude
            center_lng: Center longitude
            radius: Search radius in meters
            grid_size: Size of each grid cell in meters

        Returns:
            List of (lat, lng) tuples for grid search points
        """
        if grid_size is None:
            grid_size = Config.GRID_SIZE_METERS

        # Calculate how many grid points we need
        # Each grid point covers grid_size radius
        num_points = math.ceil(radius / grid_size)

        # Convert meters to approximate degrees
        # At equator: 1 degree ≈ 111,320 meters
        # For latitude, this is roughly constant
        # For longitude, it varies by latitude
        lat_degree = grid_size / 111320.0
        lng_degree = grid_size / (111320.0 * math.cos(math.radians(center_lat)))

        points = []

        # Generate grid around center point
        for lat_offset in range(-num_points, num_points + 1):
            for lng_offset in range(-num_points, num_points + 1):
                lat = center_lat + (lat_offset * lat_degree)
                lng = center_lng + (lng_offset * lng_degree)

                # Check if point is within original search radius
                distance = self._haversine_distance(
                    center_lat, center_lng, lat, lng
                )

                if distance <= radius:
                    points.append((lat, lng))

        return points

    def _haversine_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """
        Calculate distance between two points in meters using Haversine formula.

        Args:
            lat1, lon1: First point
            lat2, lon2: Second point

        Returns:
            Distance in meters
        """
        R = 6371000  # Earth's radius in meters

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (math.sin(delta_phi / 2) ** 2 +
             math.cos(phi1) * math.cos(phi2) *
             math.sin(delta_lambda / 2) ** 2)

        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def search_businesses(
        self,
        location: str,
        radius: int = 5000,
        business_type: Optional[str] = None,
        keyword: Optional[str] = None,
        use_grid_search: bool = None
    ) -> List[Dict]:
        """
        Search for businesses in a specific area with optional grid search for thorough coverage.

        Args:
            location: Address or coordinates (e.g., "downtown Seattle" or "47.6062,-122.3321")
            radius: Search radius in meters (default 5000m = ~3 miles)
            business_type: Business type filter (e.g., "restaurant", "retail", "lawyer")
            keyword: Additional keyword to filter results
            use_grid_search: Whether to use grid search (default from config)

        Returns:
            List of business dictionaries with basic information
        """
        if use_grid_search is None:
            use_grid_search = Config.USE_GRID_SEARCH and radius > Config.GRID_SIZE_METERS

        # Geocode the location to get coordinates
        geocode_result = self.client.geocode(location)
        if not geocode_result:
            raise ValueError(f"Could not geocode location: {location}")

        location_coords = geocode_result[0]['geometry']['location']
        center_lat = location_coords['lat']
        center_lng = location_coords['lng']

        print(f"Searching businesses near {location} ({center_lat}, {center_lng})")
        print(f"Radius: {radius}m, Type: {business_type or 'any'}, Keyword: {keyword or 'none'}")

        if use_grid_search:
            print(f"Using grid search for comprehensive coverage...")
            return self._grid_search_businesses(
                center_lat, center_lng, radius, business_type, keyword
            )
        else:
            return self._single_point_search(
                (center_lat, center_lng), radius, business_type, keyword
            )

    def _single_point_search(
        self,
        lat_lng: Tuple[float, float],
        radius: int,
        business_type: Optional[str] = None,
        keyword: Optional[str] = None
    ) -> List[Dict]:
        """
        Search for businesses from a single point.

        Args:
            lat_lng: (latitude, longitude) tuple
            radius: Search radius in meters
            business_type: Business type filter
            keyword: Keyword filter

        Returns:
            List of business dictionaries
        """
        all_results = []
        next_page_token = None
        seen_place_ids: Set[str] = set()

        # Google Places API returns max 60 results (20 per page, 3 pages)
        page = 0
        while page < 3:  # Max 3 pages
            try:
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

                results = places_result.get('results', [])

                # Deduplicate based on place_id
                for result in results:
                    place_id = result.get('place_id')
                    if place_id and place_id not in seen_place_ids:
                        seen_place_ids.add(place_id)
                        all_results.append(result)

                # Check if there are more results
                next_page_token = places_result.get('next_page_token')
                if not next_page_token:
                    break

                page += 1

            except Exception as e:
                print(f"  Warning: Error fetching page {page + 1}: {e}")
                break

        return all_results

    def _grid_search_businesses(
        self,
        center_lat: float,
        center_lng: float,
        radius: int,
        business_type: Optional[str] = None,
        keyword: Optional[str] = None
    ) -> List[Dict]:
        """
        Perform grid-based search for comprehensive coverage.

        Args:
            center_lat: Center latitude
            center_lng: Center longitude
            radius: Search radius in meters
            business_type: Business type filter
            keyword: Keyword filter

        Returns:
            Deduplicated list of businesses
        """
        # Generate grid points
        grid_points = self._generate_grid_points(center_lat, center_lng, radius)

        print(f"  Grid search: {len(grid_points)} search points")

        all_businesses = []
        seen_place_ids: Set[str] = set()

        for idx, (lat, lng) in enumerate(grid_points, 1):
            print(f"  Searching grid point {idx}/{len(grid_points)}...", end='\r')

            try:
                # Search from this grid point with smaller radius
                results = self._single_point_search(
                    (lat, lng),
                    Config.GRID_SIZE_METERS,
                    business_type,
                    keyword
                )

                # Deduplicate
                for result in results:
                    place_id = result.get('place_id')
                    if place_id and place_id not in seen_place_ids:
                        seen_place_ids.add(place_id)
                        all_businesses.append(result)

                # Small delay to respect rate limits
                time.sleep(0.2)

            except Exception as e:
                print(f"\n  Warning: Error at grid point {idx}: {e}")
                continue

        print(f"\n  Grid search complete: {len(all_businesses)} unique businesses found")
        return all_businesses

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

"""Yelp API integration for additional business data enrichment."""

import requests
import time
from typing import Dict, Optional, List
from .config import Config


class YelpEnricher:
    """Enrich business data using Yelp Fusion API."""

    API_BASE = "https://api.yelp.com/v3"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Yelp enricher.

        Args:
            api_key: Yelp API key (uses config if not provided)
        """
        self.api_key = api_key or Config.YELP_API_KEY
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_key}'
            })

    def is_available(self) -> bool:
        """Check if Yelp API is available."""
        return bool(self.api_key)

    def find_business(
        self,
        name: str,
        address: Optional[str] = None,
        phone: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None
    ) -> Optional[Dict]:
        """
        Find a business on Yelp by name and location.

        Args:
            name: Business name
            address: Business address
            phone: Business phone
            latitude: Latitude
            longitude: Longitude

        Returns:
            Yelp business data or None
        """
        if not self.is_available():
            return None

        try:
            # First try phone match (most accurate)
            if phone:
                result = self._search_by_phone(phone)
                if result:
                    return result

            # Then try name + location
            if name and (address or (latitude and longitude)):
                result = self._search_by_name_location(name, address, latitude, longitude)
                if result:
                    return result

        except Exception as e:
            print(f"    Warning: Yelp search failed: {e}")

        return None

    def _search_by_phone(self, phone: str) -> Optional[Dict]:
        """
        Search Yelp by phone number.

        Args:
            phone: Phone number

        Returns:
            Business data or None
        """
        try:
            # Clean phone number (Yelp wants +1XXXXXXXXXX format)
            clean_phone = ''.join(filter(str.isdigit, phone))
            if len(clean_phone) == 10:
                clean_phone = f"+1{clean_phone}"
            elif len(clean_phone) == 11 and clean_phone.startswith('1'):
                clean_phone = f"+{clean_phone}"
            else:
                return None

            url = f"{self.API_BASE}/businesses/search/phone"
            params = {'phone': clean_phone}

            response = self.session.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                businesses = data.get('businesses', [])
                if businesses:
                    return self._enrich_business_details(businesses[0])

        except Exception:
            pass

        return None

    def _search_by_name_location(
        self,
        name: str,
        address: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None
    ) -> Optional[Dict]:
        """
        Search Yelp by business name and location.

        Args:
            name: Business name
            address: Address
            latitude: Latitude
            longitude: Longitude

        Returns:
            Business data or None
        """
        try:
            url = f"{self.API_BASE}/businesses/search"
            params = {
                'term': name,
                'limit': 5
            }

            if latitude and longitude:
                params['latitude'] = latitude
                params['longitude'] = longitude
            elif address:
                params['location'] = address

            response = self.session.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                businesses = data.get('businesses', [])

                # Find best match by name similarity
                for business in businesses:
                    if self._is_name_match(name, business.get('name', '')):
                        return self._enrich_business_details(business)

        except Exception:
            pass

        return None

    def _is_name_match(self, name1: str, name2: str) -> bool:
        """
        Check if two business names match (fuzzy).

        Args:
            name1: First name
            name2: Second name

        Returns:
            True if names match
        """
        # Simple fuzzy matching
        n1 = name1.lower().replace(',', '').replace('.', '').replace("'", '')
        n2 = name2.lower().replace(',', '').replace('.', '').replace("'", '')

        # Exact match
        if n1 == n2:
            return True

        # One contains the other
        if n1 in n2 or n2 in n1:
            return True

        # Words match (at least 2 common words)
        words1 = set(n1.split())
        words2 = set(n2.split())
        common = words1 & words2
        if len(common) >= 2:
            return True

        return False

    def _enrich_business_details(self, business_data: Dict) -> Dict:
        """
        Enrich with detailed business information.

        Args:
            business_data: Basic business data from search

        Returns:
            Enriched business data
        """
        business_id = business_data.get('id')
        if not business_id:
            return business_data

        try:
            # Get full business details
            url = f"{self.API_BASE}/businesses/{business_id}"
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                detailed = response.json()

                # Get reviews
                time.sleep(0.2)  # Rate limiting
                reviews = self._get_reviews(business_id)
                if reviews:
                    detailed['sample_reviews'] = reviews

                return detailed

        except Exception:
            pass

        return business_data

    def _get_reviews(self, business_id: str, limit: int = 3) -> Optional[List[Dict]]:
        """
        Get reviews for a business.

        Args:
            business_id: Yelp business ID
            limit: Number of reviews to fetch

        Returns:
            List of reviews or None
        """
        try:
            url = f"{self.API_BASE}/businesses/{business_id}/reviews"
            params = {'limit': limit}

            response = self.session.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                return data.get('reviews', [])

        except Exception:
            pass

        return None

    def extract_yelp_info(self, yelp_data: Dict) -> Dict:
        """
        Extract useful information from Yelp data.

        Args:
            yelp_data: Raw Yelp API response

        Returns:
            Formatted Yelp information
        """
        info = {
            'yelp_id': yelp_data.get('id'),
            'yelp_url': yelp_data.get('url'),
            'yelp_rating': yelp_data.get('rating'),
            'yelp_review_count': yelp_data.get('review_count'),
            'yelp_price': yelp_data.get('price'),
            'yelp_categories': [c['title'] for c in yelp_data.get('categories', [])],
            'yelp_transactions': yelp_data.get('transactions', []),
            'yelp_photos': yelp_data.get('photos', [])[:3],  # First 3 photos
            'hours': yelp_data.get('hours', []),
            'is_claimed': yelp_data.get('is_claimed', False),
            'is_closed': yelp_data.get('is_closed', False),
        }

        # Extract attributes
        attributes = yelp_data.get('attributes', {})
        if attributes:
            info['outdoor_seating'] = attributes.get('outdoor_seating')
            info['wheelchair_accessible'] = attributes.get('wheelchair_accessible')
            info['good_for_groups'] = attributes.get('good_for_groups')
            info['reservations'] = attributes.get('reservations')
            info['takes_reservations'] = attributes.get('takes_reservations')
            info['delivery'] = attributes.get('delivery')
            info['takeout'] = attributes.get('takeout')

        # Extract special hours (e.g., holiday hours)
        special_hours = yelp_data.get('special_hours', [])
        if special_hours:
            info['special_hours'] = special_hours

        # Extract messaging info
        messaging = yelp_data.get('messaging', {})
        if messaging:
            info['messaging_url'] = messaging.get('url')

        # Extract reviews sentiment
        reviews = yelp_data.get('sample_reviews', [])
        if reviews:
            info['recent_reviews'] = [
                {
                    'rating': r.get('rating'),
                    'text': r.get('text', '')[:200],  # First 200 chars
                    'time_created': r.get('time_created'),
                    'user_name': r.get('user', {}).get('name')
                }
                for r in reviews
            ]

            # Calculate average recent rating
            ratings = [r.get('rating', 0) for r in reviews]
            if ratings:
                info['recent_avg_rating'] = sum(ratings) / len(ratings)

        return info

    def analyze_reviews(self, reviews: List[Dict]) -> Dict:
        """
        Analyze reviews for sentiment and themes.

        Args:
            reviews: List of review dictionaries

        Returns:
            Review analysis
        """
        if not reviews:
            return {}

        analysis = {
            'total_reviews': len(reviews),
            'avg_rating': 0,
            'sentiment': 'neutral',
            'common_themes': [],
        }

        # Calculate average rating
        ratings = [r.get('rating', 0) for r in reviews]
        if ratings:
            avg = sum(ratings) / len(ratings)
            analysis['avg_rating'] = round(avg, 2)

            # Determine sentiment
            if avg >= 4.0:
                analysis['sentiment'] = 'positive'
            elif avg >= 3.0:
                analysis['sentiment'] = 'neutral'
            else:
                analysis['sentiment'] = 'negative'

        # Extract common themes (simple keyword extraction)
        texts = [r.get('text', '').lower() for r in reviews]
        all_text = ' '.join(texts)

        # Common positive words
        positive_themes = {
            'service': ['service', 'staff', 'friendly', 'helpful'],
            'quality': ['quality', 'excellent', 'great', 'amazing', 'best'],
            'value': ['value', 'price', 'affordable', 'cheap', 'reasonable'],
            'atmosphere': ['atmosphere', 'ambiance', 'cozy', 'clean', 'nice'],
        }

        for theme, keywords in positive_themes.items():
            count = sum(all_text.count(kw) for kw in keywords)
            if count > 0:
                analysis['common_themes'].append({
                    'theme': theme,
                    'mentions': count
                })

        # Sort by mentions
        analysis['common_themes'].sort(key=lambda x: x['mentions'], reverse=True)

        return analysis

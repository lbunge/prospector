"""Business enrichment module to combine all data sources."""

import time
from typing import List, Dict, Optional
from .maps_scraper import GoogleMapsScaper
from .email_finder import EmailFinder
from .config import Config


class BusinessEnricher:
    """Enrich business data with emails and additional information."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the business enricher.

        Args:
            api_key: Google Maps API key
        """
        self.maps_scraper = GoogleMapsScaper(api_key)
        self.email_finder = EmailFinder()

    def prospect_area(
        self,
        location: str,
        radius: int = 5000,
        business_type: Optional[str] = None,
        keyword: Optional[str] = None,
        find_emails: bool = True,
        find_social: bool = True
    ) -> List[Dict]:
        """
        Prospect businesses in an area and enrich with contact information.

        Args:
            location: Location to search (address or coordinates)
            radius: Search radius in meters
            business_type: Filter by business type
            keyword: Filter by keyword
            find_emails: Whether to scrape websites for emails
            find_social: Whether to find social media profiles

        Returns:
            List of enriched business dictionaries
        """
        print(f"\n{'='*60}")
        print(f"Starting prospecting campaign")
        print(f"{'='*60}\n")

        # Step 1: Get businesses from Google Maps
        print("Step 1: Discovering businesses from Google Maps...")
        businesses = self.maps_scraper.search_and_enrich(
            location=location,
            radius=radius,
            business_type=business_type,
            keyword=keyword,
            get_details=True
        )

        print(f"\nFound {len(businesses)} businesses")

        # Step 2: Enrich with emails and social media
        if find_emails or find_social:
            print(f"\nStep 2: Enriching business data...")

        enriched_businesses = []
        for idx, business in enumerate(businesses, 1):
            print(f"\n[{idx}/{len(businesses)}] Enriching: {business['name']}")

            enriched = business.copy()

            # Initialize email and social fields
            enriched['emails_found'] = []
            enriched['email_count'] = 0
            enriched['generic_emails'] = []
            enriched['person_emails'] = []
            enriched['social_media'] = {}

            # Find emails if website exists
            if find_emails and business.get('website'):
                print(f"  → Searching for emails on website...")
                try:
                    email_result = self.email_finder.find_emails_from_website(
                        business['website']
                    )

                    if email_result['status'] == 'success':
                        enriched['emails_found'] = email_result['emails']
                        enriched['email_count'] = len(email_result['emails'])

                        # Separate generic and person emails
                        enriched['generic_emails'] = [
                            e['email'] for e in email_result['emails']
                            if e['type'] == 'generic'
                        ]
                        enriched['person_emails'] = [
                            e['email'] for e in email_result['emails']
                            if e['type'] == 'person'
                        ]

                        print(f"  ✓ Found {enriched['email_count']} emails "
                              f"({len(enriched['generic_emails'])} generic, "
                              f"{len(enriched['person_emails'])} person)")
                    else:
                        print(f"  ✗ Email search failed: {email_result['error']}")

                    time.sleep(0.5)  # Be respectful with requests

                except Exception as e:
                    print(f"  ✗ Error finding emails: {e}")

            elif not business.get('website'):
                print(f"  → No website available for email search")

            # Find social media
            if find_social and business.get('website'):
                try:
                    enriched['social_media'] = self.email_finder.find_social_media(
                        business['website']
                    )
                    if enriched['social_media']:
                        platforms = ', '.join(enriched['social_media'].keys())
                        print(f"  ✓ Found social media: {platforms}")

                except Exception as e:
                    print(f"  ✗ Error finding social media: {e}")

            enriched_businesses.append(enriched)

        print(f"\n{'='*60}")
        print(f"Prospecting complete!")
        print(f"{'='*60}")
        print(f"Total businesses: {len(enriched_businesses)}")

        businesses_with_emails = sum(1 for b in enriched_businesses if b['email_count'] > 0)
        total_emails = sum(b['email_count'] for b in enriched_businesses)

        print(f"Businesses with emails: {businesses_with_emails}")
        print(f"Total emails found: {total_emails}")

        return enriched_businesses

    def enrich_single_business(
        self,
        business_name: str,
        location: Optional[str] = None,
        website: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Enrich a single business by name.

        Args:
            business_name: Name of the business
            location: Optional location context
            website: Optional website URL (if known)

        Returns:
            Enriched business dictionary or None if not found
        """
        # If we have a website, use it directly
        if website:
            enriched = {
                'name': business_name,
                'website': website,
                'emails_found': [],
                'social_media': {}
            }

            # Find emails
            email_result = self.email_finder.find_emails_from_website(website)
            if email_result['status'] == 'success':
                enriched['emails_found'] = email_result['emails']

            # Find social media
            enriched['social_media'] = self.email_finder.find_social_media(website)

            return enriched

        # Otherwise, search Google Maps
        query = business_name
        if location:
            query += f" {location}"

        businesses = self.maps_scraper.search_businesses(
            location=query,
            radius=1000
        )

        if not businesses:
            return None

        # Get details for first match
        place_id = businesses[0]['place_id']
        details = self.maps_scraper.get_business_details(place_id)
        enriched = self.maps_scraper.extract_business_info(businesses[0], details)

        # Find emails if website exists
        if enriched.get('website'):
            email_result = self.email_finder.find_emails_from_website(
                enriched['website']
            )
            if email_result['status'] == 'success':
                enriched['emails_found'] = email_result['emails']

            enriched['social_media'] = self.email_finder.find_social_media(
                enriched['website']
            )

        return enriched

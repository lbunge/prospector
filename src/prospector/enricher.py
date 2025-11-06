"""Business enrichment module to combine all data sources."""

import time
from typing import List, Dict, Optional
from .maps_scraper import GoogleMapsScaper
from .email_finder import EmailFinder
from .website_finder import WebsiteFinder
from .yelp_enricher import YelpEnricher
from .email_validator import EmailValidator
from .phone_validator import PhoneValidator
from .franchise_detector import FranchiseDetector
from .lead_scorer import LeadScorer
from .config import Config


class BusinessEnricher:
    """Enrich business data with emails and additional comprehensive information."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the business enricher.

        Args:
            api_key: Google Maps API key
        """
        self.maps_scraper = GoogleMapsScaper(api_key)
        self.email_finder = EmailFinder()
        self.website_finder = WebsiteFinder()
        self.yelp_enricher = YelpEnricher()
        self.email_validator = EmailValidator()
        self.phone_validator = PhoneValidator()
        self.franchise_detector = FranchiseDetector()
        self.lead_scorer = LeadScorer()

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
            enriched['website_method'] = None

            # Step 1: Try to find website if not provided by Google
            website = business.get('website')
            if not website and (find_emails or find_social):
                print(f"  → No website in Google Maps, searching...")
                try:
                    website_result = self.website_finder.find_website(
                        business['name'],
                        business.get('formatted_address') or business.get('address'),
                        business.get('phone')
                    )

                    if website_result['website']:
                        website = website_result['website']
                        enriched['website'] = website
                        enriched['website_method'] = website_result['method']
                        enriched['website_confidence'] = website_result['confidence']
                        print(f"  ✓ Found website: {website} ({website_result['method']})")
                    else:
                        print(f"  ✗ Could not find website")

                    time.sleep(0.3)  # Be respectful

                except Exception as e:
                    print(f"  ✗ Error searching for website: {e}")

            # Step 2: Find social media first (might help find website)
            if find_social and website:
                try:
                    enriched['social_media'] = self.email_finder.find_social_media(website)

                    if enriched['social_media']:
                        platforms = ', '.join(enriched['social_media'].keys())
                        print(f"  ✓ Found social media: {platforms}")

                        # Try to find website from social media if we don't have one
                        if not website:
                            social_website = self.website_finder.enrich_from_social_media(
                                enriched['social_media']
                            )
                            if social_website:
                                website = social_website
                                enriched['website'] = website
                                enriched['website_method'] = 'social_media'
                                print(f"  ✓ Found website from social media: {website}")

                except Exception as e:
                    print(f"  ✗ Error finding social media: {e}")

            # Step 3: Find emails from website
            if find_emails and website:
                print(f"  → Searching for emails on website...")
                try:
                    email_result = self.email_finder.find_emails_from_website(website)

                    if email_result['status'] == 'success':
                        enriched['emails_found'] = email_result['emails']
                        enriched['email_count'] = len(email_result['emails'])
                        enriched['pages_crawled'] = email_result.get('pages_crawled', 0)

                        # Separate generic and person emails
                        enriched['generic_emails'] = [
                            e['email'] for e in email_result['emails']
                            if e['type'] == 'generic'
                        ]
                        enriched['person_emails'] = [
                            e['email'] for e in email_result['emails']
                            if e['type'] == 'person'
                        ]

                        if enriched['email_count'] > 0:
                            print(f"  ✓ Found {enriched['email_count']} emails "
                                  f"({len(enriched['generic_emails'])} generic, "
                                  f"{len(enriched['person_emails'])} person) "
                                  f"from {enriched['pages_crawled']} pages")
                        else:
                            print(f"  ○ No emails found on website")
                    else:
                        print(f"  ✗ Email search failed: {email_result['error']}")

                    time.sleep(0.5)  # Be respectful with requests

                except Exception as e:
                    print(f"  ✗ Error finding emails: {e}")

            elif not website:
                print(f"  ○ No website available for scraping")

            # Step 4: Yelp enrichment
            if Config.ENRICH_WITH_YELP and self.yelp_enricher.is_available():
                try:
                    print(f"  → Enriching with Yelp data...")
                    yelp_data = self.yelp_enricher.find_business(
                        enriched['name'],
                        enriched.get('formatted_address') or enriched.get('address'),
                        enriched.get('phone'),
                        enriched.get('location', {}).get('lat'),
                        enriched.get('location', {}).get('lng')
                    )

                    if yelp_data:
                        yelp_info = self.yelp_enricher.extract_yelp_info(yelp_data)
                        enriched['yelp_data'] = yelp_info

                        yelp_rating = yelp_info.get('yelp_rating')
                        yelp_reviews = yelp_info.get('yelp_review_count', 0)
                        if yelp_rating:
                            print(f"  ✓ Yelp: {yelp_rating}★ ({yelp_reviews} reviews)")

                        # Analyze reviews
                        if Config.ANALYZE_REVIEWS and yelp_info.get('recent_reviews'):
                            analysis = self.yelp_enricher.analyze_reviews(yelp_info['recent_reviews'])
                            enriched['review_analysis'] = analysis

                    time.sleep(0.3)

                except Exception as e:
                    print(f"  ✗ Error enriching with Yelp: {e}")

            # Step 5: Email validation and enrichment
            if Config.VALIDATE_EMAILS and enriched.get('emails_found'):
                try:
                    print(f"  → Validating emails...")
                    enriched['emails_found'] = self.email_validator.enrich_emails_with_validation(
                        enriched['emails_found'],
                        validate=True
                    )

                    validated_count = sum(
                        1 for e in enriched['emails_found']
                        if e.get('is_deliverable', False)
                    )
                    if validated_count > 0:
                        print(f"  ✓ {validated_count}/{len(enriched['emails_found'])} emails validated")

                    time.sleep(0.2)

                except Exception as e:
                    print(f"  ✗ Error validating emails: {e}")

            # Step 6: Email permutation (find additional emails)
            if Config.PERMUTE_EMAILS and website:
                try:
                    domain = self.email_validator._extract_domain(website)
                    if domain:
                        # Generate role-based emails
                        decision_maker_emails = self.email_validator.find_decision_maker_emails(
                            enriched['name'],
                            domain,
                            self.phone_validator.extract_area_code(enriched.get('phone') or '')
                        )

                        if decision_maker_emails:
                            print(f"  ✓ Generated {len(decision_maker_emails)} role-based emails")
                            # Add to emails list (marked as generated)
                            for email_info in decision_maker_emails:
                                if email_info not in enriched['emails_found']:
                                    enriched['emails_found'].append(email_info)
                                    enriched['email_count'] = len(enriched['emails_found'])

                except Exception as e:
                    print(f"  ✗ Error generating email permutations: {e}")

            # Step 7: Phone validation
            if Config.VALIDATE_PHONES and enriched.get('phone'):
                try:
                    phone_validation = self.phone_validator.validate_and_format(
                        enriched['phone']
                    )
                    enriched['phone_validation'] = phone_validation

                    if phone_validation.get('valid'):
                        formatted = phone_validation.get('formatted_national')
                        phone_type = phone_validation.get('type', 'unknown')
                        print(f"  ✓ Phone validated: {formatted} ({phone_type})")

                except Exception as e:
                    print(f"  ✗ Error validating phone: {e}")

            # Step 8: Franchise detection
            if Config.DETECT_FRANCHISES:
                try:
                    franchise_detection = self.franchise_detector.detect_franchise(
                        enriched['name'],
                        enriched.get('website'),
                        enriched.get('phone'),
                        enriched.get('formatted_address') or enriched.get('address'),
                        enriched.get('categories')
                    )
                    enriched['franchise_detection'] = franchise_detection

                    if franchise_detection.get('is_franchise'):
                        chain = franchise_detection.get('chain_name', 'Unknown')
                        print(f"  ℹ Detected as franchise: {chain}")
                    elif franchise_detection.get('is_corporate'):
                        print(f"  ℹ Detected as corporate location")
                    else:
                        print(f"  ✓ Local independent business")

                    # Find local contact hints
                    local_hints = self.franchise_detector.find_local_contact_hints(enriched)
                    enriched['local_contact_hints'] = local_hints

                    # Prioritize local contacts
                    if Config.PRIORITIZE_LOCAL_CONTACTS:
                        enriched = self.franchise_detector.prioritize_local_contacts(enriched)

                except Exception as e:
                    print(f"  ✗ Error detecting franchise: {e}")

            # Step 9: Lead scoring
            if Config.ENABLE_LEAD_SCORING:
                try:
                    lead_score = self.lead_scorer.score_lead(enriched)
                    enriched['lead_score'] = lead_score

                    print(f"  📊 Lead Score: {lead_score['total']}/100 (Grade: {lead_score['grade']}, Priority: {lead_score['priority']})")

                except Exception as e:
                    print(f"  ✗ Error calculating lead score: {e}")

            enriched_businesses.append(enriched)

        # Sort businesses by lead score (if scoring enabled)
        if Config.ENABLE_LEAD_SCORING:
            enriched_businesses = self.lead_scorer.batch_score_leads(enriched_businesses)

        print(f"\n{'='*60}")
        print(f"Prospecting Complete!")
        print(f"{'='*60}")
        print(f"Total businesses: {len(enriched_businesses)}")

        # Email statistics
        businesses_with_emails = sum(1 for b in enriched_businesses if b.get('email_count', 0) > 0)
        total_emails = sum(b.get('email_count', 0) for b in enriched_businesses)
        validated_emails = sum(
            sum(1 for e in b.get('emails_found', []) if e.get('is_deliverable', False))
            for b in enriched_businesses
        )

        print(f"\n📧 Email Discovery:")
        print(f"  Businesses with emails: {businesses_with_emails}/{len(enriched_businesses)} ({businesses_with_emails/len(enriched_businesses)*100:.1f}%)")
        print(f"  Total emails found: {total_emails}")
        if validated_emails > 0:
            print(f"  Validated emails: {validated_emails}")

        # Website statistics
        businesses_with_websites = sum(1 for b in enriched_businesses if b.get('website'))
        print(f"\n🌐 Website Coverage:")
        print(f"  Businesses with websites: {businesses_with_websites}/{len(enriched_businesses)} ({businesses_with_websites/len(enriched_businesses)*100:.1f}%)")

        # Yelp statistics
        if Config.ENRICH_WITH_YELP:
            businesses_with_yelp = sum(1 for b in enriched_businesses if b.get('yelp_data'))
            if businesses_with_yelp > 0:
                print(f"\n⭐ Yelp Data:")
                print(f"  Businesses found on Yelp: {businesses_with_yelp}")

        # Franchise detection
        if Config.DETECT_FRANCHISES:
            local_businesses = sum(1 for b in enriched_businesses if b.get('franchise_detection', {}).get('is_local'))
            franchises = sum(1 for b in enriched_businesses if b.get('franchise_detection', {}).get('is_franchise'))
            print(f"\n🏪 Business Classification:")
            print(f"  Local/Independent: {local_businesses}")
            print(f"  Franchises/Chains: {franchises}")

        # Lead scoring summary
        if Config.ENABLE_LEAD_SCORING:
            high_priority = sum(1 for b in enriched_businesses if b.get('lead_score', {}).get('priority') in ['urgent', 'high'])
            avg_score = sum(b.get('lead_score', {}).get('total', 0) for b in enriched_businesses) / len(enriched_businesses) if enriched_businesses else 0

            print(f"\n📊 Lead Quality:")
            print(f"  Average lead score: {avg_score:.1f}/100")
            print(f"  High priority leads: {high_priority}")

            # Show top 5 leads
            print(f"\n🎯 Top 5 Leads:")
            for i, business in enumerate(enriched_businesses[:5], 1):
                score = business.get('lead_score', {})
                name = business.get('name', 'Unknown')
                total_score = score.get('total', 0)
                grade = score.get('grade', 'N/A')
                email_count = business.get('email_count', 0)
                print(f"  {i}. {name}: {total_score}/100 ({grade}) - {email_count} emails")

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

"""HubSpot CRM export and integration module."""

import requests
import pandas as pd
from typing import List, Dict, Optional
from pathlib import Path
from .config import Config


class HubSpotExporter:
    """Export data to HubSpot CRM."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize HubSpot exporter.

        Args:
            api_key: HubSpot API key (uses config if not provided)
        """
        self.api_key = api_key or Config.HUBSPOT_API_KEY
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            })

    def is_available(self) -> bool:
        """Check if HubSpot API is available."""
        return bool(self.api_key)

    def export_to_hubspot_csv(
        self,
        businesses: List[Dict],
        output_path: Path,
        include_custom_fields: bool = True
    ) -> Path:
        """
        Export businesses to HubSpot-compatible CSV.

        Args:
            businesses: List of business dictionaries
            output_path: Output file path
            include_custom_fields: Include custom enrichment fields

        Returns:
            Path to exported file
        """
        rows = []

        for business in businesses:
            # Get primary contact info
            primary_email = self._get_primary_email(business)
            primary_phone = business.get('phone') or business.get('formatted_phone_number')

            # Base HubSpot company fields
            row = {
                # Required fields
                'Company name': business.get('name'),
                'Company domain name': self._extract_domain(business.get('website')),

                # Contact information
                'Phone number': primary_phone,
                'Website URL': business.get('website'),

                # Address fields
                'Street address': self._format_street_address(business),
                'City': self._extract_city(business),
                'State/Region': self._extract_state(business),
                'Postal code': self._extract_postal_code(business),
                'Country': 'United States',  # Assuming US

                # Company details
                'Industry': business.get('industry') or self._format_categories(business),
                'Type': self._get_business_type(business),
                'Description': self._create_description(business),

                # Custom metrics
                'Google Rating': business.get('rating'),
                'Review Count': business.get('user_ratings_total'),
                'Yelp Rating': business.get('yelp_data', {}).get('yelp_rating'),
                'Yelp Reviews': business.get('yelp_data', {}).get('yelp_review_count'),
            }

            # Add custom enrichment fields
            if include_custom_fields:
                lead_score = business.get('lead_score', {})
                franchise_data = business.get('franchise_detection', {})

                row.update({
                    # Lead scoring
                    'Lead Score': lead_score.get('total'),
                    'Lead Grade': lead_score.get('grade'),
                    'Lead Priority': lead_score.get('priority'),

                    # Business classification
                    'Is Franchise': 'Yes' if franchise_data.get('is_franchise') else 'No',
                    'Is Local Business': 'Yes' if franchise_data.get('is_local') else 'No',
                    'Is Corporate': 'Yes' if franchise_data.get('is_corporate') else 'No',
                    'Chain Name': franchise_data.get('chain_name'),

                    # Social media
                    'Facebook URL': business.get('social_media', {}).get('facebook'),
                    'LinkedIn URL': business.get('social_media', {}).get('linkedin'),
                    'Twitter URL': business.get('social_media', {}).get('twitter'),
                    'Instagram URL': business.get('social_media', {}).get('instagram'),

                    # Additional data
                    'Google Maps URL': business.get('google_maps_url'),
                    'Yelp URL': business.get('yelp_data', {}).get('yelp_url'),
                    'Is Popular': 'Yes' if business.get('is_popular') else 'No',
                    'Business Status': business.get('business_status'),
                    'Email Count': business.get('email_count', 0),
                })

            rows.append(row)

            # Create additional rows for additional emails (as contacts)
            emails = business.get('emails_found', [])
            for email_info in emails[1:]:  # Skip first email (already used as primary)
                contact_row = self._create_contact_row(business, email_info)
                if contact_row:
                    rows.append(contact_row)

        # Create DataFrame and export
        df = pd.DataFrame(rows)

        # Remove columns with all None values
        df = df.dropna(axis=1, how='all')

        # Export to CSV
        df.to_csv(output_path, index=False, encoding='utf-8-sig')  # UTF-8 with BOM for Excel

        print(f"\n✓ Exported {len(df)} rows to HubSpot CSV: {output_path}")
        print(f"  Companies: {len(businesses)}")
        print(f"  Additional contacts: {len(rows) - len(businesses)}")

        return output_path

    def create_company_api(self, business: Dict) -> Optional[Dict]:
        """
        Create a company in HubSpot via API.

        Args:
            business: Business data

        Returns:
            Created company data or None
        """
        if not self.is_available():
            print("HubSpot API key not configured")
            return None

        try:
            url = "https://api.hubapi.com/crm/v3/objects/companies"

            properties = {
                'name': business.get('name'),
                'domain': self._extract_domain(business.get('website')),
                'phone': business.get('phone'),
                'website': business.get('website'),
                'city': self._extract_city(business),
                'state': self._extract_state(business),
                'country': 'United States',
                'industry': business.get('industry'),
            }

            # Add custom properties
            lead_score = business.get('lead_score', {})
            if lead_score:
                properties['lead_score'] = lead_score.get('total')
                properties['lead_grade'] = lead_score.get('grade')

            payload = {'properties': properties}

            response = self.session.post(url, json=payload, timeout=30)

            if response.status_code == 201:
                return response.json()
            else:
                print(f"Error creating company: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            print(f"Error creating company in HubSpot: {e}")
            return None

    def batch_create_companies(
        self,
        businesses: List[Dict],
        batch_size: int = 100
    ) -> Dict:
        """
        Create multiple companies in HubSpot via batch API.

        Args:
            businesses: List of businesses
            batch_size: Batch size (max 100)

        Returns:
            Results summary
        """
        if not self.is_available():
            return {'error': 'HubSpot API key not configured'}

        results = {
            'created': 0,
            'failed': 0,
            'errors': []
        }

        # Process in batches
        for i in range(0, len(businesses), batch_size):
            batch = businesses[i:i + batch_size]

            try:
                url = "https://api.hubapi.com/crm/v3/objects/companies/batch/create"

                inputs = []
                for business in batch:
                    properties = {
                        'name': business.get('name'),
                        'domain': self._extract_domain(business.get('website')),
                        'phone': business.get('phone'),
                        'website': business.get('website'),
                    }
                    inputs.append({'properties': properties})

                payload = {'inputs': inputs}

                response = self.session.post(url, json=payload, timeout=60)

                if response.status_code == 201:
                    data = response.json()
                    results['created'] += len(data.get('results', []))
                else:
                    results['failed'] += len(batch)
                    results['errors'].append({
                        'batch': i // batch_size + 1,
                        'error': response.text
                    })

            except Exception as e:
                results['failed'] += len(batch)
                results['errors'].append({
                    'batch': i // batch_size + 1,
                    'error': str(e)
                })

        return results

    def _get_primary_email(self, business: Dict) -> Optional[str]:
        """Get primary email for business."""
        emails = business.get('emails_found', [])
        if emails:
            # Return first email (highest priority)
            return emails[0].get('email')
        return None

    def _extract_domain(self, website: Optional[str]) -> Optional[str]:
        """Extract domain from website URL."""
        if not website:
            return None

        from urllib.parse import urlparse
        parsed = urlparse(website)
        domain = parsed.netloc or parsed.path
        domain = domain.replace('www.', '')
        return domain

    def _format_street_address(self, business: Dict) -> Optional[str]:
        """Format street address from full address."""
        address = business.get('formatted_address') or business.get('address')
        if not address:
            return None

        # Try to extract street address (before first comma)
        parts = address.split(',')
        if parts:
            return parts[0].strip()

        return address

    def _extract_city(self, business: Dict) -> Optional[str]:
        """Extract city from address."""
        address = business.get('formatted_address') or business.get('address')
        if not address:
            return None

        # Typically: Street, City, State ZIP
        parts = [p.strip() for p in address.split(',')]
        if len(parts) >= 2:
            return parts[-2]  # Second to last is usually city

        return None

    def _extract_state(self, business: Dict) -> Optional[str]:
        """Extract state from address."""
        address = business.get('formatted_address') or business.get('address')
        if not address:
            return None

        # Typically last part: "State ZIP"
        parts = [p.strip() for p in address.split(',')]
        if parts:
            last_part = parts[-1]
            # Extract state abbreviation (2 letters before ZIP)
            words = last_part.split()
            for word in words:
                if len(word) == 2 and word.isalpha():
                    return word.upper()

        return None

    def _extract_postal_code(self, business: Dict) -> Optional[str]:
        """Extract postal code from address."""
        address = business.get('formatted_address') or business.get('address')
        if not address:
            return None

        import re
        # Find 5-digit or 5+4 digit ZIP code
        match = re.search(r'\b\d{5}(?:-\d{4})?\b', address)
        if match:
            return match.group()

        return None

    def _format_categories(self, business: Dict) -> Optional[str]:
        """Format categories as string."""
        categories = business.get('categories', [])
        if categories:
            return ', '.join(categories[:3])  # First 3 categories
        return None

    def _get_business_type(self, business: Dict) -> str:
        """Determine business type for HubSpot."""
        franchise_data = business.get('franchise_detection', {})

        if franchise_data.get('is_franchise'):
            return 'Franchise'
        elif franchise_data.get('is_corporate'):
            return 'Corporate'
        elif franchise_data.get('is_local'):
            return 'Local Business'
        else:
            return 'Unknown'

    def _create_description(self, business: Dict) -> str:
        """Create description from business data."""
        parts = []

        # Add business info
        if business.get('industry'):
            parts.append(f"Industry: {business['industry']}")

        # Add rating info
        rating = business.get('rating')
        reviews = business.get('user_ratings_total')
        if rating and reviews:
            parts.append(f"Google: {rating}★ ({reviews} reviews)")

        # Add Yelp info
        yelp_data = business.get('yelp_data', {})
        if yelp_data.get('yelp_rating'):
            parts.append(f"Yelp: {yelp_data['yelp_rating']}★ ({yelp_data.get('yelp_review_count', 0)} reviews)")

        # Add lead score
        lead_score = business.get('lead_score', {})
        if lead_score.get('total'):
            parts.append(f"Lead Score: {lead_score['total']}/100 (Grade: {lead_score.get('grade')})")

        return ' | '.join(parts) if parts else None

    def _create_contact_row(self, business: Dict, email_info: Dict) -> Optional[Dict]:
        """
        Create a contact row for additional emails.

        Args:
            business: Business data
            email_info: Email information

        Returns:
            Contact row dictionary or None
        """
        # Only create contact if we have a person email
        if email_info.get('type') != 'person':
            return None

        # Extract name from email if available
        email = email_info.get('email', '')
        local_part = email.split('@')[0]

        # Try to parse name from email
        first_name, last_name = self._parse_name_from_email(local_part)

        row = {
            'Company name': business.get('name'),
            'First name': first_name,
            'Last name': last_name,
            'Email': email,
            'Phone number': business.get('phone'),
            'Job title': self._guess_title_from_email(local_part),
        }

        return row

    def _parse_name_from_email(self, local_part: str) -> tuple:
        """
        Try to parse first and last name from email local part.

        Args:
            local_part: Part before @ in email

        Returns:
            (first_name, last_name) tuple
        """
        # Remove numbers
        clean = ''.join([c for c in local_part if not c.isdigit()])

        # Split on common separators
        for sep in ['.', '_', '-']:
            if sep in clean:
                parts = clean.split(sep)
                if len(parts) >= 2:
                    return (parts[0].title(), parts[1].title())

        # Single word - could be first or last name
        if clean:
            return (clean.title(), '')

        return ('', '')

    def _guess_title_from_email(self, local_part: str) -> Optional[str]:
        """
        Guess job title from email address.

        Args:
            local_part: Part before @ in email

        Returns:
            Guessed title or None
        """
        local_lower = local_part.lower()

        title_mapping = {
            'owner': 'Owner',
            'ceo': 'CEO',
            'president': 'President',
            'manager': 'Manager',
            'gm': 'General Manager',
            'director': 'Director',
            'sales': 'Sales',
            'marketing': 'Marketing',
        }

        for keyword, title in title_mapping.items():
            if keyword in local_lower:
                return title

        return None

"""Franchise and corporate business detection module."""

import re
from typing import Dict, List, Optional
from urllib.parse import urlparse


class FranchiseDetector:
    """Detect if a business is a franchise/chain vs local independent."""

    # Known franchise/chain indicators
    FRANCHISE_CHAINS = {
        # Fast food
        'mcdonalds', 'burger king', 'wendys', 'subway', 'kfc', 'taco bell',
        'popeyes', 'arbys', 'sonic', 'jack in the box', 'whataburger',
        'chick-fil-a', 'chickfila', 'panera', 'chipotle', 'panda express',

        # Coffee
        'starbucks', 'dunkin', 'dunkin donuts', 'tim hortons', 'caribou coffee',

        # Pizza
        'dominos', 'pizza hut', 'papa johns', 'little caesars', 'marco',

        # Casual dining
        'applebees', 'chilis', 'olive garden', 'red lobster', 'outback',
        'buffalo wild wings', 'dennys', 'ihop', 'cracker barrel',

        # Retail
        'walmart', 'target', 'cvs', 'walgreens', 'rite aid', '7-eleven',
        '7 eleven', 'circle k', 'dollar general', 'family dollar',

        # Gas stations
        'shell', 'bp', 'exxon', 'mobil', 'chevron', 'texaco', 'sunoco',

        # Hotels
        'marriott', 'hilton', 'holiday inn', 'best western', 'comfort inn',
        'hampton inn', 'motel 6', 'super 8', 'days inn',

        # Automotive
        'autozone', 'advanced auto', 'oreilly', "o'reilly", 'napa',
        'jiffy lube', 'meineke', 'midas', 'pep boys',

        # Fitness
        'planet fitness', 'la fitness', 'anytime fitness', '24 hour fitness',
        "gold's gym", 'golds gym',

        # Services
        'great clips', 'sport clips', 'supercuts', 'fantastic sams',
        'h&r block', 'hr block', 'liberty tax',
    }

    # Corporate domain indicators
    CORPORATE_DOMAIN_PATTERNS = [
        'corporate', 'headquarters', 'hq', 'franchise', 'franchisee',
        'national', 'international', 'global', 'usa', 'america'
    ]

    def __init__(self):
        """Initialize franchise detector."""
        pass

    def detect_franchise(
        self,
        business_name: str,
        website: Optional[str] = None,
        phone: Optional[str] = None,
        address: Optional[str] = None,
        categories: Optional[List[str]] = None
    ) -> Dict:
        """
        Detect if a business is a franchise/chain or independent.

        Args:
            business_name: Name of business
            website: Website URL
            phone: Phone number
            address: Business address
            categories: Business categories

        Returns:
            Detection results dictionary
        """
        result = {
            'is_franchise': False,
            'is_corporate': False,
            'is_local': True,
            'confidence': 'low',
            'indicators': [],
            'chain_name': None,
        }

        confidence_score = 0
        indicators = []

        # Check 1: Name matching
        name_check = self._check_name_for_franchise(business_name)
        if name_check['is_franchise']:
            result['is_franchise'] = True
            result['chain_name'] = name_check['chain_name']
            confidence_score += 40
            indicators.append(f"Name matches known chain: {name_check['chain_name']}")

        # Check 2: Website analysis
        if website:
            website_check = self._analyze_website(website, business_name)
            if website_check['is_corporate']:
                result['is_corporate'] = True
                confidence_score += 30
                indicators.extend(website_check['indicators'])

            if website_check['is_franchise']:
                result['is_franchise'] = True
                confidence_score += 25
                indicators.extend(website_check['franchise_indicators'])

        # Check 3: Phone number (toll-free often indicates corporate)
        if phone:
            if self._is_toll_free_number(phone):
                result['is_corporate'] = True
                confidence_score += 15
                indicators.append("Toll-free number (likely corporate)")

        # Check 4: Multiple locations indicator
        if address:
            location_check = self._check_for_location_numbers(address, business_name)
            if location_check['has_location_number']:
                result['is_franchise'] = True
                confidence_score += 20
                indicators.append(f"Location number in name/address: {location_check['number']}")

        # Determine final classification
        result['is_local'] = not (result['is_franchise'] or result['is_corporate'])

        # Set confidence based on score
        if confidence_score >= 50:
            result['confidence'] = 'high'
        elif confidence_score >= 25:
            result['confidence'] = 'medium'
        else:
            result['confidence'] = 'low'

        result['confidence_score'] = confidence_score
        result['indicators'] = indicators

        return result

    def _check_name_for_franchise(self, business_name: str) -> Dict:
        """
        Check if business name matches known franchises.

        Args:
            business_name: Business name

        Returns:
            Match result
        """
        name_lower = business_name.lower()

        # Clean common suffixes
        name_clean = name_lower
        for suffix in [' llc', ' inc', ' corp', ' ltd', ' co']:
            name_clean = name_clean.replace(suffix, '')

        # Check against known chains
        for chain in self.FRANCHISE_CHAINS:
            if chain in name_clean:
                return {
                    'is_franchise': True,
                    'chain_name': chain.title()
                }

        # Check for numbered locations (e.g., "Store #123", "Location 5")
        if re.search(r'#\d+|location\s+\d+|store\s+\d+', name_lower):
            return {
                'is_franchise': True,
                'chain_name': 'Unknown Chain'
            }

        return {'is_franchise': False, 'chain_name': None}

    def _analyze_website(self, website: str, business_name: str) -> Dict:
        """
        Analyze website for franchise/corporate indicators.

        Args:
            website: Website URL
            business_name: Business name

        Returns:
            Analysis results
        """
        result = {
            'is_corporate': False,
            'is_franchise': False,
            'indicators': [],
            'franchise_indicators': []
        }

        parsed = urlparse(website.lower())
        domain = parsed.netloc.replace('www.', '')

        # Check 1: Corporate domain patterns
        for pattern in self.CORPORATE_DOMAIN_PATTERNS:
            if pattern in domain:
                result['is_corporate'] = True
                result['indicators'].append(f"Corporate domain pattern: {pattern}")

        # Check 2: Domain != business name (might be corporate)
        name_words = set(business_name.lower().split())
        domain_words = set(domain.replace('.', ' ').replace('-', ' ').split())

        # If domain doesn't contain business name words, might be corporate
        common_words = name_words & domain_words
        if len(name_words) > 1 and len(common_words) == 0:
            result['is_corporate'] = True
            result['indicators'].append("Domain doesn't match business name")

        # Check 3: Franchise-specific subdomains
        if 'franchise' in domain or 'franchisee' in domain:
            result['is_franchise'] = True
            result['franchise_indicators'].append("Franchise-related subdomain")

        # Check 4: Location-specific subdomain (e.g., seattle.businessname.com)
        subdomain = parsed.netloc.split('.')[0] if '.' in parsed.netloc else ''
        if subdomain and subdomain != 'www':
            # Common city/state abbreviations
            locations = ['ny', 'la', 'sf', 'seattle', 'chicago', 'boston', 'miami']
            if subdomain in locations:
                result['is_franchise'] = True
                result['franchise_indicators'].append(f"Location-based subdomain: {subdomain}")

        return result

    def _is_toll_free_number(self, phone: str) -> bool:
        """
        Check if phone number is toll-free.

        Args:
            phone: Phone number

        Returns:
            True if toll-free
        """
        # Clean phone number
        digits = ''.join(filter(str.isdigit, phone))

        # US toll-free area codes: 800, 833, 844, 855, 866, 877, 888
        if len(digits) >= 10:
            area_code = digits[-10:-7]
            return area_code in ['800', '833', '844', '855', '866', '877', '888']

        return False

    def _check_for_location_numbers(self, address: str, business_name: str) -> Dict:
        """
        Check for location numbers in address or name.

        Args:
            address: Business address
            business_name: Business name

        Returns:
            Detection result
        """
        combined = f"{business_name} {address}".lower()

        # Patterns for location numbers
        patterns = [
            r'#(\d+)',  # #123
            r'location\s+(\d+)',  # Location 5
            r'store\s+(\d+)',  # Store 42
            r'unit\s+(\d+)',  # Unit 7
            r'branch\s+(\d+)',  # Branch 3
        ]

        for pattern in patterns:
            match = re.search(pattern, combined)
            if match:
                return {
                    'has_location_number': True,
                    'number': match.group(1)
                }

        return {'has_location_number': False, 'number': None}

    def find_local_contact_hints(self, business_data: Dict) -> Dict:
        """
        Find hints for local contact information vs corporate.

        Args:
            business_data: Full business data

        Returns:
            Local contact hints
        """
        hints = {
            'has_local_phone': False,
            'has_local_email': False,
            'local_indicators': [],
            'corporate_indicators': []
        }

        # Check phone
        phone = business_data.get('phone')
        if phone and not self._is_toll_free_number(phone):
            hints['has_local_phone'] = True
            hints['local_indicators'].append("Local phone number (not toll-free)")

        # Check emails
        emails = business_data.get('emails_found', [])
        for email_info in emails:
            email = email_info.get('email', '').lower()

            # Local indicators in email
            local_terms = ['owner', 'manager', 'info', 'contact', 'hello']
            if any(term in email for term in local_terms):
                hints['has_local_email'] = True
                hints['local_indicators'].append(f"Local email pattern: {email}")

            # Corporate indicators
            corporate_terms = ['corporate', 'headquarters', 'hq', 'national']
            if any(term in email for term in corporate_terms):
                hints['corporate_indicators'].append(f"Corporate email: {email}")

        # Check address for "corporate" or "headquarters"
        address = business_data.get('formatted_address', '') or business_data.get('address', '')
        if address:
            address_lower = address.lower()
            if 'corporate' in address_lower or 'headquarters' in address_lower:
                hints['corporate_indicators'].append("Corporate/HQ in address")

        return hints

    def prioritize_local_contacts(self, business_data: Dict) -> Dict:
        """
        Reorder contact information to prioritize local over corporate.

        Args:
            business_data: Business data with contacts

        Returns:
            Business data with reordered contacts
        """
        enriched = business_data.copy()

        # Prioritize emails
        emails = enriched.get('emails_found', [])
        if emails:
            scored_emails = []

            for email_info in emails:
                email = email_info.get('email', '').lower()
                score = 0

                # Prefer person-specific over generic
                if email_info.get('type') == 'person':
                    score += 20

                # Prefer local-sounding emails
                local_terms = ['owner', 'manager', 'info', 'contact', 'hello']
                if any(term in email for term in local_terms):
                    score += 15

                # Penalize corporate emails
                corporate_terms = ['corporate', 'hq', 'headquarters', 'national']
                if any(term in email for term in corporate_terms):
                    score -= 30

                email_info['local_priority_score'] = score
                scored_emails.append(email_info)

            # Sort by score
            scored_emails.sort(key=lambda x: x.get('local_priority_score', 0), reverse=True)
            enriched['emails_found'] = scored_emails

            # Update email lists
            enriched['generic_emails'] = [
                e['email'] for e in scored_emails if e.get('type') == 'generic'
            ]
            enriched['person_emails'] = [
                e['email'] for e in scored_emails if e.get('type') == 'person'
            ]

        return enriched

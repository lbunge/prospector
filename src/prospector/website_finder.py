"""Website discovery and enrichment module."""

import re
import requests
import time
from bs4 import BeautifulSoup
from urllib.parse import urlparse, quote_plus
from typing import Optional, Dict, List
from .config import Config


class WebsiteFinder:
    """Find business websites using various methods."""

    def __init__(self):
        """Initialize the website finder."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': Config.USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })

    def find_website(
        self,
        business_name: str,
        address: Optional[str] = None,
        phone: Optional[str] = None,
        existing_website: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Find website for a business using multiple strategies.

        Args:
            business_name: Name of the business
            address: Business address
            phone: Business phone number
            existing_website: Website from Google Places (if available)

        Returns:
            Dictionary with website and confidence score
        """
        result = {
            'website': existing_website,
            'confidence': 'high' if existing_website else 'none',
            'method': 'google_places' if existing_website else None,
            'alternatives': []
        }

        # If we already have a website, return it
        if existing_website:
            return result

        # Strategy 1: Google search
        if Config.FALLBACK_WEBSITE_SEARCH:
            google_result = self._search_google(business_name, address)
            if google_result:
                result['website'] = google_result['url']
                result['confidence'] = google_result['confidence']
                result['method'] = 'google_search'
                result['alternatives'] = google_result.get('alternatives', [])
                return result

        # Strategy 2: Common domain patterns
        domain_guesses = self._guess_domain(business_name)
        for domain in domain_guesses:
            if self._verify_website(domain):
                result['website'] = domain
                result['confidence'] = 'medium'
                result['method'] = 'domain_guess'
                return result

        return result

    def _search_google(
        self,
        business_name: str,
        address: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Search Google for business website.

        Args:
            business_name: Name of the business
            address: Business address for context

        Returns:
            Dictionary with URL and confidence, or None
        """
        try:
            # Build search query
            query = f"{business_name}"
            if address:
                # Extract city/state from address
                parts = address.split(',')
                if len(parts) >= 2:
                    query += f" {parts[-2].strip()}"  # City

            query += " official website"

            # Google search URL
            search_url = f"https://www.google.com/search?q={quote_plus(query)}"

            response = self.session.get(
                search_url,
                timeout=Config.REQUEST_TIMEOUT
            )

            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find search results
            # Google's HTML structure changes, so try multiple selectors
            links = []

            # Try different result selectors
            for selector in ['div.g a', 'div[data-sokoban-container] a', 'a[href^="http"]']:
                elements = soup.select(selector)
                if elements:
                    links.extend(elements)
                    break

            alternatives = []
            main_result = None

            for link in links[:10]:  # Check first 10 results
                href = link.get('href', '')

                # Skip Google's own links
                if any(skip in href for skip in ['google.com', 'youtube.com', 'facebook.com',
                                                   'instagram.com', 'twitter.com', 'linkedin.com',
                                                   'yelp.com', 'yellowpages.com']):
                    continue

                # Extract actual URL
                if href.startswith('http'):
                    # Clean URL (remove Google tracking)
                    clean_url = self._clean_url(href)

                    if clean_url and self._is_valid_business_url(clean_url):
                        if not main_result:
                            main_result = clean_url
                        else:
                            alternatives.append(clean_url)

                if main_result and len(alternatives) >= 2:
                    break

            if main_result:
                return {
                    'url': main_result,
                    'confidence': 'high',
                    'alternatives': alternatives
                }

        except Exception as e:
            print(f"    Warning: Google search failed: {e}")

        return None

    def _clean_url(self, url: str) -> Optional[str]:
        """
        Clean and normalize a URL.

        Args:
            url: Raw URL

        Returns:
            Cleaned URL or None
        """
        try:
            # Remove Google redirect
            if '/url?q=' in url:
                url = url.split('/url?q=')[1].split('&')[0]

            # Parse URL
            parsed = urlparse(url)

            # Rebuild clean URL
            if parsed.netloc:
                scheme = parsed.scheme or 'https'
                return f"{scheme}://{parsed.netloc}{parsed.path}"

        except:
            pass

        return None

    def _is_valid_business_url(self, url: str) -> bool:
        """
        Check if URL looks like a legitimate business website.

        Args:
            url: URL to check

        Returns:
            True if likely a business website
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Skip common non-business sites
            skip_domains = [
                'google.', 'facebook.', 'twitter.', 'instagram.', 'linkedin.',
                'youtube.', 'yelp.', 'yellowpages.', 'wikipedia.', 'amazon.',
                'ebay.', 'craigslist.', 'reddit.', 'pinterest.'
            ]

            for skip in skip_domains:
                if skip in domain:
                    return False

            # Must have a TLD
            if '.' not in domain:
                return False

            return True

        except:
            return False

    def _guess_domain(self, business_name: str) -> List[str]:
        """
        Generate possible domain names for a business.

        Args:
            business_name: Name of the business

        Returns:
            List of possible domain names
        """
        # Clean business name
        clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', business_name.lower())
        clean_name = clean_name.strip()

        domains = []

        # Remove common business suffixes
        suffixes = [' llc', ' inc', ' corp', ' company', ' co', ' ltd', ' limited']
        for suffix in suffixes:
            if clean_name.endswith(suffix):
                clean_name = clean_name[:-len(suffix)].strip()

        # Generate variations
        # 1. Full name no spaces
        no_spaces = clean_name.replace(' ', '')
        if no_spaces:
            domains.extend([
                f"https://www.{no_spaces}.com",
                f"https://{no_spaces}.com",
                f"https://www.{no_spaces}.net",
                f"https://www.{no_spaces}.org",
            ])

        # 2. Full name with hyphens
        with_hyphens = clean_name.replace(' ', '-')
        if with_hyphens and '-' in with_hyphens:
            domains.extend([
                f"https://www.{with_hyphens}.com",
                f"https://{with_hyphens}.com",
            ])

        # 3. Acronym (if multiple words)
        words = clean_name.split()
        if len(words) > 1:
            acronym = ''.join([w[0] for w in words if w])
            if acronym:
                domains.extend([
                    f"https://www.{acronym}.com",
                    f"https://{acronym}.com",
                ])

        return domains

    def _verify_website(self, url: str, timeout: int = 5) -> bool:
        """
        Verify that a website exists and is accessible.

        Args:
            url: URL to verify
            timeout: Request timeout in seconds

        Returns:
            True if website is accessible
        """
        try:
            response = self.session.head(
                url,
                timeout=timeout,
                allow_redirects=True
            )
            return response.status_code < 400

        except:
            return False

    def enrich_from_social_media(
        self,
        social_media: Dict[str, str]
    ) -> Optional[str]:
        """
        Try to find website from social media profiles.

        Args:
            social_media: Dictionary of social media URLs

        Returns:
            Website URL if found, else None
        """
        if not Config.SEARCH_SOCIAL_FOR_WEBSITE:
            return None

        # Try Facebook first (often has website link)
        if 'facebook' in social_media:
            try:
                website = self._extract_website_from_facebook(social_media['facebook'])
                if website:
                    return website
            except Exception as e:
                print(f"    Warning: Error extracting from Facebook: {e}")

        # Try LinkedIn
        if 'linkedin' in social_media:
            try:
                website = self._extract_website_from_linkedin(social_media['linkedin'])
                if website:
                    return website
            except Exception as e:
                print(f"    Warning: Error extracting from LinkedIn: {e}")

        return None

    def _extract_website_from_facebook(self, facebook_url: str) -> Optional[str]:
        """
        Extract website from Facebook business page.

        Args:
            facebook_url: Facebook page URL

        Returns:
            Website URL if found
        """
        try:
            response = self.session.get(
                facebook_url,
                timeout=Config.REQUEST_TIMEOUT
            )

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Look for website links
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if 'facebook.com' not in href and self._is_valid_business_url(href):
                        clean_url = self._clean_url(href)
                        if clean_url:
                            return clean_url

        except:
            pass

        return None

    def _extract_website_from_linkedin(self, linkedin_url: str) -> Optional[str]:
        """
        Extract website from LinkedIn company page.

        Args:
            linkedin_url: LinkedIn page URL

        Returns:
            Website URL if found
        """
        try:
            response = self.session.get(
                linkedin_url,
                timeout=Config.REQUEST_TIMEOUT
            )

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Look for website in the about section
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if 'linkedin.com' not in href and self._is_valid_business_url(href):
                        clean_url = self._clean_url(href)
                        if clean_url:
                            return clean_url

        except:
            pass

        return None

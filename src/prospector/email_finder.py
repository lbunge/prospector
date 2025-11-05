"""Email finding and website scraping functionality."""

import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Set, Optional
from email_validator import validate_email, EmailNotValidError
from .config import Config


class EmailFinder:
    """Find email addresses from business websites."""

    # Common email patterns
    EMAIL_PATTERN = re.compile(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    )

    # Common contact page patterns
    CONTACT_PAGE_PATTERNS = [
        'contact', 'contact-us', 'contactus', 'about', 'about-us',
        'team', 'staff', 'connect', 'reach', 'get-in-touch'
    ]

    def __init__(self):
        """Initialize the email finder."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': Config.USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })

    def find_emails_from_website(
        self,
        website_url: str,
        max_pages: int = None
    ) -> Dict[str, any]:
        """
        Find email addresses from a business website.

        Args:
            website_url: The website URL to scrape
            max_pages: Maximum number of pages to crawl (default from config)

        Returns:
            Dictionary containing:
                - emails: List of found email dictionaries
                - pages_crawled: Number of pages crawled
                - status: Success or error status
        """
        if max_pages is None:
            max_pages = Config.MAX_PAGES_PER_WEBSITE

        result = {
            'emails': [],
            'pages_crawled': 0,
            'status': 'success',
            'error': None
        }

        try:
            # Normalize URL
            if not website_url.startswith(('http://', 'https://')):
                website_url = 'https://' + website_url

            # Get pages to crawl
            pages_to_crawl = self._get_pages_to_crawl(website_url, max_pages)

            # Find emails from each page
            all_emails = set()
            email_sources = {}

            for page_url in pages_to_crawl:
                try:
                    page_emails = self._extract_emails_from_page(page_url)
                    for email in page_emails:
                        all_emails.add(email.lower())
                        if email.lower() not in email_sources:
                            email_sources[email.lower()] = page_url

                    result['pages_crawled'] += 1

                except Exception as e:
                    print(f"  Warning: Error crawling {page_url}: {e}")
                    continue

            # Classify and validate emails
            for email in all_emails:
                email_info = self._classify_email(email, email_sources.get(email))
                if email_info:
                    result['emails'].append(email_info)

            # Sort emails by type (generic first, then person-specific)
            result['emails'].sort(key=lambda x: (x['type'] != 'generic', x['email']))

        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)

        return result

    def _get_pages_to_crawl(self, website_url: str, max_pages: int) -> List[str]:
        """
        Get list of pages to crawl, prioritizing contact pages.

        Args:
            website_url: Base website URL
            max_pages: Maximum pages to return

        Returns:
            List of URLs to crawl
        """
        pages = [website_url]  # Always crawl homepage first

        try:
            # Get homepage to find contact pages
            response = self.session.get(
                website_url,
                timeout=Config.REQUEST_TIMEOUT,
                allow_redirects=True
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            base_domain = urlparse(website_url).netloc

            # Find all links
            links = soup.find_all('a', href=True)

            # Look for contact pages
            contact_pages = []
            for link in links:
                href = link['href']
                full_url = urljoin(website_url, href)

                # Only include links from same domain
                if urlparse(full_url).netloc != base_domain:
                    continue

                # Check if it's a contact-related page
                href_lower = href.lower()
                if any(pattern in href_lower for pattern in self.CONTACT_PAGE_PATTERNS):
                    if full_url not in pages and full_url not in contact_pages:
                        contact_pages.append(full_url)

            # Add contact pages (prioritized)
            pages.extend(contact_pages[:max_pages - 1])

        except Exception as e:
            print(f"  Warning: Error finding contact pages: {e}")

        return pages[:max_pages]

    def _extract_emails_from_page(self, url: str) -> Set[str]:
        """
        Extract email addresses from a single page.

        Args:
            url: Page URL

        Returns:
            Set of email addresses found
        """
        emails = set()

        try:
            response = self.session.get(
                url,
                timeout=Config.REQUEST_TIMEOUT,
                allow_redirects=True
            )
            response.raise_for_status()

            # Find emails in HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Remove script and style elements
            for script in soup(['script', 'style']):
                script.decompose()

            # Get text content
            text = soup.get_text()

            # Also check mailto links
            mailto_links = soup.find_all('a', href=re.compile(r'^mailto:', re.I))
            for link in mailto_links:
                email = link['href'].replace('mailto:', '').split('?')[0]
                emails.add(email)

            # Find emails using regex
            found_emails = self.EMAIL_PATTERN.findall(text)
            emails.update(found_emails)

        except Exception as e:
            print(f"  Warning: Error extracting emails from {url}: {e}")

        return emails

    def _classify_email(self, email: str, source_url: Optional[str] = None) -> Optional[Dict]:
        """
        Classify and validate an email address.

        Args:
            email: Email address to classify
            source_url: URL where email was found

        Returns:
            Dictionary with email info, or None if invalid
        """
        # Validate email
        try:
            validation = validate_email(email, check_deliverability=False)
            email = validation.normalized
        except EmailNotValidError:
            return None

        # Classify email type
        local_part = email.split('@')[0].lower()

        # Generic email patterns
        generic_patterns = [
            'info', 'contact', 'hello', 'support', 'sales', 'inquiries',
            'inquiry', 'admin', 'office', 'help', 'service', 'mail',
            'customer', 'team', 'general', 'reception'
        ]

        # Check if generic
        is_generic = any(pattern in local_part for pattern in generic_patterns)

        # Common non-business email domains to filter out
        common_domains = [
            'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
            'aol.com', 'icloud.com', 'live.com', 'msn.com'
        ]

        domain = email.split('@')[1].lower()
        is_personal = domain in common_domains

        email_type = 'generic' if is_generic else 'person'

        return {
            'email': email,
            'type': email_type,
            'is_personal': is_personal,
            'source_url': source_url,
            'local_part': local_part,
            'domain': domain
        }

    def find_social_media(self, website_url: str) -> Dict[str, str]:
        """
        Find social media links from a website.

        Args:
            website_url: The website URL

        Returns:
            Dictionary of social media platform: URL
        """
        social_media = {}

        try:
            if not website_url.startswith(('http://', 'https://')):
                website_url = 'https://' + website_url

            response = self.session.get(
                website_url,
                timeout=Config.REQUEST_TIMEOUT,
                allow_redirects=True
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Common social media patterns
            social_patterns = {
                'facebook': r'facebook\.com',
                'linkedin': r'linkedin\.com',
                'twitter': r'twitter\.com|x\.com',
                'instagram': r'instagram\.com',
                'youtube': r'youtube\.com',
            }

            links = soup.find_all('a', href=True)
            for link in links:
                href = link['href'].lower()
                for platform, pattern in social_patterns.items():
                    if re.search(pattern, href) and platform not in social_media:
                        social_media[platform] = link['href']

        except Exception as e:
            print(f"  Warning: Error finding social media: {e}")

        return social_media

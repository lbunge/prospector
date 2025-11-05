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

    # Common contact page patterns (expanded)
    CONTACT_PAGE_PATTERNS = [
        'contact', 'contact-us', 'contactus', 'about', 'about-us',
        'team', 'staff', 'connect', 'reach', 'get-in-touch',
        'locations', 'find-us', 'visit', 'office', 'headquarters',
        'support', 'help', 'customer-service', 'inquiry', 'sales',
        'leadership', 'management', 'people', 'our-team', 'meet-the-team'
    ]

    # Additional email patterns for obfuscated emails
    OBFUSCATED_PATTERNS = [
        re.compile(r'([a-zA-Z0-9._%+-]+)\s*\[at\]\s*([a-zA-Z0-9.-]+)\s*\[dot\]\s*([a-zA-Z]{2,})'),
        re.compile(r'([a-zA-Z0-9._%+-]+)\s*@\s*([a-zA-Z0-9.-]+)\s*\.\s*([a-zA-Z]{2,})'),
        re.compile(r'([a-zA-Z0-9._%+-]+)\s*\(at\)\s*([a-zA-Z0-9.-]+)\s*\(dot\)\s*([a-zA-Z]{2,})'),
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
        Get list of pages to crawl, prioritizing contact pages with depth-based search.

        Args:
            website_url: Base website URL
            max_pages: Maximum pages to return

        Returns:
            List of URLs to crawl
        """
        pages_to_visit = [website_url]  # Always crawl homepage first
        visited = set()
        contact_pages = []
        other_pages = []

        base_domain = urlparse(website_url).netloc
        max_depth = Config.MAX_DEPTH_PER_WEBSITE

        for depth in range(max_depth):
            if len(pages_to_visit) == 0:
                break

            current_level = pages_to_visit[:max_pages * 2]  # Limit per level
            pages_to_visit = []

            for page_url in current_level:
                if page_url in visited:
                    continue

                if len(visited) >= max_pages * 3:  # Stop if we've looked at too many
                    break

                try:
                    visited.add(page_url)

                    response = self.session.get(
                        page_url,
                        timeout=Config.REQUEST_TIMEOUT,
                        allow_redirects=True
                    )
                    response.raise_for_status()

                    soup = BeautifulSoup(response.text, 'html.parser')

                    # Find all links
                    links = soup.find_all('a', href=True)

                    for link in links:
                        href = link['href']
                        full_url = urljoin(page_url, href)

                        # Clean URL (remove fragments and query params for deduplication)
                        parsed = urlparse(full_url)
                        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

                        # Only include links from same domain
                        if urlparse(clean_url).netloc != base_domain:
                            continue

                        # Skip already visited
                        if clean_url in visited:
                            continue

                        # Skip non-HTML links
                        if any(ext in clean_url.lower() for ext in ['.pdf', '.jpg', '.png', '.gif', '.zip', '.doc']):
                            continue

                        # Check if it's a contact-related page
                        href_lower = full_url.lower()
                        is_contact = any(pattern in href_lower for pattern in self.CONTACT_PAGE_PATTERNS)

                        if is_contact and clean_url not in contact_pages:
                            contact_pages.append(clean_url)
                        elif depth < max_depth - 1 and clean_url not in other_pages:
                            # Add for next level crawling
                            pages_to_visit.append(clean_url)
                            other_pages.append(clean_url)

                except Exception as e:
                    # Silently continue on errors during page discovery
                    continue

        # Prioritize: homepage + contact pages + other pages
        result_pages = [website_url]
        result_pages.extend(contact_pages[:max_pages - 1])

        # Fill remaining slots with other pages if needed
        remaining_slots = max_pages - len(result_pages)
        if remaining_slots > 0:
            result_pages.extend(other_pages[:remaining_slots])

        return result_pages[:max_pages]

    def _extract_emails_from_page(self, url: str) -> Set[str]:
        """
        Extract email addresses from a single page with enhanced detection.

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

            # 1. Check mailto links (highest priority)
            mailto_links = soup.find_all('a', href=re.compile(r'^mailto:', re.I))
            for link in mailto_links:
                email = link['href'].replace('mailto:', '').split('?')[0].strip()
                if email:
                    emails.add(email.lower())

            # 2. Check data attributes (sometimes emails are hidden in data-* attributes)
            for tag in soup.find_all(attrs={'data-email': True}):
                email = tag.get('data-email', '').strip()
                if email:
                    emails.add(email.lower())

            # 3. Check for cloudflare email protection
            cloudflare_emails = soup.find_all('a', class_=re.compile(r'__cf_email__'))
            for email_tag in cloudflare_emails:
                # Cloudflare obfuscates emails, but the link text might contain it
                if email_tag.get('data-cfemail'):
                    # Would need to decode, skip for now
                    pass

            # 4. Get text content
            # Remove script and style elements
            for script in soup(['script', 'style']):
                script.decompose()

            text = soup.get_text()

            # Also check HTML source for hidden emails
            html_source = response.text

            # 5. Find regular emails using regex
            found_emails = self.EMAIL_PATTERN.findall(text)
            emails.update([e.lower() for e in found_emails])

            # Also search in HTML source
            source_emails = self.EMAIL_PATTERN.findall(html_source)
            emails.update([e.lower() for e in source_emails])

            # 6. Find obfuscated emails (e.g., "name [at] domain [dot] com")
            for pattern in self.OBFUSCATED_PATTERNS:
                matches = pattern.findall(text)
                for match in matches:
                    if len(match) == 3:
                        # Reconstruct email
                        email = f"{match[0]}@{match[1]}.{match[2]}"
                        emails.add(email.lower())

            # 7. Look for emails in JavaScript variables
            js_pattern = re.compile(r'["\']([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})["\']')
            js_emails = js_pattern.findall(html_source)
            emails.update([e.lower() for e in js_emails])

            # 8. Filter out common false positives
            emails = {e for e in emails if self._is_likely_real_email(e)}

        except Exception as e:
            # Silently fail for individual page errors
            pass

        return emails

    def _is_likely_real_email(self, email: str) -> bool:
        """
        Check if an email looks like a real business email (not a false positive).

        Args:
            email: Email address to check

        Returns:
            True if likely real
        """
        email_lower = email.lower()

        # Filter out common false positives
        false_positives = [
            'example@example.com',
            'email@example.com',
            'your@email.com',
            'name@example.com',
            'user@example.com',
            'test@test.com',
            'admin@localhost',
            'noreply@',
            'no-reply@',
            '@example.',
            '@test.',
            '@localhost',
        ]

        for fp in false_positives:
            if fp in email_lower:
                return False

        # Must have proper structure
        if '@' not in email or '.' not in email.split('@')[1]:
            return False

        return True

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

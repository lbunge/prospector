"""Email validation, permutation, and enrichment module."""

import re
import requests
import dns.resolver
from typing import List, Dict, Optional, Set
from email_validator import validate_email, EmailNotValidError
from .config import Config


class EmailValidator:
    """Validate, verify, and permute business emails."""

    def __init__(self):
        """Initialize email validator."""
        self.session = requests.Session()
        self.hunter_api_key = Config.HUNTER_API_KEY
        self.zerobounce_api_key = Config.ZEROBOUNCE_API_KEY

    def is_hunter_available(self) -> bool:
        """Check if Hunter.io API is available."""
        return bool(self.hunter_api_key)

    def is_zerobounce_available(self) -> bool:
        """Check if ZeroBounce API is available."""
        return bool(self.zerobounce_api_key)

    def find_emails_hunter(
        self,
        domain: str,
        company_name: Optional[str] = None
    ) -> Dict:
        """
        Find emails for a domain using Hunter.io.

        Args:
            domain: Company domain
            company_name: Company name (optional)

        Returns:
            Dictionary with found emails and pattern
        """
        if not self.is_hunter_available():
            return {'emails': [], 'pattern': None, 'confidence': 0}

        try:
            url = "https://api.hunter.io/v2/domain-search"
            params = {
                'domain': domain,
                'api_key': self.hunter_api_key,
                'limit': 10
            }

            if company_name:
                params['company'] = company_name

            response = self.session.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json().get('data', {})

                emails = []
                for email_data in data.get('emails', []):
                    emails.append({
                        'email': email_data.get('value'),
                        'type': email_data.get('type'),
                        'confidence': email_data.get('confidence'),
                        'first_name': email_data.get('first_name'),
                        'last_name': email_data.get('last_name'),
                        'position': email_data.get('position'),
                        'department': email_data.get('department'),
                        'seniority': email_data.get('seniority'),
                        'source': 'hunter.io'
                    })

                return {
                    'emails': emails,
                    'pattern': data.get('pattern'),
                    'organization': data.get('organization'),
                    'confidence': data.get('confidence', 0)
                }

        except Exception as e:
            print(f"    Warning: Hunter.io search failed: {e}")

        return {'emails': [], 'pattern': None, 'confidence': 0}

    def verify_email_hunter(self, email: str) -> Dict:
        """
        Verify email deliverability using Hunter.io.

        Args:
            email: Email address to verify

        Returns:
            Verification results
        """
        if not self.is_hunter_available():
            return {'status': 'unknown', 'score': 0}

        try:
            url = "https://api.hunter.io/v2/email-verifier"
            params = {
                'email': email,
                'api_key': self.hunter_api_key
            }

            response = self.session.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json().get('data', {})
                return {
                    'status': data.get('status'),  # valid, invalid, accept_all, unknown
                    'score': data.get('score', 0),  # 0-100
                    'result': data.get('result'),  # deliverable, undeliverable, risky, unknown
                    'smtp_check': data.get('smtp_check'),
                    'smtp_server': data.get('smtp_server'),
                    'mx_records': data.get('mx_records'),
                    'source': 'hunter.io'
                }

        except Exception:
            pass

        return {'status': 'unknown', 'score': 0}

    def verify_email_zerobounce(self, email: str) -> Dict:
        """
        Verify email using ZeroBounce.

        Args:
            email: Email to verify

        Returns:
            Verification results
        """
        if not self.is_zerobounce_available():
            return {'status': 'unknown', 'sub_status': None}

        try:
            url = "https://api.zerobounce.net/v2/validate"
            params = {
                'api_key': self.zerobounce_api_key,
                'email': email
            }

            response = self.session.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                return {
                    'status': data.get('status'),  # valid, invalid, catch-all, unknown, spamtrap, abuse, do_not_mail
                    'sub_status': data.get('sub_status'),
                    'account': data.get('account'),
                    'domain': data.get('domain'),
                    'smtp_provider': data.get('smtp_provider'),
                    'mx_found': data.get('mx_found'),
                    'mx_record': data.get('mx_record'),
                    'firstname': data.get('firstname'),
                    'lastname': data.get('lastname'),
                    'gender': data.get('gender'),
                    'source': 'zerobounce'
                }

        except Exception:
            pass

        return {'status': 'unknown', 'sub_status': None}

    def verify_email_basic(self, email: str) -> Dict:
        """
        Basic email verification (syntax + MX record check).

        Args:
            email: Email to verify

        Returns:
            Verification results
        """
        result = {
            'email': email,
            'valid_syntax': False,
            'has_mx_record': False,
            'domain': None,
            'deliverable': False,
            'score': 0
        }

        try:
            # Validate syntax
            validation = validate_email(email, check_deliverability=False)
            email_normalized = validation.normalized
            result['email'] = email_normalized
            result['valid_syntax'] = True
            result['domain'] = validation.domain

            # Check MX records
            try:
                mx_records = dns.resolver.resolve(result['domain'], 'MX')
                if mx_records:
                    result['has_mx_record'] = True
                    result['mx_servers'] = [str(mx.exchange) for mx in mx_records]

                    # If syntax valid and MX exists, likely deliverable
                    result['deliverable'] = True
                    result['score'] = 70  # Basic confidence

            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.Timeout):
                result['has_mx_record'] = False
                result['deliverable'] = False
                result['score'] = 20

        except EmailNotValidError:
            result['valid_syntax'] = False
            result['deliverable'] = False

        return result

    def generate_email_permutations(
        self,
        first_name: Optional[str],
        last_name: Optional[str],
        domain: str,
        pattern: Optional[str] = None
    ) -> List[str]:
        """
        Generate possible email permutations for a person.

        Args:
            first_name: Person's first name
            last_name: Person's last name
            domain: Company domain
            pattern: Known email pattern (e.g., "{first}.{last}@domain.com")

        Returns:
            List of possible email addresses
        """
        emails = []

        if not first_name or not last_name:
            return emails

        # Clean names
        first = first_name.lower().strip()
        last = last_name.lower().strip()
        f_initial = first[0] if first else ''
        l_initial = last[0] if last else ''

        # Common patterns
        patterns = [
            f"{first}.{last}@{domain}",  # john.smith@
            f"{first}{last}@{domain}",  # johnsmith@
            f"{f_initial}{last}@{domain}",  # jsmith@
            f"{first}_{last}@{domain}",  # john_smith@
            f"{first}-{last}@{domain}",  # john-smith@
            f"{first}@{domain}",  # john@
            f"{last}@{domain}",  # smith@
            f"{first}{l_initial}@{domain}",  # johns@
            f"{f_initial}.{last}@{domain}",  # j.smith@
            f"{last}.{first}@{domain}",  # smith.john@
            f"{last}{first}@{domain}",  # smithjohn@
            f"{l_initial}{first}@{domain}",  # sjohn@
        ]

        # If we have a known pattern, prioritize it
        if pattern:
            priority_email = self._apply_pattern(pattern, first, last, domain)
            if priority_email:
                emails.append(priority_email)

        # Add all other patterns
        for email in patterns:
            if email not in emails:
                emails.append(email)

        return emails

    def _apply_pattern(
        self,
        pattern: str,
        first_name: str,
        last_name: str,
        domain: str
    ) -> Optional[str]:
        """
        Apply an email pattern template.

        Args:
            pattern: Pattern like "{first}.{last}@{domain}"
            first_name: First name
            last_name: Last name
            domain: Domain

        Returns:
            Email address or None
        """
        try:
            # Replace placeholders
            email = pattern
            email = email.replace('{first}', first_name.lower())
            email = email.replace('{last}', last_name.lower())
            email = email.replace('{f}', first_name[0].lower() if first_name else '')
            email = email.replace('{l}', last_name[0].lower() if last_name else '')
            email = email.replace('{domain}', domain)

            if '@' in email and '.' in email:
                return email

        except Exception:
            pass

        return None

    def find_decision_maker_emails(
        self,
        business_name: str,
        domain: str,
        location: Optional[str] = None
    ) -> List[Dict]:
        """
        Find emails of decision makers (owner, manager, etc.).

        Args:
            business_name: Name of business
            domain: Business domain
            location: Business location

        Returns:
            List of found emails with role information
        """
        emails = []

        # Common decision maker roles
        roles = [
            'owner', 'co-owner',
            'manager', 'general-manager', 'gm',
            'director', 'president', 'ceo',
            'contact', 'info', 'hello', 'sales'
        ]

        for role in roles:
            # Generate role-based emails
            role_emails = [
                f"{role}@{domain}",
                f"{role}.{location}@{domain}" if location else None,
            ]

            for email in role_emails:
                if email and self._is_valid_email_format(email):
                    emails.append({
                        'email': email,
                        'type': 'role-based',
                        'role': role,
                        'confidence': 'medium',
                        'source': 'generated'
                    })

        return emails

    def _is_valid_email_format(self, email: str) -> bool:
        """
        Quick check if email has valid format.

        Args:
            email: Email to check

        Returns:
            True if format is valid
        """
        try:
            validate_email(email, check_deliverability=False)
            return True
        except:
            return False

    def batch_verify_emails(
        self,
        emails: List[str],
        method: str = 'basic'
    ) -> List[Dict]:
        """
        Verify multiple emails.

        Args:
            emails: List of emails to verify
            method: 'basic', 'hunter', or 'zerobounce'

        Returns:
            List of verification results
        """
        results = []

        for email in emails:
            if method == 'hunter' and self.is_hunter_available():
                result = self.verify_email_hunter(email)
            elif method == 'zerobounce' and self.is_zerobounce_available():
                result = self.verify_email_zerobounce(email)
            else:
                result = self.verify_email_basic(email)

            result['email'] = email
            results.append(result)

        return results

    def enrich_emails_with_validation(
        self,
        emails: List[Dict],
        validate: bool = True
    ) -> List[Dict]:
        """
        Enrich email list with validation data.

        Args:
            emails: List of email dictionaries
            validate: Whether to validate

        Returns:
            Enriched email list
        """
        if not validate or not emails:
            return emails

        enriched = []

        for email_info in emails:
            email = email_info.get('email')
            if not email:
                continue

            # Start with existing info
            enriched_info = email_info.copy()

            # Try ZeroBounce first (more detailed)
            if Config.USE_ZEROBOUNCE_API and self.is_zerobounce_available():
                validation = self.verify_email_zerobounce(email)
                enriched_info['validation'] = validation

            # Fallback to Hunter
            elif Config.USE_HUNTER_API and self.is_hunter_available():
                validation = self.verify_email_hunter(email)
                enriched_info['validation'] = validation

            # Fallback to basic
            else:
                validation = self.verify_email_basic(email)
                enriched_info['validation'] = validation

            # Add deliverability flag
            status = validation.get('status', 'unknown')
            enriched_info['is_deliverable'] = status in ['valid', 'deliverable', 'accept_all']
            enriched_info['validation_score'] = validation.get('score', 0)

            enriched.append(enriched_info)

        # Sort by validation score (highest first)
        enriched.sort(key=lambda x: x.get('validation_score', 0), reverse=True)

        return enriched

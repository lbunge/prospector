"""Phone number validation and enrichment module."""

import re
import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberType
from typing import Dict, Optional


class PhoneValidator:
    """Validate and enrich phone numbers."""

    def __init__(self):
        """Initialize phone validator."""
        pass

    def validate_and_format(
        self,
        phone: str,
        country_code: str = 'US'
    ) -> Dict:
        """
        Validate and format a phone number.

        Args:
            phone: Phone number string
            country_code: Country code (default US)

        Returns:
            Dictionary with formatted phone and metadata
        """
        result = {
            'original': phone,
            'valid': False,
            'formatted_national': None,
            'formatted_international': None,
            'formatted_e164': None,
            'type': None,
            'carrier': None,
            'is_mobile': False,
            'is_toll_free': False,
            'country_code': None,
            'national_number': None,
        }

        if not phone:
            return result

        try:
            # Parse phone number
            parsed = phonenumbers.parse(phone, country_code)

            # Validate
            if phonenumbers.is_valid_number(parsed):
                result['valid'] = True

                # Format in different ways
                result['formatted_national'] = phonenumbers.format_number(
                    parsed,
                    phonenumbers.PhoneNumberFormat.NATIONAL
                )
                result['formatted_international'] = phonenumbers.format_number(
                    parsed,
                    phonenumbers.PhoneNumberFormat.INTERNATIONAL
                )
                result['formatted_e164'] = phonenumbers.format_number(
                    parsed,
                    phonenumbers.PhoneNumberFormat.E164
                )

                # Get number type
                number_type = phonenumbers.number_type(parsed)
                result['type'] = self._get_type_name(number_type)
                result['is_mobile'] = number_type == PhoneNumberType.MOBILE
                result['is_toll_free'] = number_type == PhoneNumberType.TOLL_FREE

                # Extract components
                result['country_code'] = parsed.country_code
                result['national_number'] = parsed.national_number

                # Try to get carrier (may not work for all numbers)
                try:
                    from phonenumbers import carrier
                    carrier_name = carrier.name_for_number(parsed, 'en')
                    if carrier_name:
                        result['carrier'] = carrier_name
                except:
                    pass

                # Try to get timezone
                try:
                    from phonenumbers import timezone
                    timezones = timezone.time_zones_for_number(parsed)
                    if timezones:
                        result['timezone'] = list(timezones)[0]
                except:
                    pass

                # Try to get geocoding
                try:
                    from phonenumbers import geocoder
                    location = geocoder.description_for_number(parsed, 'en')
                    if location:
                        result['location'] = location
                except:
                    pass

        except NumberParseException as e:
            result['error'] = str(e)

        return result

    def _get_type_name(self, number_type: PhoneNumberType) -> str:
        """
        Get human-readable name for phone number type.

        Args:
            number_type: PhoneNumberType enum

        Returns:
            Type name string
        """
        type_names = {
            PhoneNumberType.FIXED_LINE: 'landline',
            PhoneNumberType.MOBILE: 'mobile',
            PhoneNumberType.FIXED_LINE_OR_MOBILE: 'landline_or_mobile',
            PhoneNumberType.TOLL_FREE: 'toll_free',
            PhoneNumberType.PREMIUM_RATE: 'premium_rate',
            PhoneNumberType.SHARED_COST: 'shared_cost',
            PhoneNumberType.VOIP: 'voip',
            PhoneNumberType.PERSONAL_NUMBER: 'personal',
            PhoneNumberType.PAGER: 'pager',
            PhoneNumberType.UAN: 'uan',
            PhoneNumberType.VOICEMAIL: 'voicemail',
            PhoneNumberType.UNKNOWN: 'unknown',
        }
        return type_names.get(number_type, 'unknown')

    def is_local_number(
        self,
        phone: str,
        target_area_code: str,
        country_code: str = 'US'
    ) -> bool:
        """
        Check if a phone number is local to a specific area code.

        Args:
            phone: Phone number
            target_area_code: Area code to check (e.g., "206")
            country_code: Country code

        Returns:
            True if local
        """
        try:
            parsed = phonenumbers.parse(phone, country_code)
            if phonenumbers.is_valid_number(parsed):
                national = str(parsed.national_number)
                # For US numbers, area code is first 3 digits of national number
                if len(national) == 10:
                    area_code = national[:3]
                    return area_code == target_area_code.lstrip('0')
        except:
            pass

        return False

    def extract_area_code(
        self,
        phone: str,
        country_code: str = 'US'
    ) -> Optional[str]:
        """
        Extract area code from phone number.

        Args:
            phone: Phone number
            country_code: Country code

        Returns:
            Area code or None
        """
        try:
            parsed = phonenumbers.parse(phone, country_code)
            if phonenumbers.is_valid_number(parsed):
                national = str(parsed.national_number)
                if len(national) == 10:  # US number
                    return national[:3]
        except:
            pass

        return None

    def is_likely_corporate(self, phone: str) -> bool:
        """
        Determine if a phone number is likely corporate (toll-free).

        Args:
            phone: Phone number

        Returns:
            True if likely corporate
        """
        validation = self.validate_and_format(phone)
        return validation.get('is_toll_free', False)

    def prioritize_local_phone(
        self,
        phones: list,
        target_location: Optional[str] = None
    ) -> list:
        """
        Sort phone numbers prioritizing local numbers.

        Args:
            phones: List of phone dictionaries
            target_location: Target location for local detection

        Returns:
            Sorted list (local first)
        """
        if not phones:
            return []

        # Extract area code from target location if needed
        target_area_code = None
        if target_location:
            # Try to extract area code from location string
            # This is a simple approach - could be enhanced
            pass

        scored_phones = []
        for phone_info in phones:
            phone = phone_info.get('phone') or phone_info.get('number')
            if not phone:
                continue

            validation = self.validate_and_format(phone)
            score = 0

            if validation.get('valid'):
                score += 10

                # Prefer landline for business
                if validation.get('type') == 'landline':
                    score += 20
                elif validation.get('type') == 'mobile':
                    score += 5

                # Deprioritize toll-free (likely corporate)
                if validation.get('is_toll_free'):
                    score -= 15

            phone_info['validation'] = validation
            phone_info['priority_score'] = score
            scored_phones.append(phone_info)

        # Sort by score (highest first)
        scored_phones.sort(key=lambda x: x.get('priority_score', 0), reverse=True)

        return scored_phones

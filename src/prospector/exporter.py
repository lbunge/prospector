"""Export business data to CRM-friendly formats."""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import List, Dict
from .config import Config


class DataExporter:
    """Export enriched business data to various formats."""

    def __init__(self, output_dir: Path = None):
        """
        Initialize the data exporter.

        Args:
            output_dir: Directory to save exports (default from config)
        """
        self.output_dir = output_dir or Config.OUTPUT_DIR
        self.output_dir.mkdir(exist_ok=True)

    def export_to_csv(
        self,
        businesses: List[Dict],
        filename: str = None,
        format_type: str = 'detailed'
    ) -> Path:
        """
        Export businesses to CSV format.

        Args:
            businesses: List of business dictionaries
            filename: Output filename (auto-generated if None)
            format_type: 'detailed' or 'simple' format

        Returns:
            Path to the exported file
        """
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"prospects_{timestamp}.csv"

        filepath = self.output_dir / filename

        if format_type == 'simple':
            df = self._create_simple_dataframe(businesses)
        else:
            df = self._create_detailed_dataframe(businesses)

        df.to_csv(filepath, index=False, encoding='utf-8')
        print(f"\n✓ Exported to CSV: {filepath}")

        return filepath

    def export_to_json(
        self,
        businesses: List[Dict],
        filename: str = None,
        pretty: bool = True
    ) -> Path:
        """
        Export businesses to JSON format.

        Args:
            businesses: List of business dictionaries
            filename: Output filename (auto-generated if None)
            pretty: Whether to pretty-print the JSON

        Returns:
            Path to the exported file
        """
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"prospects_{timestamp}.json"

        filepath = self.output_dir / filename

        indent = 2 if pretty else None
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(businesses, f, indent=indent, ensure_ascii=False)

        print(f"✓ Exported to JSON: {filepath}")

        return filepath

    def export_to_excel(
        self,
        businesses: List[Dict],
        filename: str = None
    ) -> Path:
        """
        Export businesses to Excel format with multiple sheets.

        Args:
            businesses: List of business dictionaries
            filename: Output filename (auto-generated if None)

        Returns:
            Path to the exported file
        """
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"prospects_{timestamp}.xlsx"

        filepath = self.output_dir / filename

        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # Main business sheet
            df_main = self._create_detailed_dataframe(businesses)
            df_main.to_excel(writer, sheet_name='Businesses', index=False)

            # Email details sheet
            df_emails = self._create_emails_dataframe(businesses)
            if not df_emails.empty:
                df_emails.to_excel(writer, sheet_name='Emails', index=False)

            # Summary statistics
            df_summary = self._create_summary_dataframe(businesses)
            df_summary.to_excel(writer, sheet_name='Summary', index=False)

        print(f"✓ Exported to Excel: {filepath}")

        return filepath

    def _create_simple_dataframe(self, businesses: List[Dict]) -> pd.DataFrame:
        """
        Create a simple DataFrame with essential fields.

        Args:
            businesses: List of business dictionaries

        Returns:
            pandas DataFrame
        """
        rows = []
        for business in businesses:
            # Create one row per email, or one row if no emails
            emails = business.get('emails_found', [])

            if emails:
                for email_info in emails:
                    rows.append({
                        'Business Name': business.get('name'),
                        'Email': email_info.get('email'),
                        'Email Type': email_info.get('type'),
                        'Phone': business.get('phone'),
                        'Website': business.get('website'),
                        'Address': business.get('formatted_address') or business.get('address'),
                        'Industry': business.get('industry'),
                        'Rating': business.get('rating'),
                        'Reviews': business.get('user_ratings_total'),
                    })
            else:
                rows.append({
                    'Business Name': business.get('name'),
                    'Email': None,
                    'Email Type': None,
                    'Phone': business.get('phone'),
                    'Website': business.get('website'),
                    'Address': business.get('formatted_address') or business.get('address'),
                    'Industry': business.get('industry'),
                    'Rating': business.get('rating'),
                    'Reviews': business.get('user_ratings_total'),
                })

        return pd.DataFrame(rows)

    def _create_detailed_dataframe(self, businesses: List[Dict]) -> pd.DataFrame:
        """
        Create a detailed DataFrame with all fields.

        Args:
            businesses: List of business dictionaries

        Returns:
            pandas DataFrame
        """
        rows = []
        for business in businesses:
            row = {
                'Business Name': business.get('name'),
                'Industry': business.get('industry'),
                'Address': business.get('formatted_address') or business.get('address'),
                'Phone': business.get('phone'),
                'International Phone': business.get('international_phone'),
                'Website': business.get('website'),
                'Google Maps URL': business.get('google_maps_url'),

                # Emails
                'Email Count': business.get('email_count', 0),
                'Generic Emails': ', '.join(business.get('generic_emails', [])),
                'Person Emails': ', '.join(business.get('person_emails', [])),
                'All Emails': ', '.join([e['email'] for e in business.get('emails_found', [])]),

                # Social Media
                'Facebook': business.get('social_media', {}).get('facebook'),
                'LinkedIn': business.get('social_media', {}).get('linkedin'),
                'Twitter': business.get('social_media', {}).get('twitter'),
                'Instagram': business.get('social_media', {}).get('instagram'),

                # Business Info
                'Categories': ', '.join(business.get('categories', [])),
                'Rating': business.get('rating'),
                'Total Reviews': business.get('user_ratings_total'),
                'Is Popular': business.get('is_popular'),
                'Price Level': business.get('price_level'),
                'Business Status': business.get('business_status'),
                'Currently Open': business.get('is_open_now'),

                # Location
                'Latitude': business.get('location', {}).get('lat'),
                'Longitude': business.get('location', {}).get('lng'),

                # IDs
                'Place ID': business.get('place_id'),
            }
            rows.append(row)

        return pd.DataFrame(rows)

    def _create_emails_dataframe(self, businesses: List[Dict]) -> pd.DataFrame:
        """
        Create a DataFrame focused on email details.

        Args:
            businesses: List of business dictionaries

        Returns:
            pandas DataFrame
        """
        rows = []
        for business in businesses:
            for email_info in business.get('emails_found', []):
                rows.append({
                    'Business Name': business.get('name'),
                    'Email': email_info.get('email'),
                    'Email Type': email_info.get('type'),
                    'Is Personal Domain': email_info.get('is_personal'),
                    'Domain': email_info.get('domain'),
                    'Source URL': email_info.get('source_url'),
                    'Business Website': business.get('website'),
                    'Business Phone': business.get('phone'),
                    'Business Address': business.get('formatted_address') or business.get('address'),
                })

        return pd.DataFrame(rows)

    def _create_summary_dataframe(self, businesses: List[Dict]) -> pd.DataFrame:
        """
        Create a summary statistics DataFrame.

        Args:
            businesses: List of business dictionaries

        Returns:
            pandas DataFrame
        """
        total_businesses = len(businesses)
        businesses_with_websites = sum(1 for b in businesses if b.get('website'))
        businesses_with_emails = sum(1 for b in businesses if b.get('email_count', 0) > 0)
        businesses_with_phones = sum(1 for b in businesses if b.get('phone'))

        total_emails = sum(b.get('email_count', 0) for b in businesses)
        generic_emails = sum(len(b.get('generic_emails', [])) for b in businesses)
        person_emails = sum(len(b.get('person_emails', [])) for b in businesses)

        # Industry breakdown
        industries = {}
        for b in businesses:
            industry = b.get('industry', 'Unknown')
            industries[industry] = industries.get(industry, 0) + 1

        rows = [
            {'Metric': 'Total Businesses', 'Value': total_businesses},
            {'Metric': 'Businesses with Websites', 'Value': businesses_with_websites},
            {'Metric': 'Businesses with Emails', 'Value': businesses_with_emails},
            {'Metric': 'Businesses with Phones', 'Value': businesses_with_phones},
            {'Metric': 'Total Emails Found', 'Value': total_emails},
            {'Metric': 'Generic Emails', 'Value': generic_emails},
            {'Metric': 'Person-Specific Emails', 'Value': person_emails},
            {'Metric': '', 'Value': ''},  # Spacer
            {'Metric': 'Top Industries', 'Value': ''},
        ]

        # Add top 5 industries
        top_industries = sorted(industries.items(), key=lambda x: x[1], reverse=True)[:5]
        for industry, count in top_industries:
            rows.append({'Metric': f"  {industry}", 'Value': count})

        return pd.DataFrame(rows)

    def export_all_formats(
        self,
        businesses: List[Dict],
        base_filename: str = None
    ) -> Dict[str, Path]:
        """
        Export to all available formats.

        Args:
            businesses: List of business dictionaries
            base_filename: Base filename (without extension)

        Returns:
            Dictionary mapping format to filepath
        """
        if not base_filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            base_filename = f"prospects_{timestamp}"

        exports = {}

        # CSV
        csv_file = f"{base_filename}.csv"
        exports['csv'] = self.export_to_csv(businesses, csv_file)

        # JSON
        json_file = f"{base_filename}.json"
        exports['json'] = self.export_to_json(businesses, json_file)

        # Excel
        excel_file = f"{base_filename}.xlsx"
        exports['excel'] = self.export_to_excel(businesses, excel_file)

        return exports

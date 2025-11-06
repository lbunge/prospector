#!/usr/bin/env python3
"""
Business Prospector CLI
Find businesses and their contact information for lead generation.
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from prospector.config import Config
from prospector.enricher import BusinessEnricher
from prospector.exporter import DataExporter


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Business Prospecting Tool - Find businesses and their contact information',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search for all businesses in downtown Seattle within 2km
  python prospector.py "downtown Seattle" --radius 2000

  # Search for restaurants in a specific area
  python prospector.py "Pike Place Market, Seattle" --type restaurant --radius 1000

  # Search for lawyers with specific keyword
  python prospector.py "Seattle, WA" --type lawyer --keyword "personal injury"

  # Export to specific format
  python prospector.py "downtown Portland" --format csv

  # Skip email/social media scraping
  python prospector.py "Austin, TX" --no-emails --no-social

Common business types:
  restaurant, cafe, bar, retail_store, clothing_store, lawyer, doctor,
  dentist, real_estate_agency, gym, beauty_salon, hair_care, etc.
        """
    )

    parser.add_argument(
        'location',
        help='Location to search (e.g., "downtown Seattle", "Pike Place Market")'
    )

    parser.add_argument(
        '-r', '--radius',
        type=int,
        default=5000,
        help='Search radius in meters (default: 5000m ≈ 3 miles)'
    )

    parser.add_argument(
        '-t', '--type',
        help='Business type filter (e.g., restaurant, lawyer, retail_store)'
    )

    parser.add_argument(
        '-k', '--keyword',
        help='Additional keyword filter'
    )

    parser.add_argument(
        '-f', '--format',
        choices=['csv', 'json', 'excel', 'hubspot', 'all'],
        default='all',
        help='Export format (default: all, includes HubSpot)'
    )

    parser.add_argument(
        '-o', '--output',
        help='Output filename (without extension)'
    )

    parser.add_argument(
        '--no-emails',
        action='store_true',
        help='Skip email scraping from websites'
    )

    parser.add_argument(
        '--no-social',
        action='store_true',
        help='Skip social media discovery'
    )

    parser.add_argument(
        '--api-key',
        help='Google Maps API key (overrides .env file)'
    )

    parser.add_argument(
        '--aggressive',
        action='store_true',
        help='Aggressive mode: maximum data collection (slower but more thorough)'
    )

    parser.add_argument(
        '--no-grid-search',
        action='store_true',
        help='Disable grid search (faster but may miss businesses)'
    )

    parser.add_argument(
        '--max-pages',
        type=int,
        help='Maximum pages to crawl per website (default: 10, aggressive: 15)'
    )

    args = parser.parse_args()

    try:
        # Validate configuration
        if args.api_key:
            Config.GOOGLE_MAPS_API_KEY = args.api_key

        Config.validate()

        # Set aggressive mode if requested
        if args.aggressive:
            Config.set_aggressive_mode(True)
            print("🚀 Aggressive mode enabled - maximum data collection")

        # Override config with CLI args
        if args.no_grid_search:
            Config.USE_GRID_SEARCH = False

        if args.max_pages:
            Config.MAX_PAGES_PER_WEBSITE = args.max_pages

        # Initialize enricher
        enricher = BusinessEnricher()

        # Run prospecting
        businesses = enricher.prospect_area(
            location=args.location,
            radius=args.radius,
            business_type=args.type,
            keyword=args.keyword,
            find_emails=not args.no_emails,
            find_social=not args.no_social
        )

        if not businesses:
            print("\n⚠ No businesses found. Try adjusting your search parameters.")
            return 1

        # Export results
        print(f"\nExporting results...")
        exporter = DataExporter()

        if args.format == 'all':
            exports = exporter.export_all_formats(businesses, args.output, include_hubspot=True)
            print(f"\n✓ Exported to {len(exports)} formats")
        elif args.format == 'csv':
            exporter.export_to_csv(businesses, args.output)
        elif args.format == 'json':
            exporter.export_to_json(businesses, args.output)
        elif args.format == 'excel':
            exporter.export_to_excel(businesses, args.output)
        elif args.format == 'hubspot':
            exporter.export_to_hubspot(businesses, args.output)

        print(f"\n{'='*60}")
        print("Prospecting Complete!")
        print(f"{'='*60}")

        return 0

    except ValueError as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure you have:")
        print("1. Created a .env file with your GOOGLE_MAPS_API_KEY")
        print("2. Or use --api-key to provide the API key")
        return 1

    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
        return 1

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

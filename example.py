#!/usr/bin/env python3
"""
Example script demonstrating programmatic usage of the Business Prospector.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from prospector.config import Config
from prospector.enricher import BusinessEnricher
from prospector.exporter import DataExporter


def example_basic_search():
    """Example: Basic business search."""
    print("="*60)
    print("Example 1: Basic Business Search")
    print("="*60)

    # Validate config
    Config.validate()

    # Initialize enricher
    enricher = BusinessEnricher()

    # Search for businesses
    businesses = enricher.prospect_area(
        location="downtown Seattle",
        radius=2000,  # 2km radius
        find_emails=True,
        find_social=True
    )

    print(f"\nFound {len(businesses)} businesses")

    # Export to CSV
    exporter = DataExporter()
    csv_file = exporter.export_to_csv(businesses, "example_basic.csv")
    print(f"Results saved to: {csv_file}")


def example_filtered_search():
    """Example: Filtered search by business type."""
    print("\n" + "="*60)
    print("Example 2: Filtered Search (Restaurants)")
    print("="*60)

    Config.validate()
    enricher = BusinessEnricher()

    # Search for restaurants specifically
    businesses = enricher.prospect_area(
        location="Pike Place Market, Seattle",
        radius=1000,
        business_type="restaurant",
        keyword="seafood",
        find_emails=True,
        find_social=False  # Skip social media for speed
    )

    print(f"\nFound {len(businesses)} seafood restaurants")

    # Show summary of emails found
    total_emails = sum(b.get('email_count', 0) for b in businesses)
    businesses_with_emails = sum(1 for b in businesses if b.get('email_count', 0) > 0)

    print(f"Businesses with emails: {businesses_with_emails}/{len(businesses)}")
    print(f"Total emails found: {total_emails}")

    # Export to Excel
    exporter = DataExporter()
    excel_file = exporter.export_to_excel(businesses, "example_restaurants.xlsx")
    print(f"Results saved to: {excel_file}")


def example_single_business():
    """Example: Enrich a single business."""
    print("\n" + "="*60)
    print("Example 3: Single Business Enrichment")
    print("="*60)

    Config.validate()
    enricher = BusinessEnricher()

    # Enrich a specific business by name
    business = enricher.enrich_single_business(
        business_name="Starbucks Reserve Roastery",
        location="Seattle, WA"
    )

    if business:
        print(f"\nBusiness: {business['name']}")
        print(f"Address: {business.get('formatted_address', 'N/A')}")
        print(f"Phone: {business.get('phone', 'N/A')}")
        print(f"Website: {business.get('website', 'N/A')}")

        emails = business.get('emails_found', [])
        if emails:
            print(f"\nEmails found ({len(emails)}):")
            for email_info in emails:
                print(f"  - {email_info['email']} ({email_info['type']})")
        else:
            print("\nNo emails found")

        social = business.get('social_media', {})
        if social:
            print(f"\nSocial media:")
            for platform, url in social.items():
                print(f"  - {platform}: {url}")
    else:
        print("Business not found")


def example_analysis():
    """Example: Analyze prospecting results."""
    print("\n" + "="*60)
    print("Example 4: Results Analysis")
    print("="*60)

    Config.validate()
    enricher = BusinessEnricher()

    # Search for professional services
    businesses = enricher.prospect_area(
        location="downtown Portland, OR",
        radius=3000,
        business_type="lawyer",
        find_emails=True,
        find_social=True
    )

    print(f"\n{'='*60}")
    print("ANALYSIS RESULTS")
    print(f"{'='*60}\n")

    # Overall stats
    print(f"Total businesses found: {len(businesses)}")

    # Email statistics
    businesses_with_websites = sum(1 for b in businesses if b.get('website'))
    businesses_with_emails = sum(1 for b in businesses if b.get('email_count', 0) > 0)
    total_emails = sum(b.get('email_count', 0) for b in businesses)
    generic_emails = sum(len(b.get('generic_emails', [])) for b in businesses)
    person_emails = sum(len(b.get('person_emails', [])) for b in businesses)

    print(f"\nWebsite Coverage:")
    print(f"  Businesses with websites: {businesses_with_websites} "
          f"({businesses_with_websites/len(businesses)*100:.1f}%)")

    print(f"\nEmail Discovery:")
    print(f"  Businesses with emails: {businesses_with_emails} "
          f"({businesses_with_emails/len(businesses)*100:.1f}%)")
    print(f"  Total emails found: {total_emails}")
    print(f"  Generic emails (info@, contact@): {generic_emails}")
    print(f"  Person-specific emails: {person_emails}")

    # Rating distribution
    rated_businesses = [b for b in businesses if b.get('rating')]
    if rated_businesses:
        avg_rating = sum(b['rating'] for b in rated_businesses) / len(rated_businesses)
        print(f"\nRating Statistics:")
        print(f"  Average rating: {avg_rating:.2f} stars")
        print(f"  Businesses with ratings: {len(rated_businesses)}")

    # Popular businesses
    popular = [b for b in businesses if b.get('is_popular')]
    print(f"\nPopular Businesses (4+ stars, 50+ reviews): {len(popular)}")

    # Top businesses by reviews
    print(f"\nTop 5 Most Reviewed:")
    sorted_by_reviews = sorted(
        [b for b in businesses if b.get('user_ratings_total')],
        key=lambda x: x['user_ratings_total'],
        reverse=True
    )[:5]

    for i, business in enumerate(sorted_by_reviews, 1):
        print(f"  {i}. {business['name']} - "
              f"{business['user_ratings_total']} reviews "
              f"({business.get('rating', 'N/A')} stars)")

    # Export comprehensive results
    exporter = DataExporter()
    exports = exporter.export_all_formats(businesses, "example_analysis")
    print(f"\nExported to: {', '.join(exports.keys())}")


def main():
    """Run all examples."""
    try:
        print("\n" + "="*60)
        print("Business Prospector - Example Usage")
        print("="*60)

        # Choose which examples to run
        print("\nSelect example to run:")
        print("1. Basic business search")
        print("2. Filtered search (restaurants)")
        print("3. Single business enrichment")
        print("4. Results analysis")
        print("5. Run all examples")

        choice = input("\nEnter choice (1-5): ").strip()

        if choice == '1':
            example_basic_search()
        elif choice == '2':
            example_filtered_search()
        elif choice == '3':
            example_single_business()
        elif choice == '4':
            example_analysis()
        elif choice == '5':
            example_basic_search()
            example_filtered_search()
            example_single_business()
            example_analysis()
        else:
            print("Invalid choice")
            return 1

        print("\n" + "="*60)
        print("Examples completed successfully!")
        print("="*60)
        return 0

    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}")
        print("\nMake sure you have set up your .env file with GOOGLE_MAPS_API_KEY")
        return 1
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

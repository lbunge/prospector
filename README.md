# Business Prospector 🔍

A powerful Python tool for automated business prospecting and lead generation. Search for businesses in any area using Google Maps, then automatically discover their contact information including email addresses, phone numbers, and social media profiles.

## Features

✨ **Comprehensive Business Discovery**
- Search businesses by location (address, neighborhood, city)
- Filter by business type and keywords
- Configurable search radius
- Extract detailed business information from Google Maps

📧 **Intelligent Email Finding**
- Automatically scrapes business websites for email addresses
- Distinguishes between generic emails (info@, contact@) and person-specific emails
- Crawls contact pages and about pages
- Validates email addresses

📊 **Rich Business Data**
- Business name, address, phone number
- Website and Google Maps URL
- Industry/category classification
- Customer ratings and review counts
- Popularity indicators
- Business status (open/closed, veteran-owned, etc.)
- Social media profiles (Facebook, LinkedIn, Twitter, Instagram)

💾 **CRM-Ready Export**
- Export to CSV, JSON, or Excel formats
- Multiple email addresses per business
- Detailed and simplified export formats
- Summary statistics and industry breakdown

## Prerequisites

- Python 3.8 or higher
- Google Maps API key ([Get one here](https://developers.google.com/maps/documentation/javascript/get-api-key))

## Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd prospector
```

2. **Create a virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Install Playwright browsers (for JavaScript-heavy websites):**
```bash
playwright install chromium
```

5. **Set up your Google Maps API key:**

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` and add your Google Maps API key:
```
GOOGLE_MAPS_API_KEY=your_actual_api_key_here
```

### Getting a Google Maps API Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the following APIs:
   - Places API
   - Geocoding API
4. Go to "Credentials" and create an API key
5. (Optional) Restrict the API key to only the necessary APIs

**Note:** Google Maps API has a free tier with $200 monthly credit, which is sufficient for moderate usage.

## Usage

### Basic Usage

Search for all businesses in an area:
```bash
python prospector.py "downtown Seattle"
```

### Search with Radius

Search within a specific radius (in meters):
```bash
python prospector.py "Pike Place Market, Seattle" --radius 2000
```

### Filter by Business Type

Search for specific types of businesses:
```bash
# Find restaurants
python prospector.py "downtown Portland" --type restaurant

# Find lawyers
python prospector.py "Seattle, WA" --type lawyer

# Find retail stores
python prospector.py "Austin, TX" --type retail_store
```

### Add Keywords

Further refine your search with keywords:
```bash
python prospector.py "Miami, FL" --type lawyer --keyword "personal injury"
python prospector.py "San Francisco" --type restaurant --keyword "italian"
```

### Export Options

Choose your export format:
```bash
# Export to CSV only
python prospector.py "Boston, MA" --format csv

# Export to JSON only
python prospector.py "Chicago, IL" --format json

# Export to Excel only
python prospector.py "Denver, CO" --format excel

# Export to all formats (default)
python prospector.py "Nashville, TN" --format all
```

### Custom Output Filename

Specify a custom filename:
```bash
python prospector.py "downtown Atlanta" --output atlanta_restaurants --format csv
```

### Performance Options

Skip email or social media scraping to speed up the process:
```bash
# Skip email scraping
python prospector.py "Phoenix, AZ" --no-emails

# Skip social media discovery
python prospector.py "Philadelphia, PA" --no-social

# Skip both
python prospector.py "San Diego, CA" --no-emails --no-social
```

### Complete Example

A comprehensive prospecting campaign:
```bash
python prospector.py "downtown Seattle, WA" \
  --type restaurant \
  --keyword "seafood" \
  --radius 3000 \
  --format excel \
  --output seattle_seafood_restaurants
```

## Common Business Types

Here are some commonly used business types:

- `restaurant` - Restaurants and eateries
- `cafe` - Coffee shops and cafes
- `bar` - Bars and pubs
- `lawyer` - Law firms and attorneys
- `doctor` - Medical practices
- `dentist` - Dental practices
- `real_estate_agency` - Real estate agencies
- `gym` - Gyms and fitness centers
- `beauty_salon` - Beauty salons
- `hair_care` - Hair salons
- `accounting` - Accounting firms
- `insurance_agency` - Insurance agencies
- `car_repair` - Auto repair shops
- `retail_store` - General retail
- `clothing_store` - Clothing retailers
- `electronics_store` - Electronics retailers

See the [full list of Google Places types](https://developers.google.com/maps/documentation/places/web-service/supported_types).

## Output Format

### CSV Export

The CSV export includes one row per business-email combination:

| Business Name | Email | Email Type | Phone | Website | Address | Industry | Rating |
|--------------|-------|------------|-------|---------|---------|----------|--------|
| Acme Corp | info@acme.com | generic | (555) 123-4567 | acme.com | 123 Main St | Technology | 4.5 |
| Acme Corp | john@acme.com | person | (555) 123-4567 | acme.com | 123 Main St | Technology | 4.5 |

### Excel Export

The Excel export includes multiple sheets:

1. **Businesses** - Comprehensive business data
2. **Emails** - Detailed email information
3. **Summary** - Statistics and industry breakdown

### JSON Export

Complete structured data in JSON format, including:
- Full business details
- Array of email objects with metadata
- Social media profiles
- Location coordinates
- And more...

## Output Files

All output files are saved to the `output/` directory with timestamps:

```
output/
├── prospects_20240115_143022.csv
├── prospects_20240115_143022.json
└── prospects_20240115_143022.xlsx
```

## Data Fields

### Business Information
- Business name and place ID
- Full address and coordinates (lat/lng)
- Phone number (formatted and international)
- Website URL
- Google Maps URL
- Industry/category
- Business status

### Performance Metrics
- Customer rating (0-5 stars)
- Total number of reviews
- Popularity indicator
- Price level

### Contact Information
- Email addresses (generic and person-specific)
- Email types and sources
- Social media profiles

### Operating Hours
- Weekly schedule
- Currently open status

## Rate Limiting and Best Practices

- The tool implements automatic rate limiting to respect website policies
- Default: max 5 pages crawled per website
- Includes delays between requests
- Uses respectful User-Agent headers

**Important:** Always ensure your web scraping activities comply with:
- Website terms of service
- robots.txt files
- Local laws and regulations (e.g., GDPR, CAN-SPAM)
- Google Maps API Terms of Service

## Troubleshooting

### "GOOGLE_MAPS_API_KEY is required" Error

Make sure you've created a `.env` file with your API key, or use the `--api-key` flag:
```bash
python prospector.py "Seattle" --api-key YOUR_API_KEY
```

### No Businesses Found

Try:
- Increasing the search radius: `--radius 10000`
- Using a more general location: "Seattle, WA" instead of a specific address
- Removing business type filters
- Using different keywords

### Few or No Emails Found

This is normal! Not all businesses have email addresses on their websites. Try:
- Businesses with websites are more likely to have emails
- Larger search radius = more businesses = more chances to find emails
- Some industries (professional services) are more likely to list emails

### API Quota Exceeded

Google Maps API has usage limits. Monitor your usage in the Google Cloud Console and consider:
- Reducing search radius
- Being more specific with business types
- Implementing pagination for large searches

## Project Structure

```
prospector/
├── src/prospector/
│   ├── __init__.py
│   ├── config.py           # Configuration management
│   ├── maps_scraper.py     # Google Maps integration
│   ├── email_finder.py     # Email scraping functionality
│   ├── enricher.py         # Business enrichment
│   └── exporter.py         # Data export formats
├── output/                  # Export files
├── prospector.py           # Main CLI script
├── requirements.txt        # Python dependencies
├── .env.example            # Example environment file
└── README.md               # This file
```

## Advanced Usage

### Programmatic Usage

You can also use the tool as a Python library:

```python
from prospector.enricher import BusinessEnricher
from prospector.exporter import DataExporter

# Initialize
enricher = BusinessEnricher()

# Prospect businesses
businesses = enricher.prospect_area(
    location="downtown Seattle",
    radius=5000,
    business_type="restaurant",
    find_emails=True,
    find_social=True
)

# Export results
exporter = DataExporter()
exporter.export_to_csv(businesses, "my_prospects.csv")
```

### Configuration

Edit `src/prospector/config.py` to adjust:
- Request timeouts
- Max pages to crawl per website
- Rate limiting settings
- Output directory

## Use Cases

- **Sales & Lead Generation**: Build targeted prospect lists for outreach
- **Market Research**: Understand business density and types in an area
- **Competitor Analysis**: Find similar businesses in a location
- **Partnership Opportunities**: Discover potential business partners
- **Local Marketing**: Build lists for local advertising campaigns
- **CRM Population**: Populate your CRM with fresh leads

## Legal and Ethical Considerations

⚠️ **Important**: This tool is designed for legitimate business purposes only.

- **Comply with laws**: Ensure compliance with GDPR, CAN-SPAM, and local regulations
- **Respect privacy**: Only use publicly available information
- **Terms of Service**: Respect website ToS and robots.txt
- **Rate limiting**: Don't overwhelm websites with requests
- **Purpose**: Use for legitimate business purposes only
- **Opt-out**: Honor opt-out and do-not-contact requests

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues.

## License

This project is provided as-is for educational and legitimate business purposes.

## Support

For issues, questions, or feature requests, please open an issue on GitHub.

---

**Happy Prospecting! 🎯**

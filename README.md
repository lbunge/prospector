# Business Prospector 🔍

A powerful Python tool for automated business prospecting and lead generation. Search for businesses using Google Maps, automatically discover contact information, validate emails, detect franchises, and export directly to HubSpot CRM.

## Quick Start

### Installation

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure API key
cp .env.example .env
# Edit .env and add your GOOGLE_MAPS_API_KEY

# 3. Run your first search
python prospector.py "Monroe, MI" --radius 5000
```

### Basic Usage

```bash
# Search for businesses in an area
python prospector.py "downtown Seattle" --radius 3000

# Filter by type and export to HubSpot
python prospector.py "Monroe, MI" --type restaurant --format hubspot

# Large campaign with batch processing
python prospector.py "Seattle, WA" --radius 10000 --batch --aggressive
```

## Features

### 🔍 **Comprehensive Business Discovery**
- **Grid-based search** for complete coverage (finds 200-300 vs 60 businesses)
- Filter by business type, keywords, radius
- Extract detailed Google Maps data

### 📧 **Smart Contact Finding**
- Website discovery with Google search fallback (+30-40% success)
- Deep email scraping (generic + person-specific)
- **Email validation** (3-tier: MX check, Hunter.io, ZeroBounce)
- **Email permutation** (generates decision-maker emails: owner@, ceo@, etc.)
- Phone validation with carrier detection

### 🏪 **Franchise Detection**
- Identifies franchise vs local independent businesses
- **Prioritizes local contacts** over corporate emails
- Detects toll-free (corporate) vs local phone numbers
- Scores and ranks by local preference

### ⭐ **Data Enrichment**
- **Yelp integration** (ratings, reviews, sentiment analysis)
- Social media discovery (Facebook, LinkedIn, Twitter, Instagram)
- Review analysis with keyword extraction
- Technology stack detection

### 📊 **Lead Scoring & Prioritization**
- **Comprehensive lead score** (0-100 points)
- Grade (A+ to F) and priority level (urgent/high/medium/low)
- 6 scoring factors: contact quality, legitimacy, local preference, online presence, reputation, opportunity size
- **Automatic sorting** by lead score (best leads first)

### 💾 **HubSpot CRM Export**
- **Direct HubSpot CSV export** with custom field mapping
- Multiple export formats (CSV, JSON, Excel, HubSpot)
- Separate contact rows for additional emails
- Ready to import with one click

### ⚡ **Performance & Scalability**
- **Batch processing** with automatic checkpointing
- **Resume capability** after interruptions
- **Automatic streaming** for 1000+ businesses (prevents memory issues)
- Rate limiting with exponential backoff
- Handles campaigns of any size

## Documentation

| Document | Description |
|----------|-------------|
| **[QUICKSTART.md](QUICKSTART.md)** | Get started in 5 minutes |
| **[ULTIMATE_GUIDE.md](ULTIMATE_GUIDE.md)** | Complete feature guide with examples |
| **[PERFORMANCE.md](PERFORMANCE.md)** | Performance tuning, memory management, large campaigns |
| **[ENHANCEMENTS.md](ENHANCEMENTS.md)** | Detailed feature descriptions |
| **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** | Common issues and solutions |

## Command-Line Options

### Basic Options
```bash
python prospector.py <location> [options]

Required:
  location              Location to search (e.g., "Monroe, MI", "downtown Seattle")

Search Options:
  -r, --radius METERS   Search radius in meters (default: 5000)
  -t, --type TYPE       Business type filter (restaurant, lawyer, etc.)
  -k, --keyword TEXT    Additional keyword filter

Export Options:
  -f, --format FORMAT   Export format: csv, json, excel, hubspot, all (default: all)
  -o, --output NAME     Output filename (without extension)

Features:
  --aggressive          Maximum data collection (slower but thorough)
  --no-emails           Skip email scraping
  --no-social           Skip social media discovery
  --no-grid-search      Disable grid search (faster, may miss businesses)
  --max-pages N         Max pages to crawl per website (default: 10)

Performance:
  --batch               Enable batch processing with checkpoints
  --batch-size N        Checkpoint interval (default: 10)
  --resume              Resume from previous checkpoint
```

### Examples

**Small Campaign (<100 businesses):**
```bash
python prospector.py "downtown Monroe, MI" --radius 3000 --aggressive
```

**Medium Campaign (100-300 businesses):**
```bash
python prospector.py "Monroe, MI" --radius 5000 --batch --aggressive --format hubspot
```

**Large Campaign (300-1000 businesses):**
```bash
python prospector.py "Monroe County, MI" --radius 10000 --batch --batch-size 20
```

**Resume After Interruption:**
```bash
python prospector.py "Monroe, MI" --radius 5000 --batch --resume
```

## Configuration

### Required API Keys

**Google Maps API** (Required):
- Free tier: $200/month credit (~40,000 requests)
- [Get API key →](https://developers.google.com/maps/documentation/javascript/get-api-key)

### Optional API Keys

Add these to `.env` for enhanced features:

**Yelp Fusion API** (Recommended):
- Free tier: 5,000 requests/day
- Adds ratings, reviews, sentiment analysis
- [Get API key →](https://www.yelp.com/developers)

**Hunter.io** (Email Validation):
- Free tier: 25 validations/month
- SMTP verification, deliverability scoring
- [Get API key →](https://hunter.io/api)

**ZeroBounce** (Email Validation):
- Free tier: 100 credits/month
- Full validation, catch-all detection
- [Get API key →](https://www.zerobounce.net/)

**HubSpot API** (Direct Push):
- Push leads directly to HubSpot (optional - CSV export works without API)
- [Get API key →](https://developers.hubspot.com/)

### Configuration File

Edit `src/prospector/config.py` to customize:

```python
# Search thoroughness
USE_GRID_SEARCH = True          # Complete coverage (recommended)
GRID_SIZE_METERS = 2000          # Grid cell size
MAX_PAGES_PER_WEBSITE = 10       # Crawling depth

# Enrichment features
ENRICH_WITH_YELP = True          # Yelp ratings & reviews
VALIDATE_EMAILS = True           # Email validation
PERMUTE_EMAILS = True            # Generate decision-maker emails
DETECT_FRANCHISES = True         # Franchise detection
PRIORITIZE_LOCAL_CONTACTS = True # Local over corporate

# Lead scoring
ENABLE_LEAD_SCORING = True       # Calculate lead scores
```

## Performance

### Automatic Optimizations

The tool automatically optimizes for your dataset size:

| Businesses | Auto-Enabled Features | Expected Time | Memory |
|-----------|----------------------|---------------|--------|
| < 100 | Standard processing | 10-20 min | <200 MB |
| 100-500 | None (runs normally) | 30-90 min | 200-300 MB |
| **500-1000** | **Auto batch processing** | 2-3 hours | 300-400 MB |
| **1000+** | **Auto streaming mode** | 3-10+ hours | **<500 MB** |

### Manual Control

For complete control over performance:

```bash
# Force batch processing (any size)
python prospector.py "location" --batch --batch-size 10

# Large campaigns (recommended for 1000+)
python prospector.py "location" --batch --batch-size 50 --max-pages 5
```

**See [PERFORMANCE.md](PERFORMANCE.md) for detailed optimization guide.**

## Output

### Files Created

When using `--format all` (default), you'll get:

```
output/
├── results.csv              # Standard CSV
├── results.json             # Full JSON with all data
├── results.xlsx             # Excel spreadsheet
└── results_hubspot.csv      # HubSpot-ready import
```

### HubSpot Import

The `*_hubspot.csv` file is ready to import directly:

1. In HubSpot, go to **Contacts** → **Import**
2. Choose **File from computer**
3. Upload `results_hubspot.csv`
4. Map custom fields (most are auto-mapped)
5. Complete import

**All enrichment data** is included: lead score, grade, franchise detection, validation status, social media, ratings, etc.

## Workflow Example

### Complete Monroe, MI Campaign

```bash
# 1. Search veteran-owned businesses in Monroe
python prospector.py "veteran owned businesses Monroe, MI" \
  --radius 8000 \
  --aggressive \
  --batch \
  --format hubspot

# Output:
# ✓ Found 250 businesses (grid search)
# ✓ 180 websites discovered (72%)
# ✓ 420 emails found (avg 1.7 per business)
# ✓ 156 emails validated as deliverable (37%)
# ✓ 45 high-priority leads identified
# ✓ Local businesses prioritized
# ✓ Results sorted by lead score

# 2. Import results_hubspot.csv to HubSpot

# 3. Start outreach to top-scoring leads first
```

## Troubleshooting

### Common Issues

**"No businesses found":**
- Increase search radius: `--radius 10000`
- Use less specific keywords
- Try different location formats

**"SSL/TLS connection error" (Windows):**
- See [TROUBLESHOOTING.md](TROUBLESHOOTING.md#ssltls-errors)
- Run `python test_connection.py` for diagnosis

**Out of memory on large campaigns:**
- **This is now auto-fixed** (streaming mode enabled at 1000+ businesses)
- Or manually enable: `--batch --batch-size 50`

**Process interrupted:**
```bash
# Resume from checkpoint
python prospector.py "location" --batch --resume
```

**For more issues:** See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

## System Requirements

- **Python:** 3.8 or higher
- **Memory:** 2GB RAM minimum, 4GB+ recommended for large campaigns
- **Storage:** 100MB for application, 1-10MB per 1000 businesses
- **Network:** Stable internet connection (makes many API requests)

## API Usage & Costs

### Typical Campaign (250 businesses)

| Service | Requests | Cost (Free Tier) |
|---------|----------|------------------|
| Google Maps | ~280 | Free ($200/mo credit) |
| Yelp | 250 | Free (5000/day) |
| Hunter.io | ~400 emails | $$ (25/mo free) |
| ZeroBounce | ~400 emails | $$ (100/mo free) |

**Tip:** Use MX-only validation (free) for large campaigns, save Hunter/ZeroBounce for high-priority leads.

## Support & Issues

- **Documentation:** Start with [QUICKSTART.md](QUICKSTART.md)
- **Performance Issues:** See [PERFORMANCE.md](PERFORMANCE.md)
- **Bugs/Features:** Open an issue on GitHub
- **Configuration:** See [ULTIMATE_GUIDE.md](ULTIMATE_GUIDE.md)

## Architecture

```
prospector/
├── prospector.py                    # Main CLI entry point
├── src/prospector/
│   ├── config.py                    # Configuration management
│   ├── maps_scraper.py              # Google Maps API integration
│   ├── email_finder.py              # Website scraping & email discovery
│   ├── website_finder.py            # Website discovery with fallbacks
│   ├── enricher.py                  # Main enrichment orchestrator
│   ├── yelp_enricher.py             # Yelp API integration
│   ├── email_validator.py           # Email validation & permutation
│   ├── phone_validator.py           # Phone number validation
│   ├── franchise_detector.py        # Franchise vs local detection
│   ├── lead_scorer.py               # Lead scoring algorithm
│   ├── batch_processor.py           # Batch processing & streaming
│   ├── exporter.py                  # Data export (all formats)
│   └── hubspot_exporter.py          # HubSpot-specific export
├── output/                          # Generated results
└── .prospector_checkpoints/         # Progress checkpoints
```

## Key Algorithms

### Grid Search
Breaks large areas into 2km overlapping cells, searches each independently. Finds 5-10x more businesses than standard search.

### Franchise Detection
- Pattern matching against 100+ known chains
- Domain analysis for corporate patterns
- Phone type detection (toll-free = corporate)
- Location number detection (#123, Store 5)

### Lead Scoring
6-factor algorithm (100 points total):
1. Contact Quality (25 pts): emails, validation, phone
2. Legitimacy (20 pts): website, verification, status
3. Local Preference (15 pts): local vs franchise, local contacts
4. Online Presence (15 pts): website, social, reviews
5. Reputation (15 pts): ratings, review counts
6. Opportunity (10 pts): popularity, size indicators

### Email Permutation
Generates role-based emails using company name and domain:
- owner@, ceo@, president@, manager@
- firstname.lastname@, firstlast@, f.lastname@
- Pattern detection from existing emails
- Validation of generated emails

## License

MIT License - see LICENSE file for details

## Changelog

### v2.0.0 (Latest)
- ✨ **Auto-streaming for 1000+ businesses** (prevents memory issues)
- ✨ Auto-enable batch processing at 500+ businesses
- 🐛 Fixed NoneType errors in lead scoring
- 📚 Consolidated documentation

### v1.5.0
- ✨ Batch processing with checkpointing
- ✨ Resume capability after interruptions
- ✨ Memory-efficient streaming option
- 📊 Performance optimization guide

### v1.0.0
- 🎉 Initial release with full enrichment suite
- 📧 Email validation & permutation
- 🏪 Franchise detection
- 📊 Lead scoring
- 💾 HubSpot CRM export

---

**Ready to start?** → [QUICKSTART.md](QUICKSTART.md)

**Need help?** → [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

**Advanced features?** → [ULTIMATE_GUIDE.md](ULTIMATE_GUIDE.md)

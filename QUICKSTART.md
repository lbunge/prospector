# Quick Start Guide

Get up and running with Business Prospector in 5 minutes!

## Step 1: Get Your Google Maps API Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable these APIs:
   - **Places API** (required)
   - **Geocoding API** (required)
4. Create credentials → API Key
5. Copy your API key

**Free tier**: $200/month credit = ~40,000 place details requests

## Step 2: Install

```bash
# Clone and navigate
cd prospector

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install browser for JavaScript sites (optional)
playwright install chromium
```

## Step 3: Configure

Create `.env` file:
```bash
cp .env.example .env
```

Edit `.env` and add your API key:
```
GOOGLE_MAPS_API_KEY=your_api_key_here
```

## Step 4: Run Your First Search

```bash
# Search for restaurants in downtown Seattle
python prospector.py "downtown Seattle" --type restaurant --radius 2000
```

That's it! Your results will be in the `output/` directory.

## Common Use Cases

### Local Business Outreach
```bash
python prospector.py "downtown Portland, OR" --radius 3000 --format csv
```

### Specific Industry Targeting
```bash
# Law firms
python prospector.py "Manhattan, NY" --type lawyer --keyword "corporate"

# Dental offices
python prospector.py "San Francisco" --type dentist --radius 5000

# Real estate agencies
python prospector.py "Miami, FL" --type real_estate_agency
```

### Fast Scan (No Email Scraping)
```bash
python prospector.py "Austin, TX" --type restaurant --no-emails
```

## Understanding the Output

### CSV File
- One row per business-email combination
- Import directly into most CRMs
- Great for Excel/Google Sheets

### Excel File (Recommended)
- **Businesses** sheet: Full business data
- **Emails** sheet: Detailed email info
- **Summary** sheet: Statistics

### JSON File
- Complete structured data
- Best for custom integrations
- All metadata included

## Tips for Better Results

1. **Start Broad, Then Narrow**
   ```bash
   # First, see what's there
   python prospector.py "Seattle, WA" --no-emails

   # Then target specific types
   python prospector.py "Seattle, WA" --type restaurant --radius 3000
   ```

2. **Use Landmarks for Downtown Areas**
   ```bash
   python prospector.py "Times Square, New York"
   python prospector.py "Pike Place Market, Seattle"
   ```

3. **Adjust Radius Based on Density**
   - Urban areas: 1000-3000m
   - Suburban areas: 5000-10000m
   - Rural areas: 10000-20000m

4. **Check Your API Usage**
   - Monitor at [Google Cloud Console](https://console.cloud.google.com/)
   - Each business detail call counts toward quota
   - Free tier is generous but not unlimited

## Next Steps

- Read the full [README.md](README.md) for all options
- Explore different business types
- Set up a CRM import workflow
- Automate regular prospecting runs

## Troubleshooting Quick Fixes

**No businesses found?**
- Increase radius: `--radius 10000`
- Try a more general location
- Remove the `--type` filter

**Few emails found?**
- Normal! Not all sites list emails publicly
- Try professional services (lawyers, real estate)
- Larger search = more total emails

**API errors?**
- Check your API key in `.env`
- Verify APIs are enabled in Google Cloud
- Check your quota isn't exceeded

---

**Need help?** Open an issue on GitHub or check the full README.

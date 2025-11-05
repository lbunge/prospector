# Troubleshooting Guide

This guide helps resolve common issues with the Business Prospector tool.

## Quick Diagnosis

Run the connection test script first:
```bash
python test_connection.py
```

This will check your setup and identify issues.

---

## SSL/TLS Connection Errors

### Error: `SSLEOFError: [SSL: UNEXPECTED_EOF_WHILE_READING]`

This is a common SSL handshake error on Windows, especially with Python 3.11+.

**Solution 1: Update SSL-related packages**
```bash
pip install --upgrade certifi urllib3 requests
```

**Solution 2: Reinstall the requirements**
```bash
pip uninstall -y certifi urllib3 requests googlemaps
pip install -r requirements.txt
```

**Solution 3: Use Python 3.10 or 3.11**

If you're using Python 3.12+, consider using Python 3.10 or 3.11 which have better SSL compatibility.

**Solution 4: Check your network**

If behind a corporate firewall or proxy:
```bash
# Set proxy environment variables (if needed)
set HTTPS_PROXY=http://your-proxy:port
set HTTP_PROXY=http://your-proxy:port

# Or in PowerShell
$env:HTTPS_PROXY="http://your-proxy:port"
$env:HTTP_PROXY="http://your-proxy:port"
```

**Solution 5: Windows-specific fix**

Update Windows certificates:
1. Open Windows Update
2. Check for optional updates
3. Install any certificate updates

---

## Google Maps API Errors

### Error: `GOOGLE_MAPS_API_KEY is required`

**Solution:**
1. Create a `.env` file in the project root:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your API key:
   ```
   GOOGLE_MAPS_API_KEY=your_actual_api_key_here
   ```

3. Verify the file is saved as `.env` (not `.env.txt`)

### Error: `REQUEST_DENIED` or `API key not valid`

**Solution:**

1. **Enable required APIs** in [Google Cloud Console](https://console.cloud.google.com/):
   - Places API
   - Geocoding API

2. **Check API key restrictions**:
   - Go to Credentials in Google Cloud Console
   - Make sure your API key isn't restricted to specific IPs/domains
   - Or add your current IP to the allowed list

3. **Verify the API key is correct**:
   - No extra spaces
   - Complete key copied
   - Not expired

### Error: `OVER_QUERY_LIMIT`

**Solution:**

You've exceeded your free tier quota.

1. Check usage at [Google Cloud Console](https://console.cloud.google.com/apis/api/places-backend.googleapis.com/quotas)

2. Options:
   - Wait until quota resets (monthly)
   - Enable billing for higher limits
   - Reduce search radius to get fewer results
   - Use `--no-emails` flag to skip some processing

---

## Installation Issues

### Error: `pip install` fails

**Solution 1: Update pip**
```bash
python -m pip install --upgrade pip
```

**Solution 2: Install with verbose output**
```bash
pip install -r requirements.txt -v
```

**Solution 3: Install problematic packages separately**
```bash
# If lxml fails
pip install lxml --only-binary :all:

# If pandas fails
pip install pandas --only-binary :all:
```

### Error: Playwright browser installation fails

**Solution:**

Playwright is optional (only needed for JavaScript-heavy websites).

Skip it:
```bash
# Install without playwright
pip install requests beautifulsoup4 lxml pandas python-dotenv googlemaps email-validator validators ratelimit openpyxl certifi urllib3
```

Or install just the browser:
```bash
playwright install chromium
```

---

## Runtime Errors

### Error: `No businesses found`

**Solutions:**

1. **Increase search radius**:
   ```bash
   python prospector.py "Monroe, MI" --radius 10000
   ```

2. **Use more general location**:
   ```bash
   # Instead of specific address
   python prospector.py "Monroe, MI"

   # Instead of "downtown X"
   python prospector.py "Seattle, WA"
   ```

3. **Remove filters**:
   ```bash
   # Don't use --type or --keyword initially
   python prospector.py "Monroe, MI"
   ```

4. **Check the location exists**:
   - Google the location to verify spelling
   - Use city, state format: "City, ST"

### Error: Few or no emails found

**This is normal!** Not all businesses list emails publicly on their websites.

**Why this happens:**
- Many businesses don't have websites
- Many websites don't list email addresses
- Some use contact forms instead of emails
- Some emails are obfuscated or in images

**Tips to find more emails:**
- Target professional services (lawyers, real estate, accounting)
- Increase search radius to get more businesses
- Look for businesses with 4+ star ratings (more established)

### Error: `Could not geocode location`

**Solution:**

The location couldn't be found.

Try:
- Adding state/country: "Monroe, MI, USA"
- Using full address
- Using a nearby landmark
- Verifying spelling

---

## Performance Issues

### Tool is running very slowly

**Solutions:**

1. **Skip email scraping** (much faster):
   ```bash
   python prospector.py "Seattle, WA" --no-emails
   ```

2. **Reduce search radius**:
   ```bash
   python prospector.py "Seattle, WA" --radius 2000
   ```

3. **Filter by business type** (fewer results):
   ```bash
   python prospector.py "Seattle, WA" --type restaurant
   ```

### Rate limiting / Too many requests

**Solution:**

The tool includes automatic rate limiting, but if you're hitting limits:

1. Edit `src/prospector/config.py`:
   ```python
   # Increase delay between requests
   REQUEST_TIMEOUT = 15  # Default is 10
   REQUESTS_PER_SECOND = 1  # Default is 2
   ```

2. Reduce search scope:
   - Smaller radius
   - More specific filters
   - Process areas separately

---

## Export Issues

### Error: Excel export fails

**Solution:**

Install openpyxl:
```bash
pip install openpyxl
```

Or use CSV/JSON instead:
```bash
python prospector.py "Seattle, WA" --format csv
```

### Error: CSV encoding issues (weird characters)

**Solution:**

Open CSV in Excel:
1. Use "Data" → "From Text/CSV"
2. Select UTF-8 encoding
3. Import the data

Or use Excel format instead:
```bash
python prospector.py "Seattle, WA" --format excel
```

---

## Windows-Specific Issues

### Error: `'python' is not recognized`

**Solution:**

Use `py` instead:
```bash
py prospector.py "Seattle, WA"
py -m pip install -r requirements.txt
```

### Error: Virtual environment activation fails

**Solution:**

In PowerShell:
```powershell
# Enable script execution (run as Administrator)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then activate
.\venv\Scripts\Activate.ps1
```

In Command Prompt:
```cmd
venv\Scripts\activate.bat
```

### Error: Path too long

**Solution:**

Enable long paths in Windows:
1. Open Registry Editor (regedit)
2. Navigate to: `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\FileSystem`
3. Set `LongPathsEnabled` to `1`

Or install in a shorter path:
```bash
cd C:\prospector
```

---

## Still Having Issues?

1. **Run the diagnostic test**:
   ```bash
   python test_connection.py
   ```

2. **Check your Python version**:
   ```bash
   python --version
   ```
   Should be 3.8 or higher, preferably 3.10 or 3.11

3. **Try a minimal test**:
   ```bash
   python prospector.py "Seattle, WA" --radius 1000 --no-emails --format csv
   ```

4. **Enable verbose error output**:
   - The tool already shows full stack traces
   - Check the error message carefully
   - Search for the specific error online

5. **Create a GitHub issue**:
   - Include the full error message
   - Include output from `python test_connection.py`
   - Include your Python version
   - Include your OS version

---

## Common Questions

**Q: How much does the Google Maps API cost?**

A: Free tier includes $200/month credit = approximately:
- 40,000 place details requests
- 40,000 geocoding requests

**Q: Can I use this without a Google Maps API key?**

A: No, the Google Maps API is required for business discovery.

**Q: Is web scraping legal?**

A: Scraping publicly available information is generally legal, but:
- Follow robots.txt
- Don't overwhelm servers
- Comply with website terms of service
- Follow local laws (GDPR, etc.)
- Use for legitimate purposes only

**Q: Can I run this on a schedule?**

A: Yes! Use cron (Linux/Mac) or Task Scheduler (Windows):

```bash
# Example cron job (daily at 9 AM)
0 9 * * * cd /path/to/prospector && python prospector.py "Seattle, WA" --format csv
```

**Q: How do I import results into my CRM?**

A: Most CRMs can import CSV files:
1. Export to CSV: `--format csv`
2. Open your CRM's import tool
3. Upload the CSV file
4. Map fields (Business Name → Company, Email → Email, etc.)

---

**Still stuck? The `test_connection.py` script is your best friend!**

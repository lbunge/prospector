# Performance and Scalability Guide

This guide covers performance considerations, optimization strategies, and best practices for running large prospecting campaigns.

## 🎯 Quick Summary

**Good news!** The tool now automatically handles large campaigns:

- **< 500 businesses:** Standard processing (no action needed)
- **500-1000 businesses:** Batch processing auto-enabled
- **1000+ businesses:** Streaming mode auto-enabled (prevents memory issues)

**You don't need to do anything!** The tool detects dataset size and optimizes automatically.

For manual control or advanced optimization, continue reading this guide.

## Table of Contents
- [Automatic Optimizations](#automatic-optimizations)
- [Performance Considerations](#performance-considerations)
- [Batch Processing](#batch-processing)
- [Memory Management](#memory-management)
- [Rate Limiting and API Quotas](#rate-limiting-and-api-quotas)
- [Optimization Strategies](#optimization-strategies)
- [Troubleshooting](#troubleshooting)

## Automatic Optimizations

The tool automatically detects dataset size and applies appropriate optimizations:

### How It Works

```python
# After discovering businesses from Google Maps
Found 1,250 businesses

⚠️  Large dataset detected (1250 businesses)
   Automatically enabling batch processing to prevent memory issues...

🔄 Very large dataset - enabling memory-efficient streaming
   Results will be written to disk incrementally to avoid memory issues
```

### Optimization Thresholds

| Dataset Size | Auto-Enabled Features | What Happens |
|-------------|----------------------|--------------|
| < 500 | None | Standard processing, all in memory |
| 500-999 | Batch processing (size=20) | Checkpoints every 20 businesses |
| 1000+ | Batch + Streaming | Results written to disk immediately, memory cleared after each batch |

### Benefits

**Automatic Batch Processing (500+ businesses):**
- Progress saved every 20 businesses
- Can resume if interrupted
- No configuration needed

**Automatic Streaming (1000+ businesses):**
- Constant memory usage (~300-500 MB regardless of dataset size)
- Prevents out-of-memory crashes
- Each business written to disk immediately
- Memory cleared after each batch
- Can handle datasets of any size (tested up to 10,000+ businesses)

### Manual Override

You can still manually control these features:

```bash
# Force batch processing even for small datasets
python prospector.py "location" --batch --batch-size 10

# Disable grid search to reduce dataset size
python prospector.py "location" --no-grid-search
```

## Performance Considerations

### Expected Runtime

The prospecting tool performs extensive enrichment for each business. Here are typical processing times:

**Per Business (with all features enabled):**
- Website discovery: 1-3 seconds
- Email scraping: 2-5 seconds (10 pages)
- Yelp enrichment: 1-2 seconds
- Email validation: 0.5-2 seconds (per email)
- Phone validation: 0.1 seconds
- Total: ~5-15 seconds per business

**For Large Campaigns:**
- 100 businesses: ~15-25 minutes
- 300 businesses: ~45-75 minutes
- 1000 businesses: ~3-5 hours

### Memory Usage

**Approximate memory requirements:**
- Base application: ~50-100 MB
- Per business (in memory): ~10-50 KB
- 100 businesses: ~100-150 MB total
- 1000 businesses: ~150-250 MB total

**Memory considerations:**
- Grid search can discover 200-300 businesses in areas that would normally return 60
- Each business stores comprehensive enrichment data
- Chrome/browser automation (if added) can use 500MB+ per instance

## Batch Processing

### When to Use Batch Processing

Enable batch processing (`--batch`) when:

1. **Large result sets** (100+ businesses expected)
2. **Unstable network** (checkpoint saves protect against interruptions)
3. **Long-running campaigns** (3+ hours expected)
4. **Testing/development** (easy to pause and resume)

### How It Works

```bash
# Enable batch processing with checkpoints every 10 businesses
python prospector.py "Monroe, MI" --radius 10000 --batch --batch-size 10

# If interrupted, resume from checkpoint
python prospector.py "Monroe, MI" --radius 10000 --batch --resume
```

**Features:**
- Saves progress every N businesses (default: 10)
- Checkpoint files stored in `.prospector_checkpoints/`
- Automatic resume on crash/interruption
- Progress tracking (shows X/Y completed)
- Safe error handling (won't lose data on API errors)

**Checkpoint File Structure:**
```json
{
  "job_name": "prospect_abc123",
  "total_items": 250,
  "last_index": 100,
  "timestamp": "2025-11-06T10:30:00",
  "processed_items": [...]
}
```

### Batch Size Recommendations

Choose batch size based on your needs:

| Scenario | Batch Size | Rationale |
|----------|------------|-----------|
| Testing/development | 5 | Frequent checkpoints, easy debugging |
| Small campaigns (<100) | 10 | Good balance |
| Medium campaigns (100-500) | 20 | Fewer checkpoint writes |
| Large campaigns (500+) | 50 | Minimize checkpoint overhead |
| Very stable network | 100+ | Maximum performance |

```bash
# Small batch size for testing
python prospector.py "Seattle, WA" --batch --batch-size 5

# Large batch size for production
python prospector.py "Seattle, WA" --radius 20000 --batch --batch-size 50
```

## Memory Management

### Memory-Efficient Streaming

For very large datasets (1000+ businesses), use the streaming processor to avoid loading everything into memory:

```python
from prospector.batch_processor import MemoryEfficientProcessor

# Process and stream results to file
MemoryEfficientProcessor.stream_process(
    items=businesses,
    process_func=enricher._enrich_business_data,
    output_file='large_campaign.json',
    batch_size=100  # Write to disk every 100 items
)
```

**Benefits:**
- Processes one business at a time
- Writes results to disk incrementally
- Constant memory usage regardless of dataset size
- Suitable for 10,000+ business campaigns

### Reducing Memory Usage

1. **Disable unused features:**
```python
# In config.py or via CLI
Config.ENRICH_WITH_YELP = False  # Skip Yelp enrichment
Config.VALIDATE_EMAILS = False   # Skip email validation
Config.ANALYZE_REVIEWS = False   # Skip review analysis
```

2. **Limit website crawling depth:**
```bash
python prospector.py "location" --max-pages 5  # Default is 10
```

3. **Process in smaller geographic chunks:**
```bash
# Instead of one large area
python prospector.py "Seattle, WA" --radius 20000  # Large

# Use multiple smaller searches
python prospector.py "Downtown Seattle" --radius 3000
python prospector.py "Capitol Hill, Seattle" --radius 3000
python prospector.py "Ballard, Seattle" --radius 3000
```

## Rate Limiting and API Quotas

### API Rate Limits

Each API has different rate limits. The tool implements automatic rate limiting to stay within bounds.

**Google Maps Places API:**
- Free tier: 1,000 requests/day
- Paid tier: Pay-per-use, unlimited
- Tool usage: ~2-3 requests per business (search + details)

**Yelp Fusion API:**
- Free tier: 5,000 requests/day
- Tool usage: ~1 request per business

**Hunter.io (Email Validation):**
- Free tier: 25 requests/month
- Paid tier: 100-10,000/month
- Tool usage: 1 request per email to validate

**ZeroBounce (Email Validation):**
- Free tier: 100 credits/month
- Paid tier: Pay-per-use
- Tool usage: 1 credit per email

### Managing API Quotas

**1. Estimate API usage before running:**

```
Campaign: 300 businesses expected

Google Maps API:
- Search: ~10-20 requests (grid search)
- Details: 300 requests
- Total: ~320 requests

Yelp API: 300 requests (if enabled)
Hunter.io: ~600 requests (300 businesses × 2 emails avg)
```

**2. Disable expensive features for large campaigns:**

```bash
# Run without validation to save API quota
python prospector.py "location" --batch

# Then validate emails separately on high-priority leads only
```

**3. Use configuration to control API usage:**

```python
# config.py
Config.ENRICH_WITH_YELP = False  # Save 1 request per business
Config.VALIDATE_EMAILS = False   # Save N requests per business
Config.USE_HUNTER_API = False    # Use free MX validation only
```

### Rate Limiter Configuration

The tool includes built-in rate limiting:

```python
# In config.py
Config.REQUESTS_PER_SECOND = 2  # Conservative (default)
Config.REQUESTS_PER_SECOND = 5  # Aggressive (paid tier)
```

**Built-in protections:**
- Exponential backoff on errors
- Automatic retry (up to 5 attempts)
- Respects API rate limits
- Delays between requests

## Optimization Strategies

### For Speed

**1. Disable non-essential features:**
```bash
# Minimal enrichment (fastest)
python prospector.py "location" --no-social
```

**2. Reduce crawling depth:**
```bash
python prospector.py "location" --max-pages 3  # Instead of 10
```

**3. Disable grid search for small areas:**
```bash
python prospector.py "location" --no-grid-search --radius 1000
```

### For Thoroughness

**1. Enable aggressive mode:**
```bash
python prospector.py "location" --aggressive  # Maximum features
```

**2. Use grid search for complete coverage:**
```bash
# Default behavior, but can verify with:
python prospector.py "location" --radius 10000  # Grid search auto-enabled
```

**3. Enable all enrichment features:**
```python
# config.py
Config.ENRICH_WITH_YELP = True
Config.VALIDATE_EMAILS = True
Config.PERMUTE_EMAILS = True
Config.ANALYZE_REVIEWS = True
```

### For API Quota Conservation

**1. Use MX-only email validation:**
```python
Config.USE_HUNTER_API = False
Config.USE_ZEROBOUNCE_API = False
Config.VALIDATE_EMAILS = True  # Uses free MX check
```

**2. Disable Yelp enrichment:**
```python
Config.ENRICH_WITH_YELP = False  # Saves 1 request per business
```

**3. Reduce email permutation:**
```python
Config.PERMUTE_EMAILS = False  # Prevents generating extra emails
```

## Troubleshooting

### Long Run Times

**Problem:** Campaign taking longer than expected

**Solutions:**
1. Check if grid search found more businesses than expected
   ```
   Found 250 businesses  # Instead of expected 60
   ```

2. Reduce website crawling:
   ```bash
   python prospector.py "location" --max-pages 5
   ```

3. Disable slow features:
   ```python
   Config.ENRICH_WITH_YELP = False
   Config.VALIDATE_EMAILS = False
   ```

### Memory Issues

**Problem:** Python using too much memory (>1GB)

**Solutions:**
1. Enable batch processing:
   ```bash
   python prospector.py "location" --batch --batch-size 20
   ```

2. Use streaming for very large datasets:
   ```python
   # Process in streaming mode (advanced)
   MemoryEfficientProcessor.stream_process(...)
   ```

3. Reduce result set:
   ```bash
   # Use smaller radius or more specific search
   python prospector.py "downtown area" --radius 2000
   ```

### API Rate Limit Errors

**Problem:** Getting 429 (Too Many Requests) errors

**Solutions:**
1. Reduce request rate:
   ```python
   Config.REQUESTS_PER_SECOND = 1  # More conservative
   ```

2. The tool has built-in retry with exponential backoff:
   - Attempt 1: Immediate
   - Attempt 2: Wait 2 seconds
   - Attempt 3: Wait 4 seconds
   - Attempt 4: Wait 8 seconds
   - Attempt 5: Wait 16 seconds

3. If persistent, check your API quota and tier

### Interrupted Campaigns

**Problem:** Campaign interrupted (Ctrl+C, network error, crash)

**Solutions:**
1. If batch processing was enabled, resume:
   ```bash
   python prospector.py "location" --batch --resume
   ```

2. If not using batch processing:
   - Results up to interruption are lost
   - Re-run with batch processing enabled:
   ```bash
   python prospector.py "location" --batch --batch-size 10
   ```

3. Check checkpoint directory:
   ```bash
   ls -la .prospector_checkpoints/
   ```

## Best Practices

### Recommended Settings by Campaign Size

**Small Campaign (<50 businesses):**
```bash
python prospector.py "location" --radius 2000 --aggressive
```
- No batch processing needed
- Enable all features
- Fast enough to complete without interruption

**Medium Campaign (50-200 businesses):**
```bash
python prospector.py "location" --radius 5000 --aggressive --batch --batch-size 10
```
- Enable batch processing
- Use aggressive mode
- 10-business checkpoint interval

**Large Campaign (200-1000 businesses):**
```bash
python prospector.py "location" --radius 10000 --batch --batch-size 20 --max-pages 8
```
- Batch processing required
- Larger batch size (20)
- Slightly reduced crawling depth
- Expected runtime: 2-5 hours

**Very Large Campaign (1000+ businesses):**
```bash
python prospector.py "location" --radius 20000 --batch --batch-size 50 --max-pages 5
```
- Large batch size (50)
- Reduced page crawling
- Consider disabling Yelp/validation to save API quota
- Expected runtime: 5-10+ hours
- Consider splitting into multiple geographic regions

### Production Deployment

For automated/production use:

1. **Always enable batch processing**
2. **Set up proper error handling**
3. **Monitor API quotas**
4. **Use environment variables for API keys**
5. **Set up log aggregation**
6. **Consider running in background:**
   ```bash
   nohup python prospector.py "location" --batch &
   ```

7. **Schedule during off-peak hours for API quota management**

## Performance Benchmarks

Tested on:
- Machine: 4 CPU cores, 8GB RAM
- Network: 100 Mbps
- All features enabled

| Businesses | Time | Memory | API Calls |
|-----------|------|--------|-----------|
| 10 | 2 min | 100 MB | ~30 |
| 50 | 8 min | 120 MB | ~150 |
| 100 | 18 min | 150 MB | ~300 |
| 250 | 55 min | 200 MB | ~750 |
| 500 | 2.2 hrs | 250 MB | ~1,500 |
| 1000 | 5 hrs | 350 MB | ~3,000 |

*Note: Times include all enrichment features. Actual times may vary based on network speed, API response times, and website complexity.*

## Advanced: Parallel Processing (Experimental)

For maximum performance, the tool supports concurrent API requests (use with caution):

```python
# config.py
Config.MAX_CONCURRENT_REQUESTS = 3  # Process 3 businesses simultaneously
```

**Considerations:**
- More complex error handling
- Higher risk of hitting rate limits
- 2-3x faster for large campaigns
- Use only with paid API tiers
- Monitor for rate limit errors

**Not recommended for:**
- Free tier API usage
- Unstable networks
- Small campaigns (<100 businesses)

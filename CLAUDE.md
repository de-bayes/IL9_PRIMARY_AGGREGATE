# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**IL9Cast** - Illinois 9th District Democratic Primary Forecast aggregator for the March 17, 2026 primary. Aggregates prediction market data from Manifold Markets and Kalshi every minute using a weighted formula, stores historical snapshots, and serves an interactive web dashboard.

## Development Commands

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run development server (with auto-reload)
python app.py

# Run production server locally
gunicorn app:app --preload
```

### Data Management
```bash
# Manually repair corrupted JSON data
python repair_data.py

# View recent snapshots
tail -n 50 data/historical_snapshots.json

# Check data file size
ls -lh data/historical_snapshots.json
```

### Deployment
```bash
# Railway deployment (automatic on git push)
git push origin main

# Manual Railway CLI deploy
railway up
```

## Architecture

### Application Structure

**Backend:** Flask 2.3.2 + APScheduler for background data collection
- `app.py` (611 lines) - Main Flask app with routes, API endpoints, and data collection scheduler
- Background task runs every 60 seconds to fetch and aggregate market data
- Production: Gunicorn with `--preload` flag to ensure single scheduler instance

**Frontend:** Server-side Jinja2 templates + Chart.js visualization
- `templates/landing.html` - Homepage hero section
- `templates/markets.html` - Live prediction market aggregation display
- `templates/odds.html` - Model visualization page (in development)
- `static/style.css` (2435 lines) - Complete styling with dark mode toggle

### Data Collection Pipeline

**Every 60 seconds:**
1. Fetch from Manifold API (`/v0/slug/who-will-win-the-democratic-primary-RZdcps6dL9`)
2. Fetch from Kalshi API (`/trade-api/v2/markets?series_ticker=KXIL9D&status=open`)
3. Normalize candidate names across platforms
4. Aggregate using weighted formula:
   - Manifold: 40%
   - Kalshi last price: 42%
   - Kalshi midpoint (bid/ask): 12%
   - Kalshi liquidity-adjusted: 6%
5. Apply soft normalization (30% strength toward sum=100%)
6. Create snapshot object with timestamp
7. Atomically write to `data/historical_snapshots.json`

### Data Storage

**Critical:** All historical data stored in `/data/historical_snapshots.jsonl` (JSONL format)

- **Format:** JSON Lines (one snapshot per line, newline-delimited)
- **Current Size:** ~2.4MB, 5,565+ snapshots
- **Location:** Railway persistent volume mounted at `/app/data`
- **Git Tracking:** Runtime data excluded, `seed_snapshots.json` tracked for initialization

**Why JSONL?**
- Append-only writes (no need to read/rewrite entire file)
- Corruption-proof (each line is self-contained)
- 35% space savings vs JSON array
- Prevents "Extra data" errors from incomplete writes

**Snapshot Structure (one per line):**
```json
{"candidates": [{"name": "Daniel Biss", "probability": 63.6, "hasKalshi": true}, {"name": "Kat Abughazaleh", "probability": 18.8, "hasKalshi": true}], "timestamp": "2026-01-29T19:45:30Z"}
```

**Legacy JSON Support:**
- Old `historical_snapshots.json` automatically migrated to JSONL on first run
- Backups preserved in `data/*.pre-jsonl-backup.*` files

### Data Reliability Features

**JSONL Append-Only Writes:**
- `append_snapshot_jsonl()` atomically appends single line
- No need to read entire file or risk corruption
- Each line is self-contained and parseable independently
- Automatic migration from legacy JSON format

**Deduplication:**
- Historical data cleaned of 175 millisecond-duplicate snapshots (Jan 2026)
- Use `deduplicate_aggressive.py` to remove duplicates from JSONL files
- Keeps first snapshot when multiple exist within 1 second

**Helper Functions:**
- `read_snapshots_jsonl()` - Load all snapshots from JSONL
- `count_snapshots_jsonl()` - Count snapshots without loading all into memory
- `append_snapshot_jsonl()` - Atomic append operation

## API Endpoints

### Public JSON APIs
- `GET /api/manifold` - Proxy to Manifold market data
- `GET /api/kalshi` - Proxy to Kalshi market data
- `GET /api/snapshots` - Historical aggregated snapshots (full dataset)
- `POST /api/snapshot` - Save new snapshot (internal use)

### Mock Endpoints (Development)
- `GET /api/forecast` - Hardcoded current probabilities with randomization
- `GET /api/timeline` - Generated 90-day polling trends

## Deployment Configuration

**Railway (Primary Platform):**
- Builder: NIXPACKS
- Start: `gunicorn app:app --preload`
- Health check: `GET /` with 100s timeout
- Persistent volume: `/app/data` for historical snapshots
- Auto-restart: Up to 10 retries on failure

**Environment:**
- Port: 8000 (default) or `$PORT`
- Debug: Auto-detected (disabled if `FLASK_ENV=production`)

## Important Technical Details

### Background Task Scheduling

The scheduler runs in a dedicated daemon thread when using Gunicorn:
```python
if 'gunicorn' in sys.argv[0]:
    # Start scheduler in background thread to avoid duplicate schedulers
```

This prevents multiple worker processes from creating duplicate collection jobs.

### Name Normalization

Candidate name standardization critical for cross-platform aggregation:
- Removes "Wil"/"Will" prefixes
- Strips "Goczkowski" suffix variations
- Handles "Kat"/"Katheryn" variations
- Case-insensitive matching

### Timezone Reset Migration

Markers in `data/.timezone_reset_v*` prevent repeated one-time data migrations. Do not delete these files.

## Common Issues

### JSON Corruption Recovery
If `historical_snapshots.json` becomes corrupted:
1. Automatic repair runs on next collection cycle
2. Manual repair: `python repair_data.py`
3. Backup created automatically before repair

### Data Loss Prevention
- Never delete `data/historical_snapshots.json` in production
- Railway persistent volume ensures data survives container restarts
- Seed file (`seed_snapshots.json`) only for initialization, not ongoing backup

### Double-Entry Prevention
Fixed in recent commits. Historical data may contain duplicates that should be deduplicated by timestamp during analysis.

## File Paths Reference

- Main app: `app.py`
- Data collection: `app.py:collect_market_data()`
- Name normalization: `app.py:normalize_candidate_name()`, `clean_candidate_name()`
- JSONL operations: `app.py:read_snapshots_jsonl()`, `append_snapshot_jsonl()`, `count_snapshots_jsonl()`
- Deduplication script: `deduplicate_aggressive.py`
- Data analysis script: `data_recovery.py`
- Conversion script: `convert_to_jsonl.py`
- Historical data (current): `data/historical_snapshots.jsonl`
- Historical data (legacy): `data/historical_snapshots.json` (auto-migrated to JSONL)
- Seed/backup: `data/seed_snapshots.json`

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

This is a web scraper application for Karnataka DTE (Directorate of Technical Education) circulars with automated deployment:

- **Python Scraper** (`scraper.py`): Main scraping logic using requests + BeautifulSoup
- **Frontend** (`index.html`, `script.js`, `styles.css`): Static web app to display scraped data
- **GitHub Actions** (`.github/workflows/scrape-circulars.yml`): Automated scraping every 30 minutes
- **GitHub Pages**: Serves the static web interface

### Key Components

1. **CircularScraper class** (`scraper.py:10-234`): Core scraping functionality
   - Scrapes from two URLs: Departmental Circulars and DVP Circulars
   - Validates entries using `is_valid_circular()` to filter spam/unwanted content
   - Handles different table structures for different page types
   - Saves to `circulars.json` with metadata

2. **Data Flow**: GitHub Actions → Python scraper → JSON output → GitHub Pages deployment

3. **Frontend Features**: Search, filtering by category, dark mode, PDF export

## Development Commands

### Local Testing
```bash
# Install dependencies
pip install -r requirements.txt

# Run the scraper manually
python scraper.py
```


### GitHub Actions
- Scraper runs automatically every 30 minutes via cron schedule
- Manual trigger available via workflow_dispatch
- Commits updated `circulars.json` and deploys to GitHub Pages

## Data Structure

The scraper outputs to `circulars.json` with this structure:
```json
{
  "last_updated": "ISO timestamp",
  "total_circulars": number,
  "circulars": [
    {
      "date": "string",
      "circular_no": "string", 
      "description": "string",
      "download_link": "URL or empty",
      "source_url": "source page URL",
      "scraped_at": "ISO timestamp"
    }
  ]
}
```

## Important Implementation Details

- **Anti-spam filtering**: `is_valid_circular()` method filters out unwanted domains (atoall.com, webinsight, etc.)
- **Duplicate handling**: Removes duplicates based on `(circular_no, description)` tuple
- **Date parsing**: Handles multiple date formats (DD/MM/YYYY, DD-MM-YYYY, etc.)
- **Link handling**: Converts relative URLs to absolute URLs for download links
- **Rate limiting**: 2-second delay between URL requests to be respectful to server

## URL Sources
- Departmental: `https://dtek.karnataka.gov.in/info-4/Departmental+Circulars/kn`
- DVP: `https://dtek.karnataka.gov.in/page/Circulars/DVP/kn`

## Customization Notes

- To change scraping frequency: Edit cron schedule in `.github/workflows/scrape-circulars.yml:6`
- To add new data sources: Add URLs to `self.urls` in `CircularScraper.__init__()`
- DVP pages use 5-column table structure vs 3-column for Departmental pages
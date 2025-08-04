# Karnataka DTE Circulars Scraper

A web application that automatically scrapes and displays circulars from Karnataka DTE (Directorate of Technical Education) website.

## Features

- **Automated Scraping**: Scrapes circulars every 30 minutes using GitHub Actions
- **Responsive Web Interface**: Clean, modern UI that works on all devices
- **Real-time Search**: Filter circulars by description, number, source, or date
- **Download Links**: Direct access to PDF downloads where available
- **GitHub Pages Deployment**: Automatically deployed and updated

## Live Demo

The application is deployed at: [Your GitHub Pages URL]

## Data Sources

- [Departmental Circulars](https://dtek.karnataka.gov.in/info-4/Departmental+Circulars/kn)
- [DVP Circulars](https://dtek.karnataka.gov.in/page/Circulars/DVP/kn)

## Setup Instructions

### 1. Fork/Clone this repository

```bash
git clone https://github.com/yourusername/dte-scraper.git
cd dte-scraper
```

### 2. Enable GitHub Actions

1. Go to your repository settings
2. Navigate to Actions > General
3. Enable "Allow all actions and reusable workflows"

### 3. Enable GitHub Pages

1. Go to repository Settings > Pages
2. Set Source to "GitHub Actions"
3. The site will be available at `https://yourusername.github.io/dte-scraper`

### 4. Manual Testing

To test the scraper locally:

```bash
pip install -r requirements.txt
python scraper.py
```

This will create a `circulars.json` file with the scraped data.

## File Structure

```
dte-scraper/
├── .github/
│   └── workflows/
│       └── scrape-circulars.yml    # GitHub Actions workflow
├── index.html                      # Main web interface  
├── styles.css                      # Styling
├── script.js                       # Frontend JavaScript
├── scraper.py                      # Python scraper
├── requirements.txt                # Python dependencies
├── circulars.json                  # Generated data file
└── README.md                       # This file
```

## How It Works

1. **GitHub Actions** runs the Python scraper every 30 minutes
2. **Python scraper** fetches data from DTE Karnataka website
3. **Data** is saved to `circulars.json`
4. **GitHub Pages** automatically deploys the updated site
5. **Web interface** loads and displays the circular data

## Customization

### Change Scraping Frequency

Edit `.github/workflows/scrape-circulars.yml`:

```yaml
schedule:
  - cron: '0 */2 * * *'  # Every 2 hours instead of 30 minutes
```

### Add More Data Sources

Edit `scraper.py` and add URLs to the `urls` list:

```python
self.urls = [
    "https://dtek.karnataka.gov.in/info-4/Departmental+Circulars/kn",
    "https://dtek.karnataka.gov.in/page/Circulars/DVP/kn",
    "https://your-additional-url.com"
]
```

## Technical Details

- **Backend**: Python with requests and BeautifulSoup
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Deployment**: GitHub Pages with GitHub Actions
- **Data Format**: JSON
- **Update Frequency**: Every 30 minutes

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test locally
5. Submit a pull request

## License

This project is open source and available under the MIT License.

## Disclaimer

This tool is for educational and informational purposes only. Please respect the Karnataka DTE website's terms of service and use responsibly.
import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
import time
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import signal
import sys
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class CircularScraper:
    def __init__(self):
        self.urls = [
            "https://dtek.karnataka.gov.in/info-4/Departmental+Circulars/kn",
            "https://dtek.karnataka.gov.in/page/Circulars/DVP/kn"
        ]
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Setup session with conservative retry strategy for GitHub Actions
        self.session = requests.Session()
        retry_strategy = Retry(
            total=2,  # Reduced from 5 to 2
            backoff_factor=1,  # Reduced from 2 to 1 
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.headers.update(self.headers)
        
        # Execution tracking
        self.start_time = datetime.now()
        self.max_execution_time = 240  # 4 minutes max execution time
    
    def is_valid_circular(self, date, circular_no, description, download_link):
        """Validate if the circular entry is legitimate"""
        # Filter out unwanted websites and invalid entries
        unwanted_domains = [
            'atoall.com', 
            'webinsight.cs.washington.edu',
            'satogo.com',
            'javascript:'
        ]
        
        # Check if download link contains unwanted domains
        if download_link:
            for domain in unwanted_domains:
                if domain in download_link.lower():
                    return False
        
        # Check if circular_no contains unwanted values
        if circular_no:
            unwanted_circular_nos = ['atoall', 'webanywhere', 'system access to go']
            if circular_no.lower() in unwanted_circular_nos:
                return False
        
        # Check if description indicates external website
        if description:
            unwanted_descriptions = [
                'external website that opens in a new window',
                'javascript:',
                'webanywhere',
                'system access'
            ]
            desc_lower = description.lower()
            for unwanted in unwanted_descriptions:
                if unwanted in desc_lower:
                    return False
        
        # Must have meaningful date (allow single digits for day/month)
        if not date or len(date.strip()) <= 1:
            return False
        
        # Must have some description
        if not description or len(description.strip()) < 5:
            return False
            
        return True
        
    def check_execution_time(self):
        """Check if we've exceeded maximum execution time"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        if elapsed > self.max_execution_time:
            print(f"Maximum execution time ({self.max_execution_time}s) exceeded. Stopping.")
            return True
        return False
    
    def scrape_circulars(self, url):
        # Check execution time before starting
        if self.check_execution_time():
            print(f"Skipping {url} due to time limit")
            return []
            
        max_attempts = 2  # Reduced from 3 to 2
        for attempt in range(max_attempts):
            try:
                print(f"Attempt {attempt + 1}/{max_attempts} for {url}")
                response = self.session.get(url, timeout=20, verify=False)  # Reduced from 45s to 20s
                response.raise_for_status()
                break
            except requests.exceptions.Timeout:
                print(f"Timeout on attempt {attempt + 1} for {url}")
                if attempt < max_attempts - 1:
                    time.sleep(5)  # Fixed 5s delay instead of exponential
                    continue
                else:
                    print(f"All attempts failed for {url} due to timeout")
                    return []
            except requests.exceptions.ConnectionError as e:
                print(f"Connection error on attempt {attempt + 1} for {url}: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(5)  # Fixed 5s delay instead of exponential
                    continue
                else:
                    print(f"All attempts failed for {url} due to connection error")
                    return []
            except Exception as e:
                print(f"Unexpected error on attempt {attempt + 1} for {url}: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(5)  # Fixed 5s delay
                    continue
                else:
                    print(f"All attempts failed for {url} due to unexpected error")
                    return []
        
        try:
            
            soup = BeautifulSoup(response.content, 'html.parser')
            circulars = []
            
            # Find table rows containing circular data
            table_rows = soup.find_all('tr')
            
            for row in table_rows[1:]:  # Skip header row
                cells = row.find_all('td')
                if len(cells) >= 3:
                    # Handle different page structures
                    if "DVP" in url:
                        # DVP page has a specific 5-column structure: Serial, Date, Circular_No, Description, Download_Link
                        if len(cells) >= 5:
                            try:
                                serial = cells[0].get_text(strip=True) if cells[0] else ""
                                date = cells[1].get_text(strip=True) if cells[1] else ""
                                circular_no = cells[2].get_text(strip=True) if cells[2] else ""
                                description = cells[2].get_text(strip=True) if cells[2] else ""  # Description is in cell 2 for DVP
                                
                                # DVP rows typically have meaningful content in all cells
                                # Skip header rows and empty rows
                                if (len(description) > 15 and  # DVP descriptions are longer
                                    not serial.lower() in ['sl', 'serial', 'ಕ್ರಮ', 'ಕ್ರಮಾಂಕ'] and
                                    not date.lower() in ['date', 'ದಿನಾಂಕ'] and
                                    len(date) > 5):  # DVP dates are longer
                                    pass  # This is a valid DVP row
                                else:
                                    continue  # Skip invalid rows
                            except:
                                continue
                        else:
                            # If less than 5 columns, skip (DVP always has 5 columns)
                            continue
                    else:
                        # Departmental page format
                        date = cells[0].get_text(strip=True) if cells[0] else ""
                        circular_no = cells[1].get_text(strip=True) if cells[1] else ""
                        description = cells[2].get_text(strip=True) if cells[2] else ""
                    
                    # Look for download links - check all cells for links
                    download_link = ""
                    for i, cell in enumerate(cells):
                        link_element = cell.find('a')
                        if link_element and link_element.get('href'):
                            href = link_element.get('href')
                            # Skip unwanted links
                            if not any(unwanted in href.lower() for unwanted in ['atoall.com', 'javascript:', 'webinsight', 'satogo']):
                                if href.startswith('/'):
                                    download_link = "https://dtek.karnataka.gov.in" + href
                                elif href.startswith('http'):
                                    download_link = href
                                break
                    
                    # For DVP pages, also check specific cells for links
                    if "DVP" in url and not download_link:
                        # Check last column for links (usually the download column)
                        if len(cells) >= 5:
                            link_cell = cells[4]  # 5th column often has the link
                        elif len(cells) >= 4:
                            link_cell = cells[3]  # 4th column
                        else:
                            link_cell = cells[2]  # Fallback to description column
                        
                        link_in_cell = link_cell.find('a')
                        if link_in_cell and link_in_cell.get('href'):
                            href = link_in_cell.get('href')
                            if not any(unwanted in href.lower() for unwanted in ['atoall.com', 'javascript:', 'webinsight', 'satogo']):
                                if href.startswith('/'):
                                    download_link = "https://dtek.karnataka.gov.in" + href
                                elif href.startswith('http'):
                                    download_link = href
                        
                        # Also check description cell if no link found yet
                        if not download_link:
                            desc_cell = cells[3] if len(cells) >= 5 else cells[2]
                            link_in_desc = desc_cell.find('a')
                            if link_in_desc and link_in_desc.get('href'):
                                href = link_in_desc.get('href')
                                if not any(unwanted in href.lower() for unwanted in ['atoall.com', 'javascript:', 'webinsight', 'satogo']):
                                    if href.startswith('/'):
                                        download_link = "https://dtek.karnataka.gov.in" + href
                                    elif href.startswith('http'):
                                        download_link = href
                    
                    # Filter out unwanted entries
                    if self.is_valid_circular(date, circular_no, description, download_link):
                        circulars.append({
                            'date': date,
                            'circular_no': circular_no,
                            'description': description,
                            'download_link': download_link,
                            'source_url': url,
                            'scraped_at': datetime.now().isoformat()
                        })
            
            return circulars
            
        except Exception as e:
            print(f"Error scraping {url}: {str(e)}")
            return []
    
    def scrape_all(self):
        all_circulars = []
        
        for url in self.urls:
            # Check execution time before each URL
            if self.check_execution_time():
                print("Stopping scraping due to time limit")
                break
                
            print(f"Scraping {url}...")
            circulars = self.scrape_circulars(url)
            all_circulars.extend(circulars)
            print(f"Found {len(circulars)} circulars from {url}")
            time.sleep(2)  # Reduced from 5s to 2s
        
        # Remove duplicates based on circular_no and description
        seen = set()
        unique_circulars = []
        for circular in all_circulars:
            key = (circular['circular_no'], circular['description'])
            if key not in seen:
                seen.add(key)
                unique_circulars.append(circular)
        
        return unique_circulars
    
    def load_existing_data(self, filename='circulars.json'):
        """Load existing circulars data if available"""
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('circulars', [])
        except Exception as e:
            print(f"Error loading existing data: {e}")
        return []
    
    def save_to_json(self, circulars, filename='circulars.json'):
        # Sort by date (newest first) and limit to 50 most recent
        def parse_date(date_str):
            try:
                # Handle various date formats
                date_str = date_str.strip()
                
                # DD/MM/YYYY or DD-MM-YYYY
                if '/' in date_str:
                    parts = date_str.split('/')
                    if len(parts) == 3:
                        return datetime(int(parts[2]), int(parts[1]), int(parts[0]))
                elif '-' in date_str:
                    parts = date_str.split('-')
                    if len(parts) == 3:
                        # Handle DD-MM-YYYY
                        if len(parts[2]) == 4:
                            return datetime(int(parts[2]), int(parts[1]), int(parts[0]))
                        # Handle YYYY-MM-DD
                        elif len(parts[0]) == 4:
                            return datetime(int(parts[0]), int(parts[1]), int(parts[2]))
                
                # Fallback - return very old date for unparseable dates
                return datetime(1900, 1, 1)
            except:
                return datetime(1900, 1, 1)
        
        # Sort by parsed date, newest first
        circulars.sort(key=lambda x: parse_date(x['date']), reverse=True)
        
        # Limit to last 50 circulars
        circulars = circulars[:50]
        
        data = {
            'last_updated': datetime.now().isoformat(),
            'total_circulars': len(circulars),
            'circulars': circulars
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"Saved {len(circulars)} circulars to {filename}")

def signal_handler(signum, frame):
    print(f"\nReceived signal {signum}. Gracefully shutting down...")
    sys.exit(1)

def main():
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    print(f"Starting scraper with {240}s time limit...")
    scraper = CircularScraper()
    circulars = scraper.scrape_all()
    
    elapsed_time = (datetime.now() - scraper.start_time).total_seconds()
    print(f"Scraping completed in {elapsed_time:.1f}s")
    
    # If no new circulars were found, try to preserve existing data
    if not circulars:
        print("No new circulars found. Checking for existing data...")
        existing_circulars = scraper.load_existing_data()
        if existing_circulars:
            print(f"Preserving {len(existing_circulars)} existing circulars")
            # Update timestamp but keep existing data
            data = {
                'last_updated': datetime.now().isoformat(),
                'total_circulars': len(existing_circulars),
                'circulars': existing_circulars,
                'note': 'Scraping failed - preserved existing data'
            }
            with open('circulars.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Preserved existing data with {len(existing_circulars)} circulars")
            return
        else:
            print("No existing data found. Creating empty file.")
    
    scraper.save_to_json(circulars)

if __name__ == "__main__":
    main()
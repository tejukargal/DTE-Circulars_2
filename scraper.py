import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
import time
import signal
import sys
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3
import ssl
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class CircularScraper:
    def __init__(self):
        self.is_github_actions = os.getenv('GITHUB_ACTIONS') == 'true'
        
        self.urls = [
            "https://dtek.karnataka.gov.in/info-4/Departmental+Circulars/kn",
            "https://dtek.karnataka.gov.in/page/Circulars/DVP/kn"
        ]
        
        # Enhanced session with multiple fallback user agents and headers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        })
        
        # Enhanced retry strategy with exponential backoff
        retry_strategy = Retry(
            total=5,  # More retries
            backoff_factor=2,  # Exponential backoff: 2, 4, 8, 16 seconds
            status_forcelist=[429, 500, 502, 503, 504, 520, 521, 522, 523, 524],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
            raise_on_redirect=False,
            raise_on_status=False
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.start_time = datetime.now()
        self.max_execution_time = 300 if self.is_github_actions else 600  # 5 min for GHA, 10 min local
    
    
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
        elapsed = (datetime.now() - self.start_time).total_seconds()
        if elapsed > self.max_execution_time:
            print(f"Time limit ({self.max_execution_time}s) exceeded. Stopping.")
            return True
        return False
    
    def fetch_url(self, url, max_attempts=3):
        """Enhanced URL fetching with multiple fallback strategies"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0'
        ]
        
        for attempt in range(max_attempts):
            try:
                # Use different user agent for each attempt
                if attempt < len(user_agents):
                    self.session.headers['User-Agent'] = user_agents[attempt]
                
                # Progressive timeout increases: (30,120), (45,150), (60,180)
                base_connect = 30 if self.is_github_actions else 20
                base_read = 120 if self.is_github_actions else 90
                connect_timeout = base_connect + (attempt * 15)
                read_timeout = base_read + (attempt * 30)
                timeout = (connect_timeout, read_timeout)
                
                print(f"Attempt {attempt + 1}/{max_attempts} for {url} with timeout {timeout}")
                
                # Try with SSL verification disabled and multiple fallback options
                response = self.session.get(
                    url, 
                    timeout=timeout, 
                    verify=False, 
                    allow_redirects=True,
                    stream=False
                )
                
                if response.status_code == 200:
                    print(f"Success on attempt {attempt + 1}")
                    return response
                else:
                    print(f"HTTP {response.status_code} on attempt {attempt + 1}")
                    if attempt < max_attempts - 1:
                        time.sleep(3 * (attempt + 1))  # Progressive delay
                        
            except requests.exceptions.SSLError as e:
                print(f"SSL error on attempt {attempt + 1}: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(5 * (attempt + 1))
                    
            except requests.exceptions.ConnectTimeout as e:
                print(f"Connection timeout on attempt {attempt + 1}: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(10 * (attempt + 1))  # Longer delay for connection timeouts
                    
            except requests.exceptions.ReadTimeout as e:
                print(f"Read timeout on attempt {attempt + 1}: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(5 * (attempt + 1))
                    
            except requests.exceptions.ConnectionError as e:
                print(f"Connection error on attempt {attempt + 1}: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(8 * (attempt + 1))
                    
            except Exception as e:
                print(f"Unexpected error on attempt {attempt + 1}: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(5 * (attempt + 1))
        
        print(f"All {max_attempts} attempts failed for {url}")
        return None
    
    def scrape_circulars(self, url):
        if self.check_execution_time():
            print(f"Skipping {url} due to time limit")
            return []
        
        print(f"Scraping {url}...")
        response = self.fetch_url(url)
        
        if not response:
            print(f"Failed to fetch {url}")
            return []
        
        try:
            soup = BeautifulSoup(response.content, 'html.parser')
            circulars = []
            
            # Find table rows containing circular data
            table_rows = soup.find_all('tr')
            
            # Process maximum 50 rows for speed in GitHub Actions
            max_rows = 50 if self.is_github_actions else 100
            rows_to_process = table_rows[1:max_rows+1]  # Skip header row
            
            for row in rows_to_process:
                cells = row.find_all('td')
                if len(cells) >= 3:
                    # Simple extraction based on URL type
                    if "DVP" in url and len(cells) >= 4:
                        # DVP format: Skip serial, use date, circular_no, description
                        date = cells[1].get_text(strip=True)
                        circular_no = cells[2].get_text(strip=True)
                        description = cells[3].get_text(strip=True)
                        
                        # Skip header rows
                        if date.lower() in ['date', 'ದಿನಾಂಕ'] or len(description) < 10:
                            continue
                    else:
                        # Departmental format: date, circular_no, description
                        date = cells[0].get_text(strip=True)
                        circular_no = cells[1].get_text(strip=True)
                        description = cells[2].get_text(strip=True)
                    
                    # Simple link extraction
                    download_link = ""
                    for cell in cells:
                        link = cell.find('a')
                        if link and link.get('href'):
                            href = link.get('href')
                            if not any(bad in href for bad in ['atoall.com', 'javascript:', 'webinsight']):
                                if href.startswith('/'):
                                    download_link = "https://dtek.karnataka.gov.in" + href
                                elif href.startswith('http'):
                                    download_link = href
                                break
                    
                    # Quick validation and add
                    if (date and description and len(description) > 5 and 
                        len(date) > 4 and self.is_valid_circular(date, circular_no, description, download_link)):
                        circulars.append({
                            'date': date,
                            'circular_no': circular_no,
                            'description': description,
                            'download_link': download_link,
                            'source_url': url,
                            'scraped_at': datetime.now().isoformat()
                        })
            
            print(f"Successfully extracted {len(circulars)} valid circulars")
            return circulars
            
        except Exception as e:
            print(f"Error scraping {url}: {str(e)}")
            return []
    
    def scrape_all(self):
        all_circulars = []
        
        # Always use sequential scraping for reliability
        for url in self.urls:
            if self.check_execution_time():
                print("Time limit reached, stopping")
                break
                
            circulars = self.scrape_circulars(url)
            all_circulars.extend(circulars)
            print(f"Found {len(circulars)} circulars from {url}")
            
            # Small delay between URLs
            if len(self.urls) > 1:
                time.sleep(2)
        
        # Remove duplicates based on circular_no and description
        seen = set()
        unique_circulars = []
        for circular in all_circulars:
            key = (circular['circular_no'], circular['description'])
            if key not in seen:
                seen.add(key)
                unique_circulars.append(circular)
        
        print(f"Total unique circulars after deduplication: {len(unique_circulars)}")
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
    
    def merge_with_existing_data(self, new_circulars, filename='circulars.json'):
        """Merge new circulars with existing data and return combined list"""
        existing_circulars = self.load_existing_data(filename)
        
        # Combine new and existing circulars
        all_circulars = new_circulars + existing_circulars
        
        # Remove duplicates based on circular_no and description
        seen = set()
        unique_circulars = []
        for circular in all_circulars:
            key = (circular.get('circular_no', ''), circular.get('description', ''))
            if key not in seen and key != ('', ''):
                seen.add(key)
                unique_circulars.append(circular)
        
        print(f"Merged {len(new_circulars)} new + {len(existing_circulars)} existing = {len(unique_circulars)} unique circulars")
        return unique_circulars
    
    def save_to_json(self, circulars, filename='circulars.json'):
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
        
        # Merge with existing data first
        all_circulars = self.merge_with_existing_data(circulars, filename)
        
        # Sort by parsed date, newest first
        all_circulars.sort(key=lambda x: parse_date(x['date']), reverse=True)
        
        # Ensure balanced representation from both sources
        dept_circulars = [c for c in all_circulars if 'Departmental' in c['source_url']]
        dvp_circulars = [c for c in all_circulars if 'DVP' in c['source_url']]
        
        # Take top 200 from each source to ensure representation
        selected_circulars = dept_circulars[:200] + dvp_circulars[:200]
        
        # Sort combined selection by date again
        selected_circulars.sort(key=lambda x: parse_date(x['date']), reverse=True)
        
        # Take top 400 total, but this ensures we have mix from both sources
        final_circulars = selected_circulars[:400]
        
        # Count by source for reporting
        final_dept_count = sum(1 for c in final_circulars if 'Departmental' in c['source_url'])
        final_dvp_count = sum(1 for c in final_circulars if 'DVP' in c['source_url'])
        
        data = {
            'last_updated': datetime.now().isoformat(),
            'total_circulars': len(final_circulars),
            'circulars': final_circulars,
            'scraping_status': 'success' if circulars else 'partial',
            'source_breakdown': {
                'departmental': final_dept_count,
                'dvp': final_dvp_count
            }
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"Saved {len(final_circulars)} total circulars to {filename}")
        print(f"  - Departmental: {final_dept_count}")
        print(f"  - DVP: {final_dvp_count}")

def signal_handler(signum, frame):
    print(f"\nReceived signal {signum}. Gracefully shutting down...")
    sys.exit(1)

def main():
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    scraper = CircularScraper()
    time_limit = scraper.max_execution_time
    env_info = "GitHub Actions" if scraper.is_github_actions else "local"
    print(f"Starting enhanced scraper with {time_limit}s time limit ({env_info} environment)...")
    
    # Try scraping
    circulars = scraper.scrape_all()
    
    elapsed_time = (datetime.now() - scraper.start_time).total_seconds()
    print(f"Scraping completed in {elapsed_time:.1f}s")
    
    # Always save, even if we got partial results
    if circulars:
        print(f"Successfully scraped {len(circulars)} new circulars")
        scraper.save_to_json(circulars)
    else:
        print("No new circulars found this run.")
        # Still try to merge with existing and update timestamp
        existing_circulars = scraper.load_existing_data()
        if existing_circulars:
            print(f"Maintaining {len(existing_circulars)} existing circulars")
            scraper.save_to_json([])  # This will merge with existing
        else:
            print("No existing data found either. Creating minimal file.")
            data = {
                'last_updated': datetime.now().isoformat(),
                'total_circulars': 0,
                'circulars': [],
                'scraping_status': 'failed',
                'note': 'All scraping attempts failed'
            }
            with open('circulars.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    
    print("Scraper execution completed.")

if __name__ == "__main__":
    main()
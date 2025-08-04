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
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class CircularScraper:
    def __init__(self):
        # Detect GitHub Actions environment first
        self.is_github_actions = os.getenv('GITHUB_ACTIONS') == 'true'
        
        self.urls = [
            "https://dtek.karnataka.gov.in/info-4/Departmental+Circulars/kn",
            "https://dtek.karnataka.gov.in/page/Circulars/DVP/kn"
        ]
        
        # Multiple User-Agent strings for rotation
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
        # Session pool for parallel requests
        self.sessions = []
        self.lock = threading.Lock()
        
        # Execution tracking
        self.start_time = datetime.now()
        # Strict timeout for GitHub Actions (under 5 min limit)
        self.max_execution_time = 240 if self.is_github_actions else 900  # 4 min for GHA, 15 min local
        
        # Initialize session pool
        self._init_sessions()
    
    def _init_sessions(self):
        """Initialize multiple sessions with different configurations"""
        for i in range(3):  # Create 3 different sessions
            session = requests.Session()
            
            # Rotate user agents
            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
            
            # Different retry strategies for each session
            retry_strategy = Retry(
                total=5,
                backoff_factor=1 + (i * 0.5),  # Different backoff for each session
                status_forcelist=[429, 500, 502, 503, 504, 520, 521, 522, 523, 524],
                allowed_methods=["HEAD", "GET", "OPTIONS"],
                raise_on_status=False
            )
            
            adapter = HTTPAdapter(
                max_retries=retry_strategy,
                pool_connections=20,
                pool_maxsize=20
            )
            
            session.mount("http://", adapter)
            session.mount("https://", adapter)
            session.headers.update(headers)
            
            self.sessions.append(session)
    
    def _get_session(self):
        """Get a random session from the pool"""
        with self.lock:
            return random.choice(self.sessions)
    
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
    
    def _fetch_with_multiple_strategies(self, url):
        """Try multiple strategies to fetch the URL"""
        strategies = [
            self._fetch_with_session_rotation,
            self._fetch_with_different_headers,
            self._fetch_with_basic_requests
        ]
        
        for i, strategy in enumerate(strategies):
            try:
                print(f"Trying strategy {i+1} for {url}")
                response = strategy(url)
                if response and response.status_code == 200:
                    print(f"Strategy {i+1} successful")
                    return response
            except Exception as e:
                print(f"Strategy {i+1} failed: {e}")
                continue
        
        return None
    
    def _fetch_with_session_rotation(self, url):
        """Fetch using session rotation with different configurations"""
        max_attempts = 3 if self.is_github_actions else 5
        for attempt in range(max_attempts):
            session = self._get_session()
            try:
                # Shorter timeout for GitHub Actions
                timeout = random.randint(30, 60) if self.is_github_actions else random.randint(60, 120)
                response = session.get(url, timeout=timeout, verify=False)
                if response.status_code == 200:
                    return response
                else:
                    print(f"HTTP {response.status_code} on session rotation attempt {attempt+1}")
            except Exception as e:
                print(f"Session rotation attempt {attempt+1} failed: {e}")
                if attempt < max_attempts - 1:  # Don't sleep on last attempt
                    sleep_time = random.randint(2, 5) if self.is_github_actions else random.randint(3, 8)
                    time.sleep(sleep_time)
        return None
    
    def _fetch_with_different_headers(self, url):
        """Fetch with completely different headers"""
        headers_variations = [
            {
                'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            },
            {
                'User-Agent': 'curl/7.68.0',
                'Accept': '*/*',
            },
            {
                'User-Agent': 'Python-requests/2.28.1',
                'Accept': 'text/html',
            }
        ]
        
        for headers in headers_variations:
            try:
                session = requests.Session()
                session.headers.update(headers)
                timeout = 60 if self.is_github_actions else 90
                response = session.get(url, timeout=timeout, verify=False)
                if response.status_code == 200:
                    return response
            except Exception as e:
                print(f"Different headers attempt failed: {e}")
                continue
        return None
    
    def _fetch_with_basic_requests(self, url):
        """Fetch with basic requests without session"""
        try:
            timeout = 90 if self.is_github_actions else 120
            response = requests.get(url, timeout=timeout, verify=False)
            return response
        except Exception as e:
            print(f"Basic requests failed: {e}")
            return None
    
    def scrape_circulars(self, url):
        # Check execution time before starting
        if self.check_execution_time():
            print(f"Skipping {url} due to time limit")
            return []
        
        print(f"Scraping {url}...")
        response = self._fetch_with_multiple_strategies(url)
        
        if not response:
            print(f"All fetch strategies failed for {url}")
            return []
        
        try:
            print(f"Parsing response content ({len(response.content)} bytes)")
            soup = BeautifulSoup(response.content, 'html.parser')
            circulars = []
            
            # Find table rows containing circular data
            table_rows = soup.find_all('tr')
            
            # Limit processing in GitHub Actions if we have many rows
            max_rows = 100 if self.is_github_actions else len(table_rows)
            rows_to_process = table_rows[1:max_rows+1]  # Skip header row
            
            for row in rows_to_process:
                cells = row.find_all('td')
                if len(cells) >= 3:
                    # Handle different page structures
                    if "DVP" in url:
                        # DVP page has a flexible structure, typically 4-5 columns
                        if len(cells) >= 4:
                            try:
                                serial = cells[0].get_text(strip=True) if cells[0] else ""
                                date = cells[1].get_text(strip=True) if cells[1] else ""
                                
                                # For DVP pages, circular_no might be in cells[2] and description in cells[3]
                                # Or description might span cells[2] and cells[3]
                                circular_no = cells[2].get_text(strip=True) if cells[2] else ""
                                
                                # Try to get description from the most likely cell
                                if len(cells) >= 4:
                                    description = cells[3].get_text(strip=True) if cells[3] else ""
                                    # If description is empty or very short, try combining cells[2] and cells[3]
                                    if len(description) < 10 and circular_no:
                                        description = f"{circular_no} {description}".strip()
                                        circular_no = ""  # Clear circular_no if we combined it with description
                                else:
                                    description = circular_no
                                    circular_no = ""
                                
                                # Skip header rows and empty rows
                                if (len(description) > 10 and  # Reasonable description length
                                    not serial.lower() in ['sl', 'serial', 'ಕ್ರಮ', 'ಕ್ರಮಾಂಕ', 'no', 'sno'] and
                                    not date.lower() in ['date', 'ದಿನಾಂಕ'] and
                                    len(date) > 4):  # Valid date length
                                    pass  # This is a valid DVP row
                                else:
                                    continue  # Skip invalid rows
                            except:
                                continue
                        else:
                            # If less than 4 columns, try to extract what we can
                            if len(cells) >= 3:
                                date = cells[0].get_text(strip=True) if cells[0] else ""
                                circular_no = cells[1].get_text(strip=True) if cells[1] else ""
                                description = cells[2].get_text(strip=True) if cells[2] else ""
                            else:
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
            
            print(f"Successfully extracted {len(circulars)} valid circulars")
            return circulars
            
        except Exception as e:
            print(f"Error scraping {url}: {str(e)}")
            return []
    
    def scrape_all(self):
        all_circulars = []
        
        # Use parallel scraping for local, sequential for GitHub Actions (more reliable)
        if not self.is_github_actions:  # Use parallel for local development
            try:
                print("Attempting parallel scraping...")
                with ThreadPoolExecutor(max_workers=2) as executor:
                    future_to_url = {executor.submit(self.scrape_circulars, url): url for url in self.urls}
                    
                    for future in as_completed(future_to_url, timeout=300):  # 5 min timeout
                        url = future_to_url[future]
                        try:
                            circulars = future.result()
                            all_circulars.extend(circulars)
                            print(f"Found {len(circulars)} circulars from {url}")
                        except Exception as e:
                            print(f"Parallel scraping failed for {url}: {e}")
                            
                if all_circulars:
                    print(f"Parallel scraping successful, found {len(all_circulars)} total circulars")
                else:
                    print("Parallel scraping found no results, falling back to sequential")
            except Exception as e:
                print(f"Parallel scraping failed: {e}, falling back to sequential")
        
        # Sequential scraping (GitHub Actions or fallback)
        if not all_circulars or self.is_github_actions:
            if self.is_github_actions:
                print("Using sequential scraping for GitHub Actions reliability...")
            
            for url in self.urls:
                # Check execution time before each URL
                if self.check_execution_time():
                    print("Stopping scraping due to time limit")
                    break
                    
                circulars = self.scrape_circulars(url)
                all_circulars.extend(circulars)
                print(f"Found {len(circulars)} circulars from {url}")
                
                # Brief delay between URLs to be respectful
                if len(self.urls) > 1:
                    delay = random.randint(1, 3) if self.is_github_actions else random.randint(2, 5)
                    time.sleep(delay)
        
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
        
        # Take top 75 from each source to ensure representation
        selected_circulars = dept_circulars[:75] + dvp_circulars[:75]
        
        # Sort combined selection by date again
        selected_circulars.sort(key=lambda x: parse_date(x['date']), reverse=True)
        
        # Take top 150 total, but this ensures we have mix from both sources
        final_circulars = selected_circulars[:150]
        
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
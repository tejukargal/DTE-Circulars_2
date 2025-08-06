#!/usr/bin/env python3
"""
Lightweight micro-scraper for individual DTE Karnataka sources.
Designed for GitHub Actions reliability - simple, fast, single-source.
"""

import requests
from bs4 import BeautifulSoup
import json
import os
import sys
from datetime import datetime
import time

class MicroScraper:
    def __init__(self, source_name, url):
        self.source_name = source_name
        self.url = url
        self.is_github_actions = os.getenv('GITHUB_ACTIONS') == 'true'
        
        # Simple, fast session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive'
        })
        
        # Simple timeout - no retries, fail fast
        self.timeout = (15, 45) if self.is_github_actions else (20, 60)

    def is_valid_circular(self, date, circular_no, description):
        """Basic validation for circular entries"""
        if not date or len(date.strip()) <= 1:
            return False
        if not description or len(description.strip()) < 5:
            return False
        # Filter out unwanted domains
        unwanted = ['atoall.com', 'webinsight', 'javascript:', 'system access']
        desc_lower = description.lower()
        return not any(unwanted_term in desc_lower for unwanted_term in unwanted)

    def scrape(self):
        """Scrape single source with simple, fast approach"""
        print(f"Micro-scraping {self.source_name}: {self.url}")
        
        try:
            # Single attempt, fail fast
            response = self.session.get(self.url, timeout=self.timeout, verify=False)
            if response.status_code != 200:
                print(f"HTTP {response.status_code} - skipping")
                return []

            soup = BeautifulSoup(response.content, 'html.parser')
            table_rows = soup.find_all('tr')
            
            # Process only recent entries for speed
            max_rows = 20 if self.is_github_actions else 50
            circulars = []
            
            for i, row in enumerate(table_rows[1:max_rows+1]):  # Skip header
                cells = row.find_all('td')
                if len(cells) < 3:
                    continue
                
                try:
                    # Handle different table structures
                    if self.source_name in ['EST', 'ACM'] and len(cells) >= 5:
                        # 5-column format: date, circular_no, description, empty, action
                        date = cells[0].get_text(strip=True)
                        circular_no = cells[1].get_text(strip=True)
                        description = cells[2].get_text(strip=True)
                    elif self.source_name == 'DVP' and len(cells) >= 4:
                        # 4-column format: skip serial, date, circular_no, description
                        date = cells[1].get_text(strip=True)
                        circular_no = cells[2].get_text(strip=True)
                        description = cells[3].get_text(strip=True)
                    else:
                        # 3-column format (Departmental): date, circular_no, description
                        date = cells[0].get_text(strip=True)
                        circular_no = cells[1].get_text(strip=True)
                        description = cells[2].get_text(strip=True)
                    
                    # Skip headers
                    if date.lower() in ['date', 'ದಿನಾಂಕ'] or len(description) < 10:
                        continue
                    
                    # Basic validation
                    if not self.is_valid_circular(date, circular_no, description):
                        continue
                    
                    # Extract download link
                    download_link = ""
                    for cell in cells:
                        link = cell.find('a')
                        if link and link.get('href'):
                            href = link.get('href')
                            if not any(bad in href for bad in ['atoall.com', 'javascript:']):
                                if href.startswith('/'):
                                    download_link = "https://dtek.karnataka.gov.in" + href
                                elif href.startswith('http'):
                                    download_link = href
                                break
                    
                    circulars.append({
                        'date': date,
                        'circular_no': circular_no,
                        'description': description,
                        'download_link': download_link,
                        'source_url': self.url,
                        'scraped_at': datetime.now().isoformat(),
                        'source': self.source_name
                    })
                    
                except Exception as e:
                    # Skip problematic entries, continue processing
                    continue
            
            print(f"Success {self.source_name}: Found {len(circulars)} circulars")
            return circulars
            
        except Exception as e:
            print(f"Failed {self.source_name}: {str(e)}")
            return []

def main():
    if len(sys.argv) != 3:
        print("Usage: python micro_scraper.py <source_name> <url>")
        sys.exit(1)
    
    source_name = sys.argv[1]
    url = sys.argv[2]
    
    scraper = MicroScraper(source_name, url)
    circulars = scraper.scrape()
    
    # Save to individual file
    output_file = f"data_{source_name.lower()}.json"
    data = {
        'source': source_name,
        'url': url,
        'scraped_at': datetime.now().isoformat(),
        'count': len(circulars),
        'circulars': circulars,
        'status': 'success' if circulars else 'no_data'
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"Saved {len(circulars)} circulars to {output_file}")

if __name__ == "__main__":
    main()
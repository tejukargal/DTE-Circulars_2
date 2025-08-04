import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
import time
import urllib3
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
        
    def scrape_circulars(self, url):
        try:
            response = requests.get(url, headers=self.headers, timeout=30, verify=False)
            response.raise_for_status()
            
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
            print(f"Scraping {url}...")
            circulars = self.scrape_circulars(url)
            all_circulars.extend(circulars)
            time.sleep(2)  # Be respectful to the server
        
        # Remove duplicates based on circular_no and description
        seen = set()
        unique_circulars = []
        for circular in all_circulars:
            key = (circular['circular_no'], circular['description'])
            if key not in seen:
                seen.add(key)
                unique_circulars.append(circular)
        
        return unique_circulars
    
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

def main():
    scraper = CircularScraper()
    circulars = scraper.scrape_all()
    scraper.save_to_json(circulars)

if __name__ == "__main__":
    main()
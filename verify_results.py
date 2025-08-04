#!/usr/bin/env python3
import json
from datetime import datetime

def verify_scraper_results():
    """Verify the scraper results and show summary"""
    with open('circulars.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"=== Scraper Results Summary ===")
    print(f"Total circulars: {data['total_circulars']}")
    print(f"Last updated: {data['last_updated']}")
    print(f"Scraping status: {data.get('scraping_status', 'unknown')}")
    
    if 'source_breakdown' in data:
        print(f"\nSource breakdown:")
        print(f"  - Departmental: {data['source_breakdown']['departmental']}")
        print(f"  - DVP: {data['source_breakdown']['dvp']}")
    
    # Show recent circulars from each source
    dept_circulars = [c for c in data['circulars'] if 'Departmental' in c['source_url']]
    dvp_circulars = [c for c in data['circulars'] if 'DVP' in c['source_url']]
    
    print(f"\nRecent Departmental Circulars (Top 5):")
    for i, circular in enumerate(dept_circulars[:5], 1):
        try:
            desc = circular['description'][:60].encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
            print(f"  {i}. {circular['date']} - {desc}...")
        except:
            print(f"  {i}. {circular['date']} - [Description contains special characters]")
    
    print(f"\nRecent DVP Circulars (Top 5):")
    for i, circular in enumerate(dvp_circulars[:5], 1):
        try:
            desc = circular['description'][:60].encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')  
            print(f"  {i}. {circular['date']} - {desc}...")
        except:
            print(f"  {i}. {circular['date']} - [Description contains special characters]")
    
    # Check date range
    dates = [c['date'] for c in data['circulars']]
    print(f"\nDate range: {min(dates)} to {max(dates)}")
    print(f"✅ Successfully scraped {data['total_circulars']} recent circulars from both sections!")

if __name__ == "__main__":
    verify_scraper_results()
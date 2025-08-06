#!/usr/bin/env python3
"""
Smart data merger for combining micro-scraper results.
Handles fallback to baseline data if scrapers fail.
"""

import json
import os
from datetime import datetime, timedelta
import glob

class DataMerger:
    def __init__(self):
        self.sources = ['departmental', 'dvp', 'est', 'acm']
        self.baseline_file = 'circulars-baseline.json'
        self.output_file = 'circulars.json'
        
    def load_baseline(self):
        """Load baseline data as fallback"""
        try:
            if os.path.exists(self.baseline_file):
                with open(self.baseline_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️ Could not load baseline: {e}")
        return None
    
    def load_source_data(self, source):
        """Load data from individual micro-scraper"""
        filename = f"data_{source}.json"
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Check if data is recent (within last 4 hours)
                    scraped_time = datetime.fromisoformat(data['scraped_at'].replace('Z', '+00:00'))
                    if (datetime.now() - scraped_time).total_seconds() < 4 * 3600:
                        return data['circulars']
                    else:
                        print(f"⚠️ {source}: Data too old, skipping")
        except Exception as e:
            print(f"⚠️ {source}: Could not load - {e}")
        return []
    
    def merge_data(self):
        """Merge all available data sources"""
        print("Starting data merge...")
        
        # Collect fresh data from all sources
        all_circulars = []
        source_counts = {}
        
        for source in self.sources:
            circulars = self.load_source_data(source)
            all_circulars.extend(circulars)
            source_counts[source] = len(circulars)
            print(f"{source.upper()}: {len(circulars)} circulars")
        
        # If we got very little data, fall back to baseline
        if len(all_circulars) < 50:
            print("Too little fresh data, loading baseline...")
            baseline = self.load_baseline()
            if baseline and 'circulars' in baseline:
                baseline_circulars = baseline['circulars']
                # Mix fresh data with baseline
                all_circulars.extend(baseline_circulars)
                print(f"Added {len(baseline_circulars)} baseline circulars")
        
        # Remove duplicates based on circular_no and description
        seen = set()
        unique_circulars = []
        for circular in all_circulars:
            key = (circular.get('circular_no', ''), circular.get('description', ''))
            if key not in seen and key != ('', ''):
                seen.add(key)
                unique_circulars.append(circular)
        
        # Sort by date, newest first
        def parse_date(date_str):
            try:
                date_str = date_str.strip()
                if '/' in date_str:
                    parts = date_str.split('/')
                    if len(parts) == 3:
                        return datetime(int(parts[2]), int(parts[1]), int(parts[0]))
                elif '-' in date_str:
                    parts = date_str.split('-')
                    if len(parts) == 3:
                        if len(parts[2]) == 4:
                            return datetime(int(parts[2]), int(parts[1]), int(parts[0]))
                        elif len(parts[0]) == 4:
                            return datetime(int(parts[0]), int(parts[1]), int(parts[2]))
            except:
                pass
            return datetime(1900, 1, 1)
        
        unique_circulars.sort(key=lambda x: parse_date(x['date']), reverse=True)
        
        # Take top 400 circulars
        final_circulars = unique_circulars[:400]
        
        # Count by source
        final_counts = {}
        for source in self.sources:
            count = sum(1 for c in final_circulars if c.get('source', '').lower() == source)
            final_counts[source] = count
        
        # Create final data structure
        merged_data = {
            'last_updated': datetime.now().isoformat(),
            'total_circulars': len(final_circulars),
            'circulars': final_circulars,
            'scraping_status': 'success' if len(final_circulars) > 100 else 'partial',
            'source_breakdown': final_counts,
            'merge_info': {
                'merged_at': datetime.now().isoformat(),
                'sources_used': [s for s, c in source_counts.items() if c > 0],
                'fresh_data_count': sum(source_counts.values()),
                'total_after_merge': len(final_circulars)
            }
        }
        
        # Save merged data
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, ensure_ascii=False, indent=2)
        
        print(f"Merge complete: {len(final_circulars)} total circulars")
        print(f"Source breakdown: {final_counts}")
        return merged_data

def main():
    merger = DataMerger()
    result = merger.merge_data()
    
    # Print summary
    info = result.get('merge_info', {})
    print(f"\nSummary:")
    print(f"   Fresh data: {info.get('fresh_data_count', 0)} circulars")
    print(f"   Final total: {info.get('total_after_merge', 0)} circulars")
    print(f"   Status: {result.get('scraping_status', 'unknown')}")

if __name__ == "__main__":
    main()
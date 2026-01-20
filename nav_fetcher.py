from mftool import Mftool
from fuzzywuzzy import process
import pandas as pd
import datetime
import json
import os

class NavFetcher:
    def __init__(self):
        self.mf = Mftool()
        self.scheme_codes = self.mf.get_scheme_codes() # Returns a dict {code: name}
        self.scheme_names = list(self.scheme_codes.values())
        self.cache_file = 'nav_cache.json'
        self.mapping_file = 'scheme_mapping.json'
        self.load_mappings()
        self.load_cache()

    def load_mappings(self):
        if os.path.exists(self.mapping_file):
            with open(self.mapping_file, 'r') as f:
                self.mappings = json.load(f)
        else:
            self.mappings = {}

    def save_mappings(self):
        with open(self.mapping_file, 'w') as f:
            json.dump(self.mappings, f, indent=4)

    def load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    self.cache = json.load(f)
            except:
                self.cache = {}
        else:
            self.cache = {}

    def save_cache(self):
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=4)

    def get_scheme_code(self, scheme_name):
        """
        Finds the AMFI scheme code for a given scheme name using fuzzy matching.
        """
        if scheme_name in self.mappings:
            return self.mappings[scheme_name]

        # Fuzzy match
        # We look for the best match in the AMFI list
        best_match, score = process.extractOne(scheme_name, self.scheme_names)
        
        if score > 80: # Threshold for automatic acceptance
            # Find the code for this name
            for code, name in self.scheme_codes.items():
                if name == best_match:
                    self.mappings[scheme_name] = code
                    self.save_mappings()
                    return code
        
        print(f"Warning: Low match score ({score}) for '{scheme_name}'. Best match: '{best_match}'")
        return None

    def fetch_historical_nav(self, scheme_code):
        """
        Fetches historical NAV for a given scheme code.
        Checks cache first. Cache is valid for 24 hours.
        """
        if not scheme_code:
            return None
            
        # Check Cache
        today_str = datetime.date.today().isoformat()
        
        if scheme_code in self.cache:
            last_updated = self.cache[scheme_code].get('last_updated')
            # If updated today, return cached data
            if last_updated == today_str:
                data = self.cache[scheme_code]['data']
                df = pd.DataFrame(data)
                df['date'] = pd.to_datetime(df['date']) # Format is already ISO in JSON usually or we need to check
                # When saving to JSON, dates become strings. 
                # Let's standardize on saving as list of dicts with ISO date strings
                return df

        try:
            data = self.mf.get_scheme_historical_nav(scheme_code)
            if data and 'data' in data:
                raw_data = data['data']
                
                # Process for DataFrame
                df = pd.DataFrame(raw_data)
                df['date'] = pd.to_datetime(df['date'], format='%d-%m-%Y')
                df['nav'] = pd.to_numeric(df['nav'])
                df = df.sort_values('date')
                
                # Update Cache
                # Convert date back to string for JSON serialization
                cache_data = df.copy()
                cache_data['date'] = cache_data['date'].dt.strftime('%Y-%m-%d')
                
                self.cache[scheme_code] = {
                    'last_updated': today_str,
                    'data': cache_data.to_dict('records')
                }
                self.save_cache()
                
                return df
        except Exception as e:
            print(f"Error fetching NAV for {scheme_code}: {e}")
            return None
        return None

if __name__ == "__main__":
    fetcher = NavFetcher()
    # Test with a known fund from the user's list (based on previous output)
    test_fund = "Franklin India Small Cap Fund - Growth" 
    code = fetcher.get_scheme_code(test_fund)
    print(f"Code for '{test_fund}': {code}")
    
    if code:
        df = fetcher.fetch_historical_nav(code)
        if df is not None:
            print(f"Fetched {len(df)} records.")
            print(df.tail())

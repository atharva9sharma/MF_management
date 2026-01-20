import pandas as pd
import warnings

# Suppress openpyxl warnings
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

class DataProcessor:
    def __init__(self, file_path):
        self.file_path = file_path
        self.transactions = None

    def load_data(self):
        """
        Loads the Excel file and extracts transaction data.
        Assumes the 'Transaction Details' sheet exists and header is at row 8 (0-indexed).
        """
        try:
            # Read the specific sheet with header at row 8
            df = pd.read_excel(self.file_path, sheet_name='Transaction Details', header=8)
            
            # Filter for relevant columns
            required_cols = ['Scheme Name', 'Date', 'NAV', 'Units', 'Amount', 'Transaction Description']
            # Map columns if names are slightly different (e.g. extra spaces)
            col_map = {c: c.strip() for c in df.columns}
            df.rename(columns=col_map, inplace=True)
            
            # Ensure we have the columns we need
            available_cols = [c for c in required_cols if c in df.columns]
            df = df[available_cols].copy()
            
            # Drop rows where Scheme Name is NaN (often footer or empty lines)
            df.dropna(subset=['Scheme Name'], inplace=True)
            
            # Convert Date to datetime
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df.dropna(subset=['Date'], inplace=True)
            
            # Convert numeric fields
            for col in ['NAV', 'Units', 'Amount']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            # Filter out zero amount transactions if they are not relevant (e.g. stamp duty lines often have small amounts, but 0 might be reversals)
            # Keeping all for now, but user might want to filter.
            
            self.transactions = df
            return df
            
        except Exception as e:
            print(f"Error loading data: {e}")
            return None

    def get_schemes(self):
        """Returns a list of unique scheme names found in the transactions."""
        if self.transactions is not None:
            return self.transactions['Scheme Name'].unique().tolist()
        return []

    def get_transactions_for_scheme(self, scheme_name):
        """Returns transactions for a specific scheme."""
        if self.transactions is not None:
            return self.transactions[self.transactions['Scheme Name'] == scheme_name].sort_values('Date')
        return pd.DataFrame()

if __name__ == "__main__":
    # Test run
    processor = DataProcessor('/Users/nbt3157/Personal/MF_management/cas_detailed_report_2026_01_20_151931.xlsx')
    df = processor.load_data()
    if df is not None:
        print("Data loaded successfully.")
        print(f"Total transactions: {len(df)}")
        schemes = processor.get_schemes()
        print(f"Found {len(schemes)} schemes:")
        for s in schemes:
            print(f" - {s}")

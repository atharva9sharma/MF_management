import pandas as pd
import os

file_path = '/Users/nbt3157/Personal/MF_management/cas_detailed_report_2026_01_20_151931.xlsx'

try:
    # Read the excel file. It might have a password or specific sheet structure.
    # Assuming standard format first.
    xls = pd.ExcelFile(file_path)
    print(f"Sheet names: {xls.sheet_names}")
    
    for sheet in ['Transaction Details']:
        print(f"\n--- Sheet: {sheet} ---")
        # Read first 20 rows to find header
        df_temp = pd.read_excel(xls, sheet_name=sheet, nrows=20, header=None)
        
        # Based on previous output, header seems to be at index 8
        df = pd.read_excel(xls, sheet_name=sheet, header=8)
        print("Columns:", df.columns.tolist())
        print(df.head())
        
        # Check for required columns
        required_cols = ['Date', 'NAV', 'Units', 'Amount', 'Scheme Name', 'Transaction Date']
        found_cols = [col for col in df.columns if any(req.lower() in str(col).lower() for req in required_cols)]
        print("Found relevant columns:", found_cols)
        
except Exception as e:
    print(f"Error reading Excel file: {e}")

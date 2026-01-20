import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from data_processor import DataProcessor
from nav_fetcher import NavFetcher
import os

st.set_page_config(page_title="MF SIP Tracker", layout="wide")

@st.cache_data
def load_data(file_path):
    processor = DataProcessor(file_path)
    df = processor.load_data()
    return processor, df

def main():
    st.title("Mutual Fund SIP Tracker")
    
    # Sidebar for configuration
    st.sidebar.header("Configuration")
    
    # File Selection
    uploaded_file = st.sidebar.file_uploader("Upload CAS Excel File", type=['xlsx', 'xls'])
    
    DEFAULT_FILE = 'default_cas.xlsx'
    
    if uploaded_file is not None:
        file_source = uploaded_file
        # Option to save as default
        if st.sidebar.button("Set as Default"):
            with open(DEFAULT_FILE, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.sidebar.success("File saved as default!")
    elif os.path.exists(DEFAULT_FILE):
        st.sidebar.info("Using default cached file.")
        file_source = DEFAULT_FILE
    else:
        # Fallback to local path for development if it exists, otherwise warn
        dev_path = '/Users/nbt3157/Personal/MF_management/cas_detailed_report_2026_01_20_151931.xlsx'
        if os.path.exists(dev_path):
             st.sidebar.info("Using local dev file.")
             file_source = dev_path
        else:
            st.warning("Please upload a CAS Excel file to proceed.")
            return

    processor, df = load_data(file_source)
    
    if df is None:
        st.error("Failed to load data.")
        return

    # Initialize NAV Fetcher
    fetcher = NavFetcher()
    
    # Scheme Selection Logic
    schemes = processor.get_schemes()
    
    # Filter for Active SIPs (funds with transactions in last 45 days)
    # We need to check transactions for each scheme
    active_schemes = []
    cutoff_date = datetime.datetime.now() - pd.Timedelta(days=45)
    
    for s in schemes:
        trans = processor.get_transactions_for_scheme(s)
        # Check for PURCHASES (Amount > 0) in the last 45 days
        recent_purchases = trans[(trans['Date'] >= cutoff_date) & (trans['Amount'] > 0)]
        if not recent_purchases.empty:
            active_schemes.append(s)
            
    use_active_only = st.sidebar.checkbox("Show Only Active SIPs", value=True)
    
    if use_active_only and active_schemes:
        display_schemes = active_schemes
    else:
        display_schemes = schemes
        
    selected_scheme = st.sidebar.selectbox("Select Scheme", display_schemes)
    
    if selected_scheme:
        st.header(f"Analysis: {selected_scheme}")
        
        # Get transactions for this scheme
        transactions = processor.get_transactions_for_scheme(selected_scheme)
        
        # Get Historical NAV
        with st.spinner("Fetching Historical NAV..."):
            scheme_code = fetcher.get_scheme_code(selected_scheme)
            
            if not scheme_code:
                st.warning(f"Could not find AMFI scheme code for '{selected_scheme}'. Please check mapping.")
                st.dataframe(transactions)
                return
                
            nav_data = fetcher.fetch_historical_nav(scheme_code)
            
        if nav_data is None:
            st.error("Failed to fetch historical NAV data.")
            st.dataframe(transactions)
            return

        # Time Range Selection
        time_ranges = {
            "6 Months": 180,
            "1 Year": 365,
            "2 Years": 2*365,
            "3 Years": 3*365,
            "All Time": None
        }
        selected_range = st.radio("Select Time Range", list(time_ranges.keys()), index=1, horizontal=True)
        
        # Filter NAV data based on selection
        end_date = datetime.datetime.now()
        
        if time_ranges[selected_range]:
            start_date = end_date - pd.Timedelta(days=time_ranges[selected_range])
        else:
            # All Time: Start from the beginning of available NAV data or transactions
            start_date = nav_data['date'].min()
            if not transactions.empty:
                start_date = min(start_date, transactions['Date'].min())

        # Ensure we cover transaction history if it falls within the window (optional, but user might want to see context)
        # Actually, for "All Time" we want everything. For specific ranges, we strictly respect the range 
        # BUT if a transaction happened in that range, we show it.
        
        mask = (nav_data['date'] >= start_date) & (nav_data['date'] <= end_date)
        filtered_nav = nav_data.loc[mask]
        
        # Plotting
        fig = go.Figure()
        
        # NAV Line
        fig.add_trace(go.Scatter(
            x=filtered_nav['date'], 
            y=filtered_nav['nav'],
            mode='lines',
            name='NAV',
            line=dict(color='blue', width=2)
        ))
        
        # Process Transactions for Plotting
        if not transactions.empty:
            # Aggregate by Date
            agg_trans = transactions.groupby('Date').agg({
                'Amount': 'sum',
                'Units': 'sum',
                'NAV': 'mean' # NAV should be same for same day usually
            }).reset_index()
            
            # Filter for purchases (Amount > 0)
            purchases = agg_trans[agg_trans['Amount'] > 0]
            
            if not purchases.empty:
                # Calculate size based on amount
                # Normalize size: min 8, max 25
                min_size = 8
                max_size = 25
                min_amt = purchases['Amount'].min()
                max_amt = purchases['Amount'].max()
                
                if max_amt == min_amt:
                    purchases['size'] = 12
                else:
                    purchases['size'] = purchases['Amount'].apply(
                        lambda x: min_size + (x - min_amt) * (max_size - min_size) / (max_amt - min_amt)
                    )

                fig.add_trace(go.Scatter(
                    x=purchases['Date'],
                    y=purchases['NAV'],
                    mode='markers',
                    name='Purchase',
                    marker=dict(
                        color='green', 
                        size=purchases['size'], 
                        symbol='circle',
                        line=dict(color='white', width=1)
                    ),
                    text=purchases.apply(lambda row: f"Date: {row['Date'].date()}<br>Total Amount: ₹{row['Amount']:,.2f}<br>Total Units: {row['Units']:.2f}", axis=1),
                    hoverinfo='text'
                ))
        
        # Redemption Points (if any)
        redemptions = transactions[transactions['Amount'] < 0] # Assuming negative amount for redemption, or we check units
        # Actually in the file, amount might be positive for redemption too? 
        # Let's assume based on units. If units are negative?
        # The sample data showed positive units and amount. Need to check if there are redemptions.
        # For now, let's just plot all transactions.
        
        fig.update_layout(
            title=f"NAV Performance & Transactions - {selected_scheme}",
            xaxis_title="Date",
            yaxis_title="NAV",
            hovermode="x unified",
            height=600
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Transaction Table
        st.subheader("Transaction Details")
        st.dataframe(transactions)
        
        # Summary Metrics
        total_invested = transactions['Amount'].sum()
        total_units = transactions['Units'].sum()
        latest_nav = filtered_nav.iloc[-1]['nav']
        current_value = total_units * latest_nav
        profit = current_value - total_invested
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Invested", f"₹{total_invested:,.2f}")
        col2.metric("Current Value", f"₹{current_value:,.2f}")
        col3.metric("Profit/Loss", f"₹{profit:,.2f}", delta_color="normal")
        
    st.markdown("---")
    st.markdown("<div style='text-align: center; color: grey;'>Made By Atharva</div>", unsafe_allow_html=True)

import datetime
if __name__ == "__main__":
    main()

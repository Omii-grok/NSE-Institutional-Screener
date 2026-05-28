import pandas as pd
import sys

def ultimate_triple_scanner(csv_file_path):
    print("Initiating EOD Ultimate Triple Scan...\n")
    try:
        # 1. Load and clean the data
        df = pd.read_csv(csv_file_path, skipinitialspace=True)
        df = df[df['SERIES'] == 'EQ'].copy()
        df.columns = df.columns.str.strip()
        
        # 2. Force columns to numeric
        df['DELIV_PER'] = pd.to_numeric(df['DELIV_PER'], errors='coerce')
        df['CLOSE_PRICE'] = pd.to_numeric(df['CLOSE_PRICE'], errors='coerce')
        df['PREV_CLOSE'] = pd.to_numeric(df['PREV_CLOSE'], errors='coerce')
        df['TTL_TRD_QNTY'] = pd.to_numeric(df['TTL_TRD_QNTY'], errors='coerce')
        
        # 3. Calculate Percentage Change
        df['PCT_CHANGE'] = ((df['CLOSE_PRICE'] - df['PREV_CLOSE']) / df['PREV_CLOSE']) * 100
        
        # ==========================================================
        # OUTPUT 1: ORIGINAL HIGH-VOLUME INSTITUTIONAL BREAKOUTS
        # ==========================================================
        out_1 = df[
            (df['CLOSE_PRICE'] > 50.0) &
            (df['TTL_TRD_QNTY'] > 500000) &  # Strictly greater than 5 Lakhs
            (df['PCT_CHANGE'] >= 4.0) &
            (df['DELIV_PER'] >= 50.0)
        ].copy()
        out_1 = out_1.sort_values(by='DELIV_PER', ascending=False)
        out_1 = out_1[['SYMBOL', 'CLOSE_PRICE', 'PCT_CHANGE', 'TTL_TRD_QNTY', 'DELIV_PER']]
        out_1.columns = ['Symbol', 'Close Price (₹)', 'Change (%)', 'Total Volume', 'Delivery (%)']
        out_1['Change (%)'] = out_1['Change (%)'].round(2)
        
        # ==========================================================
        # OUTPUT 2: HNI / LOW-VOLUME BREAKOUTS
        # ==========================================================
        out_2 = df[
            (df['CLOSE_PRICE'] > 50.0) &
            (df['TTL_TRD_QNTY'] > 50000) &
            (df['TTL_TRD_QNTY'] <= 500000) & # Ensures no duplicates from Output 1
            (df['PCT_CHANGE'] >= 4.0) &
            (df['DELIV_PER'] >= 50.0)
        ].copy()
        out_2 = out_2.sort_values(by='DELIV_PER', ascending=False)
        out_2 = out_2[['SYMBOL', 'CLOSE_PRICE', 'PCT_CHANGE', 'TTL_TRD_QNTY', 'DELIV_PER']]
        out_2.columns = ['Symbol', 'Close Price (₹)', 'Change (%)', 'Total Volume', 'Delivery (%)']
        out_2['Change (%)'] = out_2['Change (%)'].round(2)

        # ==========================================================
        # OUTPUT 3: 100% PURE DELIVERY (CIRCUIT LOCKS)
        # ==========================================================
        out_3 = df[
            (df['CLOSE_PRICE'] > 10.0) &
            (df['TTL_TRD_QNTY'] > 0) & 
            (df['DELIV_PER'] == 100.0) & 
            (df['PCT_CHANGE'] > 0) # Must be in the green
        ].copy()
        out_3 = out_3.sort_values(by='TTL_TRD_QNTY', ascending=False)
        out_3 = out_3[['SYMBOL', 'CLOSE_PRICE', 'PCT_CHANGE', 'TTL_TRD_QNTY', 'DELIV_PER']]
        
        out_3.columns = ['Symbol', 'Close Price (₹)', 'Change (%)', 'Total Volume', 'Delivery (%)']
        out_3['Change (%)'] = out_3['Change (%)'].round(2)
        
        # ==========================================================
        # TERMINAL PRINTER (PRINTS ALL 3 LISTS)
        # ==========================================================
        print("=" * 75)
        print(" OUTPUT 1: HIGH-VOLUME INSTITUTIONAL BREAKOUTS (Vol > 5 Lakhs)")
        print("=" * 75)
        if out_1.empty:
            print("No stocks met the criteria today.")
        else:
            print(out_1.to_string(index=False))
            
        print("\n" * 2) # Adding spacing between tables
        
        print("=" * 75)
        print(" OUTPUT 2: HNI / LOW-VOLUME BREAKOUTS (Vol 50k to 5 Lakhs)")
        print("=" * 75)
        if out_2.empty:
            print("No stocks met the criteria today.")
        else:
            print(out_2.to_string(index=False))
            
        print("\n" * 2)
        
        print("=" * 75)
        print(" OUTPUT 3: 100% PURE DELIVERY (Positive Close & Circuit Locks)")
        print("=" * 75)
        if out_3.empty:
            print("No stocks recorded exactly 100.00% delivery in the green today.")
        else:
            print(out_3.to_string(index=False))
            print("\n")
            
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# --- Execution ---
if __name__ == "__main__":
    # Check if user provided a CSV file as argument
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    else:
        csv_file = 'sec_bhavdata_full.csv'
    
    print(f"Processing file: {csv_file}\n")
    ultimate_triple_scanner(csv_file)
import yfinance as yf
import json
from datetime import datetime

# List of top 10 defense company tickers
DEFENSE_TICKERS = [
    "LMT",   # Lockheed Martin
    "RTX",   # Raytheon Technologies
    "BA",    # Boeing
    "GD",    # General Dynamics
    "NOC",   # Northrop Grumman
    "HII",   # Huntington Ingalls Industries
    "LHX",   # L3Harris Technologies
    "BAESY", # BAE Systems
    "LDOS",  # Leidos Holdings
    "AXON"   # Axon Enterprise
]

def get_defense_stocks_data():
    data = []
    
    for ticker in DEFENSE_TICKERS:
        try:
            # Get stock info
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Get current price and calculate daily change
            current_price = info.get('currentPrice', 'N/A')
            previous_close = info.get('previousClose', 'N/A')
            
            if current_price != 'N/A' and previous_close != 'N/A':
                price_change_percent = ((current_price - previous_close) / previous_close) * 100
            else:
                price_change_percent = 'N/A'
            
            # Add to data list
            data.append({
                'ticker': ticker,
                'current_price': float(current_price) if current_price != 'N/A' else None,
                'change_percent': float(f"{price_change_percent:.2f}") if price_change_percent != 'N/A' else None
            })
            
        except Exception as e:
            print(f"Error fetching data for {ticker}: {str(e)}", file=sys.stderr)
            continue
    
    return data

if __name__ == "__main__":
    import sys
    data = get_defense_stocks_data()
    print(json.dumps(data, indent=2)) 
import yfinance as yf
import json
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

# Pydantic Models
class StockData(BaseModel):
    ticker: str
    current_price: Optional[float] = None
    change_percent: Optional[float] = None
    status: str = Field(default="unknown", description="Stock status: increasing, decreasing, or stable")

class StocksAnalysis(BaseModel):
    timestamp: str
    stocks: List[StockData]
    statistics: dict
    market_summary: dict

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

# Global variable to store stocks data
stocks_data: Optional[StocksAnalysis] = None

def fetch_defense_stocks_data() -> List[StockData]:
    """Fetch current defense stocks data"""
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
                status = "increasing" if price_change_percent > 0 else "decreasing" if price_change_percent < 0 else "stable"
            else:
                price_change_percent = 'N/A'
                status = "unknown"
            
            # Add to data list
            stock_data = StockData(
                ticker=ticker,
                current_price=float(current_price) if current_price != 'N/A' else None,
                change_percent=float(f"{price_change_percent:.2f}") if price_change_percent != 'N/A' else None,
                status=status
            )
            data.append(stock_data)
            
        except Exception as e:
            print(f"Error fetching data for {ticker}: {str(e)}")
            # Add error entry
            data.append(StockData(
                ticker=ticker,
                current_price=None,
                change_percent=None,
                status="error"
            ))
            continue
    
    return data

def update_stocks_data() -> StocksAnalysis:
    """Update and return complete stocks analysis"""
    global stocks_data
    
    print("Updating stocks data...")
    stocks_list = fetch_defense_stocks_data()
    
    # Calculate statistics
    valid_changes = [stock.change_percent for stock in stocks_list if stock.change_percent is not None]
    avg_stock_change = sum(valid_changes) / len(valid_changes) if valid_changes else 0
    max_change = max(valid_changes) if valid_changes else 0
    min_change = min(valid_changes) if valid_changes else 0
    
    statistics = {
        "average_change_percent": round(avg_stock_change, 2),
        "max_change_percent": round(max_change, 2),
        "min_change_percent": round(min_change, 2),
        "stocks_analyzed": len(stocks_list),
        "valid_data_points": len(valid_changes)
    }
    
    market_summary = {
        "overall_trend": "bullish" if avg_stock_change > 0 else "bearish",
        "volatility": abs(max_change - min_change)
    }
    
    stocks_data = StocksAnalysis(
        timestamp=datetime.now().isoformat(),
        stocks=stocks_list,
        statistics=statistics,
        market_summary=market_summary
    )
    
    print(f"Stocks data updated: {len(stocks_list)} stocks analyzed")
    return stocks_data

def get_defense_stocks_data() -> Optional[StocksAnalysis]:
    """Get current stocks data from memory"""
    return stocks_data

if __name__ == "__main__":
    import sys
    data = update_stocks_data()
    print(data.model_dump_json(indent=2)) 
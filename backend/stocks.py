import yfinance as yf
import json
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from threading import Lock

# Pydantic Models
class StockData(BaseModel):
    ticker: str
    current_price: Optional[float] = None
    change_percent: Optional[float] = None
    status: str = Field(default="unknown", description="Stock status: increasing, decreasing, or stable")

class StockSummary(BaseModel):
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
    "PLTR",  # Palantir Technologies
    "NVDA",  # Nvidia
]

# Global variable to store stocks data
stock_data: Optional[StockSummary] = None
lock = Lock()

def fetch_stock_data() -> List[StockData]:
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
            stock_data_item = StockData(
                ticker=ticker,
                current_price=float(current_price) if current_price != 'N/A' else None,
                change_percent=float(f"{price_change_percent:.2f}") if price_change_percent != 'N/A' else None,
                status=status
            )
            data.append(stock_data_item)
            
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

def fetch_stock_summary() -> StockSummary:
    stocks_list = fetch_stock_data()
    
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
    
    stock_summary = StockSummary(
        timestamp=datetime.now().isoformat(),
        stocks=stocks_list,
        statistics=statistics,
        market_summary=market_summary
    )
    
    return stock_summary

def update_stock_data():
    global stock_data
    with lock:
        stock_data = fetch_stock_summary()

def get_stock_data() -> Optional[StockSummary]:
    with lock:
        return stock_data.copy() if stock_data else None
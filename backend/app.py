from dotenv import load_dotenv
import json
import os

load_dotenv()

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import asyncio
import os
from dotenv import load_dotenv

# Import data modules
from stocks import stocks_data, update_stocks_data, get_defense_stocks_data
from news import articles, calculate_doomsday_probability
from pizza import pizza_data, update_pentagon_pizza_data, get_pentagon_pizza_data

# Check required environment variables
required_env_vars = ['OPENAI_API_KEY', 'NEWSAPI_KEY', 'GOOGLE_MAPS_API_KEY']
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

app = FastAPI(
    title="Doomsday Analysis API",
    description="API providing real-time defense stocks, news analysis, and local pizza data",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Background task functions
async def update_stocks_periodically():
    while True:
        try:
            update_stocks_data()
        except Exception as e:
            print(f"Error updating stocks: {str(e)}")
        await asyncio.sleep(10)  # 10 seconds

async def update_news_periodically():
    while True:
        try:
            calculate_doomsday_probability()  # This will fetch fresh articles and analyze them
        except Exception as e:
            print(f"Error updating news: {str(e)}")
        await asyncio.sleep(3600)  # 1 hour = 3600 seconds

async def update_pizza_periodically():
    while True:
        try:
            update_pentagon_pizza_data()
        except Exception as e:
            print(f"Error updating pizza: {str(e)}")
        await asyncio.sleep(1200)  # 20 minutes = 1200 seconds

# API Endpoints
@app.get("/stocks")
async def get_stocks():
    """Get current defense stocks analysis"""
    try:
        data = get_defense_stocks_data()
        if data is None:
            raise HTTPException(status_code=503, detail="Stocks data not yet available. Please try again in a few seconds.")
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/news")
async def get_news_analysis():
    """Get comprehensive news analysis with doomsday probability"""
    try:
        return calculate_doomsday_probability()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/pizza")
async def get_pizza_analysis():
    """Get pizza place analysis around the Pentagon"""
    try:
        data = get_pentagon_pizza_data()
        if data is None:
            raise HTTPException(status_code=503, detail="Pizza data not yet available. Please try again in a few minutes.")
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Startup event to initialize background tasks
@app.on_event("startup")
async def startup_event():
    print("Loading initial data...")
    try:
        update_stocks_data()
        print("✓ Initial stocks data loaded")
    except Exception as e:
        print(f"✗ Failed to load initial stocks data: {e}")
    
    try:
        calculate_doomsday_probability()
        print("✓ Initial news data loaded")
    except Exception as e:
        print(f"✗ Failed to load initial news data: {e}")
    
    try:
        update_pentagon_pizza_data()
        print("✓ Initial pizza data loaded")
    except Exception as e:
        print(f"✗ Failed to load initial pizza data: {e}")
    
    # Start background tasks
    print("Starting background update tasks...")
    asyncio.create_task(update_stocks_periodically())
    asyncio.create_task(update_news_periodically())
    asyncio.create_task(update_pizza_periodically())
    print("✓ All background tasks started")
    print("Pentagon Pizza Meter API is ready!")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

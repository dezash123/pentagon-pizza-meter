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
from stocks import update_stock_data, get_stock_data
from news import update_news_data, get_news_data
from pizza import update_pizza_data, get_pizza_data

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
async def stock_task():
    while True:
        try:
            update_stock_data()
        except Exception as e:
            print(f"Error updating stocks: {str(e)}")
        await asyncio.sleep(10)  # 10 seconds

async def news_task():
    while True:
        try:
            update_news_data()  # This will fetch fresh articles and analyze them
        except Exception as e:
            print(f"Error updating news: {str(e)}")
        await asyncio.sleep(3600)  # 1 hour = 3600 seconds

async def pizza_task():
    while True:
        try:
            update_pizza_data()
        except Exception as e:
            print(f"Error updating pizza: {str(e)}")
        await asyncio.sleep(1200)  # 20 minutes = 1200 seconds

# API Endpoints
@app.get("/stocks")
async def get_stocks():
    return get_stock_data()

@app.get("/news")
async def get_news_analysis():
    """Get comprehensive news analysis with doomsday probability"""
    try:
        return get_news_data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/pizza")
async def get_pizza_analysis():
    return get_pizza_data() 

# Startup event to initialize background tasks
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(stock_task())
    asyncio.create_task(news_task())
    asyncio.create_task(pizza_task())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

from dotenv import load_dotenv
import json
import os

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import defense_stocks
import news_analysis
import populartimes
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase Admin SDK
firebase_credentials = json.loads(os.getenv('FIREBASE_CREDENTIALS', '{}'))
cred = credentials.Certificate(firebase_credentials)
firebase_admin.initialize_app(cred)
db = firestore.client()

# Check required environment variables
required_env_vars = ['OPENAI_API_KEY', 'NEWSAPI_KEY', 'GOOGLE_MAPS_API_KEY']
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

app = FastAPI(
    title="Doomsday Analysis API",
    description="API providing comprehensive defense stocks, news analysis, and local pizza data",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def is_pizza_place(place):
    """Check if a place is a pizza establishment"""
    if "types" in place and any("pizza" in t.lower() for t in place["types"]):
        return True
    if "name" in place and "pizza" in place["name"].lower():
        return True
    return False

def get_pentagon_pizza_data():
    """Get pizza place data around the Pentagon"""
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    
    # Pentagon coordinates and search area
    pentagon_lat, pentagon_lng = 38.8719, -77.0563
    degree_offset = 0.0145 * 5  # 5 miles
    
    bound_lower = (pentagon_lat - degree_offset, pentagon_lng - degree_offset)
    bound_upper = (pentagon_lat + degree_offset, pentagon_lng + degree_offset)
    
    places = []
    place_types = ["restaurant", "meal_takeaway"]
    
    for place_type in place_types:
        results = populartimes.get(
            api_key,
            [place_type],
            bound_lower,
            bound_upper,
            radius=8047
        )
        pizza_places = [place for place in results if is_pizza_place(place)]
        places.extend(pizza_places)

    # Remove duplicates
    unique_places = []
    seen = set()
    for place in places:
        key = (place["name"], place["address"])
        if key not in seen:
            seen.add(key)
            unique_places.append(place)

    current_hour = datetime.now().hour
    current_day = datetime.now().strftime("%A")
    
    busy_places = []
    for place in unique_places:
        if "current_popularity" in place:
            typical_popularity = 0
            for day in place["populartimes"]:
                if day["name"] == current_day:
                    typical_popularity = day["data"][current_hour]
                    break
            
            busyness_ratio = (place["current_popularity"] / typical_popularity) if typical_popularity > 0 else 1
            percent_difference = round((busyness_ratio - 1) * 100, 1)
            
            weekly_schedule = {}
            for day in place["populartimes"]:
                weekly_schedule[day["name"]] = {
                    "hourly_data": day["data"],
                    "peak_hour": day["data"].index(max(day["data"])),
                    "peak_popularity": max(day["data"])
                }

            place_data = {
                "name": place["name"],
                "address": place["address"],
                "coordinates": place.get("coordinates", {}),
                "current_status": {
                    "current_popularity": place["current_popularity"],
                    "typical_popularity": typical_popularity,
                    "busyness_ratio": round(busyness_ratio, 2),
                    "percent_difference": percent_difference,
                    "status": "busier" if percent_difference > 0 else "less busy" if percent_difference < 0 else "typical"
                },
                "ratings": {
                    "google_rating": place.get("rating", None),
                    "number_of_ratings": place.get("rating_n", None)
                },
                "place_types": place.get("types", []),
                "weekly_popularity": weekly_schedule,
                "wait_time_minutes": place.get("time_wait", None),
                "time_spent_minutes": place.get("time_spent", None)
            }
            busy_places.append(place_data)
    
    # Sort by how unusually busy they are
    busy_places.sort(key=lambda x: abs(x["current_status"]["percent_difference"]), reverse=True)
    
    return {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "location": "Pentagon Area",
            "radius_miles": 5,
            "search_type": "Pizza Places",
            "current_time": f"{current_hour}:00",
            "current_day": current_day,
            "total_pizza_places_found": len(unique_places),
            "places_with_current_data": len(busy_places)
        },
        "pizza_places": busy_places
    }

def save_to_firebase(data: dict):
    """Save analysis data to Firebase"""
    try:
        # Convert datetime objects to strings for Firebase
        data_copy = json.loads(json.dumps(data, default=str))
        
        # Save to 'analyses' collection with timestamp as document ID
        timestamp = data_copy['metadata']['timestamp'].replace(':', '-')
        doc_ref = db.collection('analyses').document(timestamp)
        doc_ref.set(data_copy)
        
        # Also save as latest analysis
        latest_ref = db.collection('analyses').document('latest')
        latest_ref.set(data_copy)
        
        return timestamp
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save to Firebase: {str(e)}")

def get_latest_from_firebase():
    """Get the latest analysis from Firebase"""
    try:
        doc_ref = db.collection('analyses').document('latest')
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict()
        else:
            raise HTTPException(status_code=404, detail="No analysis data found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read from Firebase: {str(e)}")

@app.get("/")
async def root():
    return {
        "message": "Welcome to the Analysis API",
        "endpoints": {
            "/update": "Get and save latest analysis of defense stocks, news, and pizza data",
            "/read": "Get the most recent analysis from the database",
            "/pizza": "Get real-time pizza place busyness data around the Pentagon"
        }
    }

@app.get("/read")
async def read_latest_analysis():
    """Get the most recent analysis from Firebase"""
    try:
        return get_latest_from_firebase()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/pizza")
async def get_pizza_analysis():
    """Get pizza place analysis around the Pentagon"""
    try:
        return get_pentagon_pizza_data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/update")
async def get_analysis():
    try:
        # Get defense stocks data
        stocks_data = defense_stocks.get_defense_stocks_data()
        
        # Calculate stocks statistics
        valid_changes = [stock['change_percent'] for stock in stocks_data if stock['change_percent'] is not None]
        avg_stock_change = sum(valid_changes) / len(valid_changes) if valid_changes else 0
        max_change = max(valid_changes) if valid_changes else 0
        min_change = min(valid_changes) if valid_changes else 0
        
        # Get news analysis
        news_results = news_analysis.calculate_doomsday_probability()
        
        # Get pizza analysis
        pizza_data = get_pentagon_pizza_data()
        
        # Get current timestamp
        current_time = datetime.now().isoformat()
        
        # Prepare response data
        response_data = {
            "metadata": {
                "timestamp": current_time,
                "data_sources": ["defense_stocks", "news_analysis", "local_pizza_analysis"],
                "analysis_time": current_time
            },
            "defense_stocks_analysis": {
                "statistics": {
                    "average_change_percent": round(avg_stock_change, 2),
                    "max_change_percent": round(max_change, 2),
                    "min_change_percent": round(min_change, 2),
                    "stocks_analyzed": len(stocks_data)
                },
                "market_summary": {
                    "overall_trend": "bullish" if avg_stock_change > 0 else "bearish",
                    "volatility": abs(max_change - min_change)
                },
                "detailed_stocks_data": [
                    {
                        "ticker": stock['ticker'],
                        "current_price": stock['current_price'],
                        "change_percent": stock['change_percent'],
                        "status": "increasing" if stock['change_percent'] > 0 else "decreasing" if stock['change_percent'] < 0 else "stable"
                    } for stock in stocks_data
                ]
            },
            "news_analysis": {
                "doomsday_metrics": {
                    "probability": news_results['doomsday_probability'],
                    "analysis_basis": news_results['analysis_basis'],
                    "interpretation": news_results['interpretation']
                },
                "detailed_news_analysis": {
                    "articles_analyzed": len(news_results['detailed_results']),
                    "articles": [
                        {
                            "title": article['title'],
                            "published": article['published'],
                            "source": article['source'],
                            "severity": article['analysis']['severity'],
                            "explanation": article['analysis']['explanation'],
                            "link": article['link']
                        } for article in news_results['detailed_results']
                    ]
                },
                "severity_distribution": calculate_severity_distribution(news_results['detailed_results'])
            },
            "local_pizza_analysis": {
                "metadata": pizza_data["metadata"],
                "summary": {
                    "total_places": pizza_data["metadata"]["total_pizza_places_found"],
                    "places_with_live_data": pizza_data["metadata"]["places_with_current_data"],
                    "location": "Pentagon Area",
                    "radius_miles": 5
                },
                "busyness_metrics": {
                    "unusually_busy_threshold": 20,  # % above normal
                    "unusually_quiet_threshold": -20,  # % below normal
                    "places_by_status": calculate_pizza_status_distribution(pizza_data["pizza_places"])
                },
                "detailed_places": pizza_data["pizza_places"]
            }
        }
        
        # Save to Firebase
        save_to_firebase(response_data)
        
        return response_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def calculate_severity_distribution(articles):
    """Calculate the distribution of severity scores across articles"""
    severity_ranges = {
        "low": 0,      # 0.0 - 0.25
        "medium": 0,   # 0.26 - 0.5
        "high": 0,     # 0.51 - 0.75
        "critical": 0  # 0.76 - 1.0
    }
    
    for article in articles:
        severity = article['analysis']['severity']
        if severity <= 0.25:
            severity_ranges["low"] += 1
        elif severity <= 0.5:
            severity_ranges["medium"] += 1
        elif severity <= 0.75:
            severity_ranges["high"] += 1
        else:
            severity_ranges["critical"] += 1
    
    total = len(articles)
    return {
        "counts": severity_ranges,
        "percentages": {
            level: round((count / total * 100), 2) if total > 0 else 0 
            for level, count in severity_ranges.items()
        }
    }

def calculate_pizza_status_distribution(places):
    """Calculate distribution of pizza places by their busyness status"""
    distribution = {
        "very_busy": [],    # >50% busier than normal
        "busy": [],         # 20-50% busier than normal
        "typical": [],      # within 20% of normal
        "quiet": [],        # 20-50% less busy than normal
        "very_quiet": []    # >50% less busy than normal
    }
    
    for place in places:
        percent_diff = place["current_status"]["percent_difference"]
        if percent_diff > 50:
            distribution["very_busy"].append(place["name"])
        elif percent_diff > 20:
            distribution["busy"].append(place["name"])
        elif percent_diff < -50:
            distribution["very_quiet"].append(place["name"])
        elif percent_diff < -20:
            distribution["quiet"].append(place["name"])
        else:
            distribution["typical"].append(place["name"])
    
    return {
        "counts": {
            status: len(places) for status, places in distribution.items()
        },
        "places": distribution,
        "summary": {
            "total_unusually_busy": len(distribution["very_busy"]) + len(distribution["busy"]),
            "total_unusually_quiet": len(distribution["very_quiet"]) + len(distribution["quiet"]),
            "total_typical": len(distribution["typical"])
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

import os
import json
import populartimes
from datetime import datetime
from dotenv import load_dotenv
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from threading import Lock

# Pydantic Models
class CurrentStatus(BaseModel):
    current_popularity: int
    typical_popularity: int
    busyness_ratio: float
    percent_difference: float
    status: str

class Ratings(BaseModel):
    google_rating: Optional[float] = None
    number_of_ratings: Optional[int] = None

class WeeklyData(BaseModel):
    hourly_data: List[int]
    peak_hour: int
    peak_popularity: int

class PizzaPlace(BaseModel):
    name: str
    address: str
    coordinates: Dict[str, Any] = Field(default_factory=dict)
    current_status: CurrentStatus
    ratings: Ratings
    place_types: List[str] = Field(default_factory=list)
    weekly_popularity: Dict[str, WeeklyData]
    wait_time_minutes: Optional[int] = None
    time_spent_minutes: Optional[int] = None

class PizzaMetadata(BaseModel):
    timestamp: str
    location: str
    radius_miles: int
    search_type: str
    current_time: str
    current_day: str
    total_pizza_places_found: int
    places_with_current_data: int

class PizzaAnalysis(BaseModel):
    metadata: PizzaMetadata
    pizza_places: List[PizzaPlace]

def safe_extract_time(value):
    """Safely extract time value from various data types returned by populartimes"""
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, list):
        return value[0] if value and isinstance(value[0], int) else None
    if isinstance(value, dict):
        # Sometimes populartimes returns dict structures, ignore them
        return None
    return None

def is_pizza_place(place):
    if "types" in place and any("pizza" in t.lower() for t in place["types"]):
        return True
    if "name" in place and "pizza" in place["name"].lower():
        return True
    return False

def fetch_pizza_data():
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    
    pentagon_lat, pentagon_lng = 38.8719, -77.0563
    degree_offset = 0.0145 * 5  # 5 miles
    
    bound_lower = (pentagon_lat - degree_offset, pentagon_lng - degree_offset)
    bound_upper = (pentagon_lat + degree_offset, pentagon_lng + degree_offset)
    
    places = []
    place_types = ["restaurant", "meal_takeaway"]
    
    try:
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
                    weekly_schedule[day["name"]] = WeeklyData(
                        hourly_data=day["data"],
                        peak_hour=day["data"].index(max(day["data"])),
                        peak_popularity=max(day["data"])
                    )

                place_data = PizzaPlace(
                    name=place["name"],
                    address=place["address"],
                    coordinates=place.get("coordinates", {}),
                    current_status=CurrentStatus(
                        current_popularity=place["current_popularity"],
                        typical_popularity=typical_popularity,
                        busyness_ratio=round(busyness_ratio, 2),
                        percent_difference=percent_difference,
                        status="busier" if percent_difference > 0 else "less busy" if percent_difference < 0 else "typical"
                    ),
                    ratings=Ratings(
                        google_rating=place.get("rating", None),
                        number_of_ratings=place.get("rating_n", None)
                    ),
                    place_types=place.get("types", []),
                    weekly_popularity=weekly_schedule,
                    wait_time_minutes=safe_extract_time(place.get("time_wait")),
                    time_spent_minutes=safe_extract_time(place.get("time_spent"))
                )
                busy_places.append(place_data)
        
        # Sort by how unusually busy they are
        busy_places.sort(key=lambda x: abs(x.current_status.percent_difference), reverse=True)
        
        # Limit to maximum of 5 places
        busy_places = busy_places[:5]
        
        metadata = PizzaMetadata(
            timestamp=datetime.now().isoformat(),
            location="Pentagon Area",
            radius_miles=5,
            search_type="Pizza Places",
            current_time=f"{current_hour}:00",
            current_day=current_day,
            total_pizza_places_found=len(unique_places),
            places_with_current_data=len(busy_places)
        )
        
        pizza_analysis = PizzaAnalysis(
            metadata=metadata,
            pizza_places=busy_places
        )
        
        print(f"Pizza data fetched: {len(busy_places)} places with current data")
        return pizza_analysis
        
    except Exception as e:
        print(f"Error fetching pizza data: {str(e)}")
        # Return empty data on error
        metadata = PizzaMetadata(
            timestamp=datetime.now().isoformat(),
            location="Pentagon Area",
            radius_miles=5,
            search_type="Pizza Places",
            current_time=f"{datetime.now().hour}:00",
            current_day=datetime.now().strftime("%A"),
            total_pizza_places_found=0,
            places_with_current_data=0
        )
        
        return PizzaAnalysis(
            metadata=metadata,
            pizza_places=[]
        )
        
# Global variable to store pizza data
pizza_data: Optional[PizzaAnalysis] = None
lock = Lock()

def update_pizza_data():
    global pizza_data
    with lock:
        pizza_data = fetch_pizza_data()

def get_pizza_data():
    with lock:
        return pizza_data.copy() if pizza_data else None
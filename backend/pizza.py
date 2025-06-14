import os
import json
import populartimes
from datetime import datetime
from dotenv import load_dotenv
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# Pydantic Models
class CurrentStatus(BaseModel):
    """Model for current pizza place status"""
    current_popularity: int
    typical_popularity: int
    busyness_ratio: float
    percent_difference: float
    status: str

class Ratings(BaseModel):
    """Model for pizza place ratings"""
    google_rating: Optional[float] = None
    number_of_ratings: Optional[int] = None

class WeeklyData(BaseModel):
    """Model for weekly popularity data"""
    hourly_data: List[int]
    peak_hour: int
    peak_popularity: int

class PizzaPlace(BaseModel):
    """Model for individual pizza place data"""
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
    """Model for pizza analysis metadata"""
    timestamp: str
    location: str
    radius_miles: int
    search_type: str
    current_time: str
    current_day: str
    total_pizza_places_found: int
    places_with_current_data: int

class PizzaAnalysis(BaseModel):
    """Model for complete pizza analysis"""
    metadata: PizzaMetadata
    pizza_places: List[PizzaPlace]

# Global variable to store pizza data
pizza_data: Optional[PizzaAnalysis] = None

def is_pizza_place(place):
    """Check if a place is a pizza establishment"""
    # Check if "pizza" is in the place types
    if "types" in place and any("pizza" in t.lower() for t in place["types"]):
        return True
    # Check if "pizza" is in the name
    if "name" in place and "pizza" in place["name"].lower():
        return True
    return False

def update_pentagon_pizza_data() -> PizzaAnalysis:
    """Update and return pizza place data around the Pentagon"""
    global pizza_data
    
    print("Updating pizza data...")
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    
    # Pentagon coordinates and search area
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
                    wait_time_minutes=place.get("time_wait", None),
                    time_spent_minutes=place.get("time_spent", None)
                )
                busy_places.append(place_data)
        
        # Sort by how unusually busy they are
        busy_places.sort(key=lambda x: abs(x.current_status.percent_difference), reverse=True)
        
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
        
        pizza_data = PizzaAnalysis(
            metadata=metadata,
            pizza_places=busy_places
        )
        
        print(f"Pizza data updated: {len(busy_places)} places with current data")
        return pizza_data
        
    except Exception as e:
        print(f"Error updating pizza data: {str(e)}")
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
        
        pizza_data = PizzaAnalysis(
            metadata=metadata,
            pizza_places=[]
        )
        return pizza_data

def get_pentagon_pizza_data() -> Optional[PizzaAnalysis]:
    """Get current pizza data from memory"""
    return pizza_data

def analyze_takeout_places():
    """Legacy function - use get_pentagon_pizza_data() instead"""
    # Load API key from environment
    load_dotenv()
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    
    if not api_key:
        raise ValueError("Please set GOOGLE_MAPS_API_KEY in your .env file")

    # Define the search area around the Pentagon
    # These coordinates create a roughly 5-mile box around the Pentagon
    # 1 mile ≈ 0.0145 degrees at this latitude
    pentagon_lat, pentagon_lng = 38.8719, -77.0563
    degree_offset = 0.0145 * 5  # 5 miles
    
    bound_lower = (pentagon_lat - degree_offset, pentagon_lng - degree_offset)  # SW corner
    bound_upper = (pentagon_lat + degree_offset, pentagon_lng + degree_offset)  # NE corner

    # Search for pizza places - we'll search both restaurant and meal_takeaway
    # and filter for pizza places afterwards
    place_types = ["restaurant", "meal_takeaway"]
    
    try:
        places = []
        for place_type in place_types:
            results = populartimes.get(
                api_key,
                [place_type],
                bound_lower,
                bound_upper,
                radius=8047  # 5 miles in meters
            )
            # Filter for pizza places only
            pizza_places = [place for place in results if is_pizza_place(place)]
            places.extend(pizza_places)

        # Remove duplicates based on place name and address
        unique_places = []
        seen = set()
        for place in places:
            key = (place["name"], place["address"])
            if key not in seen:
                seen.add(key)
                unique_places.append(place)
        places = unique_places

        # Get current time
        current_hour = datetime.now().hour
        current_day = datetime.now().strftime("%A")

        # Prepare JSON response
        response = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "location": "Pentagon Area",
                "radius_miles": 5,
                "search_type": "Pizza Places",
                "current_time": f"{current_hour}:00",
                "current_day": current_day,
                "total_pizza_places_found": len(places)
            },
            "pizza_places": []
        }

        # Filter and sort places by current popularity
        busy_places = []
        for place in places:
            if "current_popularity" in place:
                # Get the typical popularity for this time
                typical_popularity = 0
                for day in place["populartimes"]:
                    if day["name"] == current_day:
                        typical_popularity = day["data"][current_hour]
                        break
                
                # Calculate how unusual the current busyness is
                busyness_ratio = (place["current_popularity"] / typical_popularity) if typical_popularity > 0 else 1
                
                # Get the full weekly schedule
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
                        "busyness_ratio": round(busyness_ratio, 2)
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
        busy_places.sort(key=lambda x: x["current_status"]["busyness_ratio"], reverse=True)
        response["pizza_places"] = busy_places

        # Print JSON output
        print(json.dumps(response, indent=2))
        
        # Save to file
        with open('pentagon_pizza_analysis.json', 'w') as f:
            json.dump(response, f, indent=2)

    except Exception as e:
        error_response = {
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        print(json.dumps(error_response, indent=2))

if __name__ == "__main__":
    data = update_pentagon_pizza_data()
    print(data.model_dump_json(indent=2))
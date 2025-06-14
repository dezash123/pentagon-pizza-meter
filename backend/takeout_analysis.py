import os
import json
import populartimes
from datetime import datetime
from dotenv import load_dotenv

def is_pizza_place(place):
    """Check if a place is a pizza establishment"""
    # Check if "pizza" is in the place types
    if "types" in place and any("pizza" in t.lower() for t in place["types"]):
        return True
    # Check if "pizza" is in the name
    if "name" in place and "pizza" in place["name"].lower():
        return True
    return False

def analyze_takeout_places():
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
    analyze_takeout_places() 
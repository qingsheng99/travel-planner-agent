from typing import List, Dict
import httpx
from app.schemas.config import settings


def search_pois(destination: str, category: str = "attractions") -> List[Dict]:
    if not settings.MAPS_API_KEY:
        return [
            {
                "name": f"{destination} 热门景点",
                "rating": "N/A",
                "address": "API key not configured",
                "category": category
            }
        ]
    
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                "https://maps.googleapis.com/maps/api/place/textsearch/json",
                params={
                    "key": settings.MAPS_API_KEY,
                    "query": f"{category} in {destination}",
                    "language": "zh-CN"
                }
            )
            data = response.json()
            
            return [
                {
                    "name": place["name"],
                    "rating": place.get("rating", "N/A"),
                    "address": place.get("formatted_address", ""),
                    "category": category,
                    "place_id": place.get("place_id", "")
                }
                for place in data.get("results", [])[:10]
            ]
    except Exception as e:
        return [{"name": f"Error: {str(e)}", "category": category}]

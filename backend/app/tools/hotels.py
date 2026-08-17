from typing import List, Dict, Optional
import httpx
from app.schemas.config import settings


def search_hotels(
    destination: str,
    dates: Optional[Dict] = None,
    budget: Optional[Dict] = None
) -> List[Dict]:
    if not settings.HOTELS_API_KEY:
        min_price = budget.get("min", 200) if budget else 200
        max_price = budget.get("max", 1000) if budget else 1000
        
        return [
            {
                "name": f"{destination} 酒店",
                "price": f"{min_price}-{max_price}",
                "rating": "4.5",
                "address": destination,
                "amenities": ["WiFi", "早餐", "停车场"]
            }
        ]
    
    try:
        with httpx.Client(timeout=10.0) as client:
            return [
                {
                    "name": f"{destination} 豪华酒店",
                    "price": 888,
                    "currency": "CNY",
                    "rating": 4.7,
                    "stars": 5,
                    "address": destination,
                    "amenities": ["免费WiFi", "早餐", "游泳池", "健身房"]
                },
                {
                    "name": f"{destination} 商务酒店",
                    "price": 398,
                    "currency": "CNY",
                    "rating": 4.3,
                    "stars": 4,
                    "address": destination,
                    "amenities": ["免费WiFi", "早餐"]
                }
            ]
    except Exception as e:
        return [{"name": f"Error: {str(e)}"}]

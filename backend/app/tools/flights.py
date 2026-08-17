from typing import List, Dict, Optional
import httpx
from datetime import datetime
from app.schemas.config import settings


def search_flights(
    destination: str,
    origin: str = "",
    dates: Optional[Dict] = None
) -> List[Dict]:
    if not settings.FLIGHTS_API_KEY:
        return [
            {
                "airline": "示例航班",
                "price": "N/A",
                "departure": dates.get("start", "") if dates else "",
                "arrival": destination,
                "duration": "N/A"
            }
        ]
    
    try:
        start_date = dates.get("start", datetime.now().strftime("%Y-%m-%d")) if dates else datetime.now().strftime("%Y-%m-%d")
        
        with httpx.Client(timeout=10.0) as client:
            return [
                {
                    "airline": "示例航空",
                    "flight_number": "CA1234",
                    "price": 1200,
                    "currency": "CNY",
                    "departure_time": f"{start_date} 08:00",
                    "arrival_time": f"{start_date} 11:00",
                    "origin": origin or "出发地",
                    "destination": destination,
                    "duration": "3h"
                }
            ]
    except Exception as e:
        return [{"airline": f"Error: {str(e)}"}]

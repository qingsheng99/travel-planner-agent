from typing import Dict, Optional
import httpx
from app.schemas.config import settings


def get_weather(destination: str) -> Dict:
    if not settings.WEATHER_API_KEY:
        return {
            "temperature": "N/A",
            "condition": "API key not configured",
            "forecast": []
        }
    
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                "https://api.weatherapi.com/v1/forecast.json",
                params={
                    "key": settings.WEATHER_API_KEY,
                    "q": destination,
                    "days": 7
                }
            )
            data = response.json()
            
            return {
                "temperature": data["current"]["temp_c"],
                "condition": data["current"]["condition"]["text"],
                "humidity": data["current"]["humidity"],
                "wind": data["current"]["wind_kph"],
                "forecast": [
                    {
                        "date": day["date"],
                        "max_temp": day["day"]["maxtemp_c"],
                        "min_temp": day["day"]["mintemp_c"],
                        "condition": day["day"]["condition"]["text"]
                    }
                    for day in data.get("forecast", {}).get("forecastday", [])
                ]
            }
    except Exception as e:
        return {
            "temperature": "N/A",
            "condition": f"Error: {str(e)}",
            "forecast": []
        }

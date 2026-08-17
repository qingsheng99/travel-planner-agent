from typing import TypedDict, Annotated, List, Dict, Optional
import operator


class TravelState(TypedDict):
    messages: Annotated[list, operator.add]
    user_id: Optional[int]
    trip_id: Optional[int]
    destination: Optional[str]
    dates: Optional[Dict]
    budget: Optional[Dict]
    travelers: Optional[int]
    preferences: Optional[Dict]
    weather_info: Optional[Dict]
    flight_info: Optional[List[Dict]]
    hotel_info: Optional[List[Dict]]
    poi_info: Optional[List[Dict]]
    itinerary: Optional[Dict]
    next: Optional[str]

from app.graph.state import TravelState


def supervisor(state: TravelState) -> str:
    next_step = state.get("next", "finish")
    
    routes = {
        "weather": "weather",
        "flights": "flights",
        "hotels": "hotels",
        "pois": "pois",
        "itinerary": "itinerary",
        "finish": "end"
    }
    
    return routes.get(next_step, "end")

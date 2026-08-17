from langgraph.graph import StateGraph, END
from app.graph.state import TravelState
from app.graph.nodes import (
    intent_router,
    weather_node,
    flights_node,
    hotels_node,
    pois_node,
    itinerary_node
)
from app.graph.supervisor import supervisor


def build_travel_graph():
    workflow = StateGraph(TravelState)
    
    workflow.add_node("intent_router", intent_router)
    workflow.add_node("weather", weather_node)
    workflow.add_node("flights", flights_node)
    workflow.add_node("hotels", hotels_node)
    workflow.add_node("pois", pois_node)
    workflow.add_node("itinerary", itinerary_node)
    
    workflow.set_entry_point("intent_router")
    
    workflow.add_conditional_edges(
        "intent_router",
        supervisor,
        {
            "weather": "weather",
            "flights": "flights",
            "hotels": "hotels",
            "pois": "pois",
            "itinerary": "itinerary",
            "end": END
        }
    )
    
    workflow.add_edge("weather", "intent_router")
    workflow.add_edge("flights", "intent_router")
    workflow.add_edge("hotels", "intent_router")
    workflow.add_edge("pois", "intent_router")
    workflow.add_edge("itinerary", END)
    
    return workflow.compile()


travel_graph = build_travel_graph()

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from app.schemas.config import settings
from app.graph.state import TravelState
from app.tools.weather import get_weather
from app.tools.flights import search_flights
from app.tools.hotels import search_hotels
from app.tools.maps import search_pois
from app.rag.retriever import retrieve_knowledge

llm = ChatOpenAI(
    model=settings.OPENAI_MODEL,
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.OPENAI_API_BASE,
    temperature=0.7
)


def intent_router(state: TravelState) -> TravelState:
    system_prompt = """你是一个旅行规划助手的意图分类器。
    根据用户的消息，判断下一步需要调用什么工具或者直接回复。
    
    可能的下一步：
    - weather: 需要查询天气信息
    - flights: 需要查询航班信息
    - hotels: 需要查询酒店信息
    - pois: 需要查询景点/兴趣点
    - itinerary: 需要生成行程规划
    - finish: 信息足够，可以直接回复用户
    
    只返回下一步的关键词，不要其他内容。"""
    
    messages = [SystemMessage(content=system_prompt)] + state["messages"][-5:]
    response = llm.invoke(messages)
    next_step = response.content.strip().lower()
    
    valid_next = ["weather", "flights", "hotels", "pois", "itinerary", "finish"]
    if next_step not in valid_next:
        next_step = "finish"
    
    return {"next": next_step}


def weather_node(state: TravelState) -> TravelState:
    if state.get("destination"):
        weather = get_weather(state["destination"])
        return {"weather_info": weather}
    return {}


def flights_node(state: TravelState) -> TravelState:
    if state.get("destination"):
        flights = search_flights(
            destination=state["destination"],
            dates=state.get("dates", {})
        )
        return {"flight_info": flights}
    return {}


def hotels_node(state: TravelState) -> TravelState:
    if state.get("destination"):
        hotels = search_hotels(
            destination=state["destination"],
            dates=state.get("dates", {}),
            budget=state.get("budget", {})
        )
        return {"hotel_info": hotels}
    return {}


def pois_node(state: TravelState) -> TravelState:
    if state.get("destination"):
        pois = search_pois(state["destination"])
        knowledge = retrieve_knowledge(state["messages"][-1].content if state["messages"] else "")
        return {"poi_info": pois, "messages": [SystemMessage(content=f"参考知识：{knowledge}")]}
    return {}


def itinerary_node(state: TravelState) -> TravelState:
    system_prompt = """你是一位专业的旅行规划师。
    根据收集到的天气、航班、酒店、景点信息，为用户生成一份详细的行程规划。
    行程要包含每日安排、交通建议、餐饮推荐、注意事项等。"""
    
    context = f"""
    目的地：{state.get('destination', '未指定')}
    日期：{state.get('dates', {})}
    预算：{state.get('budget', {})}
    出行人数：{state.get('travelers', 1)}
    天气信息：{state.get('weather_info', {})}
    航班信息：{state.get('flight_info', [])}
    酒店信息：{state.get('hotel_info', [])}
    景点信息：{state.get('poi_info', [])}
    """
    
    messages = [
        SystemMessage(content=system_prompt),
        SystemMessage(content=context),
    ] + state["messages"]
    
    response = llm.invoke(messages)
    return {"itinerary": {"content": response.content}, "next": "finish"}

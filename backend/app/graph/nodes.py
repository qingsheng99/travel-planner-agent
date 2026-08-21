"""
工作流节点模块。

定义旅行规划 Agent 工作流中的各个处理节点，包括：
- intent_router：意图分类，将用户消息路由到对应工具节点
- weather_node：天气查询节点
- flights_node：航班查询节点
- hotels_node：酒店查询节点
- pois_node：景点/兴趣点查询节点
- itinerary_node：行程规划生成节点
"""

import asyncio
from typing import Any

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from app.schemas.config import settings
from app.graph.state import TravelState
from app.tools.weather import get_weather
from app.tools.flights import search_flights
from app.tools.hotels import search_hotels
from app.tools.maps import search_pois

# 初始化大语言模型实例，用于意图分类和行程生成
llm = ChatOpenAI(
    model=settings.OPENAI_MODEL,
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.OPENAI_API_BASE,
    temperature=0.7
)


async def _stream_llm(messages) -> str:
    """流式调用 LLM 并聚合完整文本。

    使用 astream 而非 ainvoke，使 astream_events 能够捕获
    on_chat_model_stream 事件，从而向前端推送逐 token 的流式输出。

    Args:
        messages: 发送给 LLM 的消息列表。

    Returns:
        聚合后的完整回复文本。
    """
    parts: list[str] = []
    async for chunk in llm.astream(messages):
        text = getattr(chunk, "content", None)
        if text is None:
            text = str(chunk)
        # 部分模型以内容块列表返回，需展开提取文本
        if isinstance(text, list):
            text = "".join(
                b.get("text", "") if isinstance(b, dict) else str(b)
                for b in text
            )
        if text:
            parts.append(text)
    return "".join(parts)


async def intent_router(state: TravelState) -> TravelState:
    """意图分类节点：根据用户消息判断下一步操作。

    使用 LLM 对用户最近的消息进行意图分类，
    返回下一步应执行的任务类型。

    Args:
        state: 当前工作流状态，包含对话消息历史。

    Returns:
        更新后的状态，包含 "next" 字段指示下一步操作：
        - "weather" / "flights" / "hotels" / "pois" / "itinerary" / "respond"
    """
    # 系统提示词，指导 LLM 对用户意图进行分类
    system_prompt = """你是一个旅行规划助手的意图分类器。
    根据用户的消息，判断下一步需要调用什么工具或者直接回复。
    
    可能的下一步：
    - weather: 需要查询天气信息
    - flights: 需要查询航班信息
    - hotels: 需要查询酒店信息
    - pois: 需要查询景点/兴趣点
    - itinerary: 需要生成行程规划
    - respond: 无需查询工具，直接回答用户

    只返回下一步的关键词，不要其他内容。"""
    
    # 取最近 5 条消息进行意图判断
    messages = [SystemMessage(content=system_prompt)] + state["messages"][-5:]
    # 流式调用 LLM 进行意图分类（流式仅用于捕获 token 事件，此处聚合结果）
    next_step = (await _stream_llm(messages)).strip().lower()
    
    # 校验分类结果，确保返回有效的下一步操作
    valid_next = ["weather", "flights", "hotels", "pois", "itinerary", "respond"]
    if next_step not in valid_next:
        next_step = "respond"  # 无效分类仍给用户一个自然语言回复
    
    return {"next": next_step}


async def weather_node(state: TravelState) -> TravelState:
    """天气查询节点：获取目的地的天气信息（带 Redis 缓存）。

    Args:
        state: 当前工作流状态，需包含 destination 字段。

    Returns:
        更新后的状态，包含 weather_info 字段（若目的地存在）。
    """

    async def _fetch() -> dict:
        """内部封装：调用实际天气工具（同步函数放入线程池）。"""
        return await asyncio.to_thread(get_weather, state["destination"])

    if state.get("destination"):
        weather = await _cached_tool("weather", state["destination"], _fetch)
        return {"weather_info": weather}
    return {}  # 无目的地时返回空


async def flights_node(state: TravelState) -> TravelState:
    """航班查询节点：搜索目的地的航班信息（带 Redis 缓存）。

    Args:
        state: 当前工作流状态，需包含 destination 和 dates 字段。

    Returns:
        更新后的状态，包含 flight_info 字段（若目的地存在）。
    """

    async def _fetch() -> list:
        """内部封装：调用实际航班搜索工具。"""
        return await asyncio.to_thread(
            search_flights,
            destination=state["destination"],
            dates=state.get("dates", {}),
        )

    if state.get("destination"):
        key_tail = _safe_key(str(state.get("dates", {})))
        flights = await _cached_tool("flights", f"{state['destination']}:{key_tail}", _fetch)
        return {"flight_info": flights}
    return {}


async def hotels_node(state: TravelState) -> TravelState:
    """酒店查询节点：搜索目的地的酒店信息（带 Redis 缓存）。

    Args:
        state: 当前工作流状态，需包含 destination、dates 和 budget 字段。

    Returns:
        更新后的状态，包含 hotel_info 字段（若目的地存在）。
    """

    async def _fetch() -> list:
        """内部封装：调用实际酒店搜索工具。"""
        return await asyncio.to_thread(
            search_hotels,
            destination=state["destination"],
            dates=state.get("dates", {}),
            budget=state.get("budget", {}),
        )

    if state.get("destination"):
        key_tail = _safe_key(f"{state.get('dates', {})}:{state.get('budget', {})}")
        hotels = await _cached_tool("hotels", f"{state['destination']}:{key_tail}", _fetch)
        return {"hotel_info": hotels}
    return {}


async def pois_node(state: TravelState) -> TravelState:
    """景点查询节点：搜索目的地的景点/兴趣点信息（带 Redis 缓存）。

    同步查询景点 POI 数据，并从 RAG 知识库检索相关背景知识，
    POI 与知识检索结果均带缓存，RAG 失败时不影响主对话。

    Args:
        state: 当前工作流状态，需包含 destination 字段。

    Returns:
        更新后的状态，包含 poi_info 字段以及知识参考消息（若目的地存在）。
    """

    async def _fetch_pois() -> list:
        return await asyncio.to_thread(search_pois, state["destination"])

    async def _fetch_knowledge() -> str:
        last_message = state["messages"][-1].content if state.get("messages") else ""
        # _retrieve_knowledge 本身是异步协程且内部已用 to_thread 包装同步检索，
        # 这里必须 await，否则会产生未 await 的协程导致 RAG 检索结果丢失。
        return await _retrieve_knowledge(last_message)

    if state.get("destination"):
        pois = await _cached_tool("pois", state["destination"], _fetch_pois)
        knowledge = ""
        try:
            knowledge = await _cached_tool("rag", state["destination"], _fetch_knowledge)
        except Exception:  # noqa: BLE001
            knowledge = ""
        updates: dict[str, Any] = {"poi_info": pois}
        if knowledge:
            updates["messages"] = [SystemMessage(content=f"参考知识：{knowledge}")]
        return updates
    return {}


async def itinerary_node(state: TravelState) -> TravelState:
    """行程规划节点：基于收集到的所有信息生成详细行程。

    将天气、航班、酒店、景点等信息汇总，交给 LLM 生成完整的行程规划。

    Args:
        state: 当前工作流状态，应包含 destination、dates、budget、travelers
               以及 weather_info、flight_info、hotel_info、poi_info 等字段。

    Returns:
        更新后的状态，包含 itinerary 字段，并设置 next 为 "finish" 结束流程。
    """
    # 系统提示词，指导 LLM 作为旅行规划师生成行程
    system_prompt = """你是一位专业的旅行规划师。
    根据收集到的天气、航班、酒店、景点信息，为用户生成一份详细的行程规划。
    行程要包含每日安排、交通建议、餐饮推荐、注意事项等。
    生成时务必贴合用户的偏好（如饮食、兴趣、出行方式、预算等）。"""
    
    # 汇总所有收集到的信息作为上下文
    context = f"""
    目的地：{state.get('destination', '未指定')}
    日期：{state.get('dates', {})}
    预算：{state.get('budget', {})}
    出行人数：{state.get('travelers', 1)}
    用户偏好：{state.get('preferences', {})}
    天气信息：{state.get('weather_info', {})}
    航班信息：{state.get('flight_info', [])}
    酒店信息：{state.get('hotel_info', [])}
    景点信息：{state.get('poi_info', [])}
    """
    
    # 构造消息列表：系统提示 + 上下文 + 对话历史
    messages = [
        SystemMessage(content=system_prompt),
        SystemMessage(content=context),
    ] + state["messages"]
    
    # 流式调用 LLM 生成行程规划（逐 token 事件由 stream 层实时推送）
    content = await _stream_llm(messages)
    return {
        "itinerary": {"content": content},
        "assistant_response": content,
        "next": "finish",
    }


async def response_node(state: TravelState) -> TravelState:
    """将单项查询结果或普通问题组织为最终的用户可读回复。"""
    system_prompt = """你是一位专业的旅行规划师。
请基于提供的旅行上下文回答用户最后的问题。不要编造未提供的实时数据；
缺少目的地、日期或预算时，明确说明还需要哪些信息。"""
    context = {
        "destination": state.get("destination"),
        "dates": state.get("dates"),
        "budget": state.get("budget"),
        "travelers": state.get("travelers"),
        "weather": state.get("weather_info"),
        "flights": state.get("flight_info"),
        "hotels": state.get("hotel_info"),
        "pois": state.get("poi_info"),
    }
    content = await _stream_llm(
        [
            SystemMessage(content=system_prompt),
            SystemMessage(content=f"旅行上下文：{context}"),
            *state.get("messages", []),
        ]
    )
    return {"assistant_response": content, "next": "finish"}


async def _retrieve_knowledge(query: str) -> str:
    """在单独线程中执行可选 RAG 检索，失败时不影响主对话。"""
    if not query:
        return ""
    try:
        from app.rag.retriever import retrieve_knowledge

        return await asyncio.to_thread(retrieve_knowledge, query)
    except Exception:
        return ""


def _safe_key(value: str) -> str:
    """将可能含空格 / 特殊字符的键片段压缩为 Redis 安全的简写。

    通过哈希生成固定长度的键，避免因目的地为空或含有空格导致键过大 / 表意不明。
    """
    import hashlib

    norm = value.strip().replace(" ", "")
    return hashlib.md5(norm.encode("utf-8")).hexdigest()[:12]


async def _cached_tool(namespace: str, discriminator: str, fetch) -> Any:
    """带 Redis 缓存地执行一个工具查询。

    优先尝试读取缓存；缓存未命中时调用 fetch 获取真实结果并回填缓存。
    若 Redis 不可用或出错，则静默降级为直接调用，不影响主流程。

    参数:
        namespace: 缓存命名空间，如 "weather" / "flights" / "hotels" / "pois" / "rag"。
        discriminator: 用于区分不同查询的关键字（如目的地、日期、预算）。
        fetch: 一个无参的异步可调用对象，返回真实的工具结果。

    返回:
        工具查询结果（缓存命中则直接返回缓存值）。
    """
    cache_key = _safe_key(discriminator)

    try:
        from app.core.redis import cache_get, cache_set, cache_key as _cache_key_builder

        full_key = _cache_key_builder("travel_tool", namespace, cache_key)
        cached = await cache_get(full_key)
        if cached is not None:
            return cached
    except Exception:  # noqa: BLE001
        # Redis 不可用时降级为直连调用
        return await fetch()

    result = await fetch()

    try:
        from app.core.redis import cache_set, cache_key as _cache_key_builder

        await cache_set(_cache_key_builder("travel_tool", namespace, cache_key), result)
    except Exception:  # noqa: BLE001
        pass

    return result

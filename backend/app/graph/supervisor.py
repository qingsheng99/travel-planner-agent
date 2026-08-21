"""
监督节点模块。

提供 supervisor 函数，根据当前状态中记录的下一步意图，
将工作流路由到对应的工具节点或结束节点。
"""

from app.graph.state import TravelState


def supervisor(state: TravelState) -> str:
    """监督节点：根据状态路由到下一个工作节点。

    读取 state 中的 "next" 字段，将其映射到对应的图节点名称，
    用于 LangGraph 的条件边路由。

    Args:
        state: 当前工作流状态，包含由 intent_router 设置的 "next" 字段。

    Returns:
        下一个要执行的节点名称：
        - "weather" / "flights" / "hotels" / "pois" / "itinerary" 分别对应各工具节点
        - "respond" 表示无需工具调用，直接生成回复
        - "end" 表示结束工作流
    """
    # 读取下一步意图，默认为 "finish"（即结束）
    next_step = state.get("next", "finish")
    
    # 意图到图节点的映射表
    routes = {
        "weather": "weather",      # 查询天气
        "flights": "flights",      # 查询航班
        "hotels": "hotels",        # 查询酒店
        "pois": "pois",            # 查询景点
        "itinerary": "plan",       # 生成行程
        "respond": "respond",      # 直接回复
        "finish": "end"            # 结束流程
    }
    
    # 返回映射后的节点名，未知意图默认结束
    return routes.get(next_step, "end")

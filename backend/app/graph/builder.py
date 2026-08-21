"""
工作流构建模块。

使用 LangGraph 的 StateGraph 构建旅行规划 Agent 的有向图工作流。
定义节点注册、条件边路由以及各节点间的连接关系，
最终编译为可执行的图实例。
"""

from langgraph.graph import StateGraph, END
from app.graph.state import TravelState
from app.graph.nodes import (
    intent_router,
    weather_node,
    flights_node,
    hotels_node,
    pois_node,
    itinerary_node,
    response_node,
)
from app.graph.supervisor import supervisor


def build_travel_graph():
    """构建旅行规划 Agent 的工作流图。

    注册所有处理节点，设置意图分类节点为入口，
    通过条件边将意图路由到对应的工具节点或完整规划节点。
    每条路径都在一次工具执行或一次规划生成后结束。

    Returns:
        编译后的 StateGraph 实例，可直接用于执行工作流。
    """
    # 创建基于 TravelState 的状态图
    workflow = StateGraph(TravelState)
    
    # 注册所有工作节点
    workflow.add_node("intent_router", intent_router)  # 意图分类
    workflow.add_node("weather", weather_node)          # 天气查询
    workflow.add_node("flights", flights_node)          # 航班查询
    workflow.add_node("hotels", hotels_node)            # 酒店查询
    workflow.add_node("pois", pois_node)                # 景点查询
    workflow.add_node("plan", itinerary_node)        # 行程生成
    workflow.add_node("respond", response_node)         # 通用自然语言回复
    
    # 设置入口节点为意图分类器
    workflow.set_entry_point("intent_router")
    
    # 从意图分类器出发的条件边：根据 supervisor 的返回值路由到不同节点
    workflow.add_conditional_edges(
        "intent_router",
        supervisor,                              # 路由决策函数
        {
            "weather": "weather",    # 路由到天气节点
            "flights": "flights",    # 路由到航班节点
            "hotels": "hotels",      # 路由到酒店节点
            "pois": "pois",          # 路由到景点节点
            "plan": "plan",            # 路由到行程生成节点
            "respond": "respond",    # 直接回复
            "end": END               # 结束工作流
        }
    )
    
    # 单项查询完成后生成回复，避免重复路由形成循环。
    workflow.add_edge("weather", "respond")
    workflow.add_edge("flights", "respond")
    workflow.add_edge("hotels", "respond")
    workflow.add_edge("pois", "respond")
    workflow.add_edge("respond", END)
    # 行程生成完成后直接结束
    workflow.add_edge("plan", END)
    
    # 编译图为可执行实例
    return workflow.compile()


# 全局单例：编译后的旅行规划工作流图
travel_graph = build_travel_graph()

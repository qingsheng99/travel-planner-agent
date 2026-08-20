"""
旅行规划 Agent 的状态定义模块。

定义整个 Agent 工作流中流转的状态数据结构 TravelState，
包含用户意图、目的地、日期、预算、天气/航班/酒店/景点信息以及最终行程等字段。
"""

from typing import TypedDict, Annotated, List, Dict, Optional
import operator


class TravelState(TypedDict, total=False):
    """旅行规划 Agent 的状态类型。

    作为 LangGraph 中各个节点之间传递的状态容器，
    记录了对话消息、用户需求以及各工具节点返回的结果数据。

    Attributes:
        messages: 对话消息列表，使用 operator.add 实现自动合并。
        user_id: 用户 ID，可选。
        trip_id: 行程 ID，可选。
        destination: 目的地名称，可选。
        dates: 出行日期信息（如 {"start": "2025-06-01", "end": "2025-06-05"}），可选。
        budget: 预算信息（如总预算、各分类预算），可选。
        travelers: 出行人数，可选。
        preferences: 用户偏好设置（如兴趣、饮食偏好等），可选。
        weather_info: 天气查询结果，可选。
        flight_info: 航班搜索结果列表，可选。
        hotel_info: 酒店搜索结果列表，可选。
        poi_info: 景点/兴趣点搜索结果列表，可选。
        itinerary: 最终生成的行程规划，可选。
        next: 下一步要执行的节点名称，由意图分类器设置。
        assistant_response: 最终返回给用户的自然语言回复。
    """
    messages: Annotated[list, operator.add]       # 对话消息历史，自动累加
    user_id: Optional[int]                         # 用户 ID
    trip_id: Optional[int]                         # 行程 ID
    destination: Optional[str]                     # 目的地
    dates: Optional[Dict]                          # 出行日期
    budget: Optional[Dict]                         # 预算信息
    travelers: Optional[int]                       # 出行人数
    preferences: Optional[Dict]                    # 用户偏好
    weather_info: Optional[Dict]                   # 天气信息
    flight_info: Optional[List[Dict]]              # 航班信息
    hotel_info: Optional[List[Dict]]               # 酒店信息
    poi_info: Optional[List[Dict]]                 # 景点信息
    itinerary: Optional[Dict]                      # 行程规划
    next: Optional[str]                            # 下一步路由
    assistant_response: Optional[str]              # 最终助手回复

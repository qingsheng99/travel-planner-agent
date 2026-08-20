"""
地图 POI 查询模块

提供搜索指定目的地兴趣点（POI，Points of Interest）的功能。
使用 Google Maps Places API 的文本搜索接口，支持按类别筛选景点、
餐厅、购物中心等场所。适用于旅行规划中的景点推荐场景。
"""

from typing import List, Dict
import httpx
from app.schemas.config import settings


def search_pois(destination: str, category: str = "attractions") -> List[Dict]:
    """
    搜索指定目的地的兴趣点（POI）。

    调用 Google Maps Places API 进行文本搜索，获取指定类别的地点列表。
    若 API 密钥未配置，返回包含提示信息的占位数据。

    参数:
        destination (str): 目的地名称，如 "北京"、"Tokyo"。
        category (str, optional): 兴趣点类别，如 "attractions"（景点）、
                                  "restaurants"（餐厅）、"shopping"（购物）等，
                                  默认为 "attractions"。

    返回:
        List[Dict]: 兴趣点列表，每个 POI 包含：
            - name (str): 地点名称
            - rating (float/str): 评分（0-5），无评分时为 "N/A"
            - address (str): 格式化地址
            - category (str): 类别
            - place_id (str): Google Maps 地点唯一标识符
    """
    # 检查 API 密钥是否已配置，若未配置则返回占位数据
    if not settings.MAPS_API_KEY:
        return [
            {
                "name": f"{destination} 热门景点",
                "rating": "N/A",
                "address": "API key not configured",
                "category": category
            }
        ]
    
    try:
        # 创建 HTTP 客户端，设置 10 秒超时
        with httpx.Client(timeout=10.0) as client:
            # 请求 Google Maps Places API 文本搜索接口
            response = client.get(
                "https://maps.googleapis.com/maps/api/place/textsearch/json",
                params={
                    "key": settings.MAPS_API_KEY,          # API 密钥
                    "query": f"{category} in {destination}",  # 搜索查询：类别 + 目的地
                    "language": "zh-CN"                    # 返回结果为中文
                }
            )
            data = response.json()  # 解析 JSON 响应
            
            # 提取前 10 个结果，组装为结构化数据
            return [
                {
                    "name": place["name"],                         # 地点名称
                    "rating": place.get("rating", "N/A"),          # 评分（可能缺失）
                    "address": place.get("formatted_address", ""), # 格式化地址
                    "category": category,                          # 搜索类别
                    "place_id": place.get("place_id", "")          # Google 地点 ID
                }
                for place in data.get("results", [])[:10]          # 最多取 10 条结果
            ]
    except Exception as e:
        # 请求失败时返回错误信息，避免中断调用方
        return [{"name": f"Error: {str(e)}", "category": category}]

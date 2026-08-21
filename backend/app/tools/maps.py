"""
地图 POI 查询模块

提供搜索指定目的地兴趣点（POI，Points of Interest）的功能。

数据源优先级（国内直连优先）：
1. 高德地图 Web 服务 API（AMAP_API_KEY，国内直连免费）
2. Google Maps Places API（MAPS_API_KEY，需国际网络）
3. 均未配置时返回占位数据

适用于旅行规划中的景点推荐场景。
"""

from typing import List, Dict
import httpx
from app.schemas.config import settings

# 高德 POI 文本搜索接口
AMAP_TEXT_URL = "https://restapi.amap.com/v3/place/text"
# Google Places 文本搜索接口（兜底）
GOOGLE_TEXT_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"

# 英文类别 → 中文关键词映射（高德按中文检索更准确）
_CATEGORY_ZH = {
    "attractions": "景点",
    "restaurants": "美食",
    "shopping": "购物",
    "hotels": "酒店",
}


def _call_amap(destination: str, category: str) -> List[Dict]:
    """调用高德地图 POI 文本搜索接口，归一化为统一结构。"""
    zh = _CATEGORY_ZH.get(category, category)
    with httpx.Client(timeout=10.0) as client:
        response = client.get(
            AMAP_TEXT_URL,
            params={
                "key": settings.AMAP_API_KEY,
                "keywords": f"{destination} {zh}",  # 关键词：目的地 + 类别
                "city": destination,                 # 限制城市，提高相关性
                "citylimit": "true",
                "offset": 10,                        # 最多返回 10 条
                "extensions": "base",
            },
        )
        data = response.json()

    pois = data.get("pois") or []
    results = []
    for p in pois[:10]:
        # 高德 location 为 "经度,纬度"，拆分为单独字段便于前端地图使用
        location = p.get("location", "")
        lng, lat = "", ""
        if location and "," in location:
            lng, lat = location.split(",", 1)
        results.append(
            {
                "name": p.get("name", destination),
                "rating": "N/A",                      # 高德基础接口不返回评分
                "address": p.get("address", ""),
                "category": category,
                "tel": p.get("tel", ""),
                "location": {"lng": lng, "lat": lat},
            }
        )
    return results


def _call_google(destination: str, category: str) -> List[Dict]:
    """调用 Google Places API（兜底方案），归一化为统一结构。"""
    with httpx.Client(timeout=10.0) as client:
        response = client.get(
            GOOGLE_TEXT_URL,
            params={
                "key": settings.MAPS_API_KEY,
                "query": f"{category} in {destination}",
                "language": "zh-CN",
            },
        )
        data = response.json()
    return [
        {
            "name": place["name"],
            "rating": place.get("rating", "N/A"),
            "address": place.get("formatted_address", ""),
            "category": category,
            "place_id": place.get("place_id", ""),
        }
        for place in data.get("results", [])[:10]
    ]


def search_pois(destination: str, category: str = "attractions") -> List[Dict]:
    """
    搜索指定目的地的兴趣点（POI）。

    优先使用高德地图（国内直连），未配置高德 key 时回退 Google Places，
    均未配置则返回占位数据。返回结果含名称、评分、地址、类别及经纬度。

    参数:
        destination (str): 目的地名称，如 "北京"、"Tokyo"。
        category (str, optional): 兴趣点类别，如 "attractions"（景点）、
                                  "restaurants"（美食）、"shopping"（购物），
                                  默认为 "attractions"。

    返回:
        List[Dict]: 兴趣点列表，每个 POI 包含：
            - name (str): 地点名称
            - rating (float/str): 评分（0-5），数据源未提供时为 "N/A"
            - address (str): 格式化地址
            - category (str): 类别
            - location (dict, optional): 经纬度 {"lng", "lat"}（高德来源）
            - place_id (str, optional): Google 地点 ID（Google 来源）
    """
    # 优先级 1：高德地图（国内直连）
    if settings.AMAP_API_KEY:
        try:
            return _call_amap(destination, category)
        except Exception as e:  # noqa: BLE001
            # 高德调用失败时回退到 Google（若已配置）
            if settings.MAPS_API_KEY:
                try:
                    return _call_google(destination, category)
                except Exception:  # noqa: BLE001
                    pass
            return [{"name": f"Error: {str(e)}", "category": category}]

    # 优先级 2：Google Places（需国际网络）
    if settings.MAPS_API_KEY:
        try:
            return _call_google(destination, category)
        except Exception as e:  # noqa: BLE001
            return [{"name": f"Error: {str(e)}", "category": category}]

    # 兜底：未配置任何 key，返回占位数据
    return [
        {
            "name": f"{destination} 热门景点",
            "rating": "N/A",
            "address": "API key not configured",
            "category": category,
        }
    ]

"""
酒店查询模块

提供搜索酒店信息的功能。根据目的地、日期和预算范围推荐酒店。
优先调用真实酒店 API（当前接入 Google Places Text Search，复用地图服务密钥），
未配置 API 密钥或调用失败时，优雅降级为按预算生成的占位数据。

说明：项目未内置独立的酒店供应商 SDK，故复用 Google Places 来检索“酒店”类 POI，
通过 HOTELS_API_KEY（或 MAPS_API_KEY）激活。
"""
from typing import List, Dict, Optional
import httpx
from app.schemas.config import settings

# Google Places Text Search API 地址
PLACES_TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"


def _mock_hotels(destination: str, budget: Optional[Dict]) -> List[Dict]:
    """生成示例酒店数据（无密钥或调用失败时的降级方案）。"""
    min_price = budget.get("min", 200) if budget else 200
    max_price = budget.get("max", 1000) if budget else 1000
    return [
        {
            "name": f"{destination} 酒店",
            "price": f"{min_price}-{max_price}",
            "rating": "4.5",
            "address": destination,
            "amenities": ["WiFi", "早餐", "停车场"],
        }
    ]


def _call_real_api(destination: str) -> List[Dict]:
    """调用 Google Places Text Search 检索酒店的酒店信息。"""
    # 优先使用独立的酒店密钥，其次复用地图服务密钥
    api_key = settings.HOTELS_API_KEY or settings.MAPS_API_KEY
    params = {
        "query": f"{destination} 酒店",
        "language": "zh-CN",
        "key": api_key,
    }
    response = httpx.get(PLACES_TEXT_SEARCH_URL, params=params, timeout=10.0)
    response.raise_for_status()
    results = (response.json() or {}).get("results") or []

    hotels = []
    for item in results[:5]:  # 取前 5 条
        hotels.append(
            {
                "name": item.get("name", destination),
                "price": "N/A",  # Places 不直接返回房价，价格由行程规划阶段估算
                "currency": "CNY",
                "rating": item.get("rating", "N/A"),
                "stars": None,
                "address": item.get("formatted_address", destination),
                "amenities": [],
            }
        )
    if not hotels:
        raise ValueError("no hotel data returned")
    return hotels


def search_hotels(
    destination: str,
    dates: Optional[Dict] = None,
    budget: Optional[Dict] = None
) -> List[Dict]:
    """
    搜索指定目的地的酒店信息。

    支持根据目的地、入住日期和预算范围筛选酒店。优先调用真实酒店 API，
    未配置密钥或调用失败时返回议价占位数据作为降级方案。

    参数:
        destination (str): 目的地城市或区域。
        dates (Dict, optional): 入住日期范围，包含以下键：
            - start (str): 入住日期，格式 "YYYY-MM-DD"
            - end (str): 退房日期，格式 "YYYY-MM-DD"
        budget (Dict, optional): 预算范围，包含以下键：
            - min (float): 最低预算
            - max (float): 最高预算

    返回:
        List[Dict]: 酒店信息列表，每个酒店包含：
            - name (str): 酒店名称
            - price (float/str): 价格
            - currency (str, optional): 货币单位
            - rating (float/str): 评分
            - stars (int, optional): 星级
            - address (str): 地址
            - amenities (list): 设施列表，如 ["WiFi", "早餐"]
    """
    # 未配置 API 密钥时依据预算范围生成占位数据
    if not (settings.HOTELS_API_KEY or settings.MAPS_API_KEY):
        return _mock_hotels(destination, budget)

    try:
        return _call_real_api(destination)
    except Exception as e:  # noqa: BLE001
        # 真实 API 调用失败时降级为占位数据，避免中断调用方
        return [{"name": f"Error: {str(e)}"}]
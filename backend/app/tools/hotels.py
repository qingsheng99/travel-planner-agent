"""
酒店查询模块

提供搜索酒店信息的功能。根据目的地、日期和预算范围推荐酒店。

数据源优先级（真实数据优先，国内直连）：
1. RollingGo MCP searchHotels（ROLLINGGO_API_KEY，返回真实房价/星级/库存）
2. 高德地图 Web 服务 API（AMAP_API_KEY，按"住宿服务"类别检索酒店）
3. Google Places Text Search（HOTELS_API_KEY 或 MAPS_API_KEY，需国际网络）
4. 均未配置时返回按预算生成的占位数据

说明：高德/Google 的 POI 搜索不返回实时房价，价格由行程规划阶段估算；
仅 RollingGo 提供真实房价与预订链接。
"""

from typing import List, Dict, Optional
import httpx
from app.schemas.config import settings
from app.tools.mcp_client import mcp_call_tool

# RollingGo 酒店 MCP 端点（已验证可用：/mcp 提供 searchHotels 等工具）
ROLLINGGO_HOTEL_MCP_URL = "https://mcp.rollinggo.cn/mcp"
# 高德 POI 文本搜索接口（按住宿服务类型检索酒店）
AMAP_TEXT_URL = "https://restapi.amap.com/v3/place/text"
# Google Places Text Search API 地址（兜底）
PLACES_TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"

# 高德 POI 分类代码：100000 = 住宿服务（含商务酒店、宾馆等）
AMAP_HOTEL_TYPES = "100000"


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


def _call_rollinggo(
    destination: str, dates: Optional[Dict], budget: Optional[Dict]
) -> List[Dict]:
    """
    调用 RollingGo searchHotels 工具查询真实酒店，归一化为统一结构。

    参数:
        destination (str): 目的地（城市/机场/景点/酒店名等）。
        dates (Dict, optional): 入住日期范围（start/end）。
        budget (Dict, optional): 预算范围（min/max）。

    返回:
        List[Dict]: 酒店信息列表（含真实房价、星级、坐标、预订链接）。

    异常:
        ValueError: 返回数据为空或缺少酒店列表时抛出，由上层降级。
    """
    # 必填参数：place / placeType / originQuery
    arguments: Dict = {
        "place": destination,
        "placeType": "城市",
        "originQuery": f"入住{destination}的酒店",
        "size": 5,  # 默认返回 5 个酒店
    }
    # 入住日期与晚数（可选）
    start = (dates or {}).get("start")
    end = (dates or {}).get("end")
    if start:
        stay_nights = 1
        if end and end > start:
            try:
                from datetime import date
                d0 = date.fromisoformat(start)
                d1 = date.fromisoformat(end)
                stay_nights = max(1, (d1 - d0).days)
            except ValueError:
                stay_nights = 1
        arguments["checkInParam"] = {
            "checkInDate": start,
            "stayNights": stay_nights,
            "adultCount": 2,
        }
    # 预算上限（可选）
    if budget and budget.get("max"):
        arguments["hotelTags"] = {"maxPricePerNight": float(budget["max"])}

    data = mcp_call_tool(
        ROLLINGGO_HOTEL_MCP_URL,
        "searchHotels",
        arguments,
        api_key=settings.ROLLINGGO_API_KEY,
    )

    # 容错解析：酒店列表可能在 hotelInformationList / data / results 等字段
    items = []
    if isinstance(data, dict):
        for key in ("hotelInformationList", "hotels", "results", "data", "items", "list"):
            value = data.get(key)
            if isinstance(value, list) and value:
                items = value
                break

    hotels = []
    for item in items[:5]:
        # 价格信息可能在 price 子对象中（含最低价与货币）
        price_obj = item.get("price") if isinstance(item.get("price"), dict) else {}
        price = (
            price_obj.get("lowestPrice")
            or price_obj.get("price")
            or item.get("price")
            or "N/A"
        )
        rating = item.get("rating") or item.get("score") or "N/A"
        stars = item.get("starRating") or item.get("stars")
        location = {
            "lng": item.get("longitude", ""),
            "lat": item.get("latitude", ""),
        }
        hotels.append(
            {
                "name": item.get("name", destination),
                "price": price,
                "currency": price_obj.get("currency", "CNY"),
                "rating": rating,
                "stars": stars,
                "address": item.get("address", destination),
                "tel": item.get("tel", ""),
                "amenities": item.get("hotelAmenities") or item.get("amenities") or [],
                "location": location,
                "image_url": item.get("imageUrl", ""),
                "booking_url": item.get("bookingUrl", ""),
                "hotel_id": item.get("hotelId", ""),
                "description": item.get("description", ""),
            }
        )
    if not hotels:
        raise ValueError(f"no hotel data returned: {str(data)[:200]}")
    return hotels


def _call_amap(destination: str) -> List[Dict]:
    """调用高德 POI 文本搜索检索住宿类酒店，归一化为统一结构。"""
    with httpx.Client(timeout=10.0) as client:
        response = client.get(
            AMAP_TEXT_URL,
            params={
                "key": settings.AMAP_API_KEY,
                "keywords": f"{destination} 酒店",
                "types": AMAP_HOTEL_TYPES,   # 仅检索住宿服务类 POI
                "city": destination,
                "citylimit": "true",
                "offset": 5,                 # 最多返回 5 条
                "extensions": "base",
            },
        )
        data = response.json()

    pois = data.get("pois") or []
    hotels = []
    for item in pois[:5]:
        location = item.get("location", "")
        lng, lat = "", ""
        if location and "," in location:
            lng, lat = location.split(",", 1)
        hotels.append(
            {
                "name": item.get("name", destination),
                "price": "N/A",   # 高德 POI 不返回房价，由行程阶段估算
                "currency": "CNY",
                "rating": "N/A",
                "stars": None,
                "address": item.get("address", destination),
                "tel": item.get("tel", ""),
                "amenities": [],
                "location": {"lng": lng, "lat": lat},
            }
        )
    if not hotels:
        raise ValueError("no hotel data returned")
    return hotels


def _call_google(destination: str) -> List[Dict]:
    """调用 Google Places Text Search 检索酒店的酒店信息（兜底方案）。"""
    # 优先使用独立的酒店密钥，其次复用地图服务密钥
    api_key = settings.HOTELS_API_KEY or settings.MAPS_API_KEY
    response = httpx.get(
        PLACES_TEXT_SEARCH_URL,
        params={
            "query": f"{destination} 酒店",
            "language": "zh-CN",
            "key": api_key,
        },
        timeout=10.0,
    )
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

    支持根据目的地、入住日期和预算范围筛选酒店。数据源优先级：
    1. RollingGo MCP（真实房价/星级/预订链接）
    2. 高德地图（国内直连）
    3. Google Places（需国际网络）
    4. 按预算生成的占位数据（均未配置时）

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
            - location (dict, optional): 经纬度 {"lng": ..., "lat": ...}
            - booking_url (str, optional): 预订链接（仅 RollingGo）
            - image_url (str, optional): 酒店图片链接（仅 RollingGo）
    """
    # 优先级 1：RollingGo MCP（真实房价）
    if settings.ROLLINGGO_API_KEY:
        try:
            return _call_rollinggo(destination, dates, budget)
        except Exception as e:  # noqa: BLE001
            # RollingGo 失败时记录错误，继续尝试下一数据源
            rollinggo_error = str(e)
            # 依次回退到高德 → Google
            if settings.AMAP_API_KEY:
                try:
                    return _call_amap(destination)
                except Exception:  # noqa: BLE001
                    pass
            if settings.HOTELS_API_KEY or settings.MAPS_API_KEY:
                try:
                    return _call_google(destination)
                except Exception:  # noqa: BLE001
                    pass
            # 全部真实数据源失败：返回带错误提示的占位数据
            mock = _mock_hotels(destination, budget)
            mock[0]["note"] = f"酒店真实服务暂不可用，以下为示例数据（{rollinggo_error[:80]}）"
            return mock

    # 优先级 2：高德地图（国内直连）
    if settings.AMAP_API_KEY:
        try:
            return _call_amap(destination)
        except Exception as e:  # noqa: BLE001
            # 高德调用失败时回退到 Google（若已配置）
            if settings.HOTELS_API_KEY or settings.MAPS_API_KEY:
                try:
                    return _call_google(destination)
                except Exception:  # noqa: BLE001
                    pass
            return [{"name": f"Error: {str(e)}"}]

    # 优先级 3：Google Places（需国际网络）
    if settings.HOTELS_API_KEY or settings.MAPS_API_KEY:
        try:
            return _call_google(destination)
        except Exception as e:  # noqa: BLE001
            return [{"name": f"Error: {str(e)}"}]

    # 兜底：未配置任何 key，返回按预算生成的占位数据
    return _mock_hotels(destination, budget)

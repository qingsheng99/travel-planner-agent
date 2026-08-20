"""
航班查询模块

提供搜索航班信息的功能。优先调用真实航班 API（当前接入 Aviasales /
Travelpayouts 的价格查询接口），未配置 API 密钥或调用失败时，优雅降级为
示例航班数据，方便无密钥环境下开发调试。

启用真实查询所需配置（.env）：
    FLIGHTS_API_KEY=<Travelpayouts token>
可选参数（可自定义）：
    FLIGHTS_API_URL=https://api.travelpayouts.com/aviasales/v3/prices_for_dates
"""
from typing import List, Dict, Optional
import httpx
from datetime import datetime
from app.schemas.config import settings

# 真实 API 地址（可通过配置覆盖）
FLIGHTS_API_URL = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"


def _mock_flights(destination: str, origin: str, dates: Optional[Dict]) -> List[Dict]:
    """生成示例航班数据（无密钥或调用失败时的降级方案）。"""
    start_date = (dates or {}).get("start") or datetime.now().strftime("%Y-%m-%d")
    return [
        {
            "airline": "示例航班",
            "flight_number": "CA1234",
            "price": 1200,
            "currency": "CNY",
            "departure_time": f"{start_date} 08:00",
            "arrival_time": f"{start_date} 11:00",
            "origin": origin or "出发地",
            "destination": destination,
            "duration": "3h",
        },
        {
            "airline": "示例航班",
            "flight_number": "MU5678",
            "price": 950,
            "currency": "CNY",
            "departure_time": f"{start_date} 13:00",
            "arrival_time": f"{start_date} 16:00",
            "origin": origin or "出发地",
            "destination": destination,
            "duration": "3h",
        },
    ]


def _call_real_api(destination: str, origin: str, dates: Optional[Dict]) -> List[Dict]:
    """调用 Aviasales 真实航班 API 并归一化为统一结构。"""
    start_date = (dates or {}).get("start") or datetime.now().strftime("%Y-%m-%d")
    end_date = (dates or {}).get("end")

    params = {
        "origin": origin or "SHA",  # 未指定出发地时默认上海
        "destination": destination,
        "departure_at": start_date,
        "currency": "CNY",
        "one_way": "false",
        "token": settings.FLIGHTS_API_KEY,
    }
    if end_date and end_date != start_date:
        params["return_at"] = end_date

    response = httpx.get(FLIGHTS_API_URL, params=params, timeout=10.0)
    response.raise_for_status()
    data = (response.json() or {}).get("data") or []

    flights = []
    for item in data:
        price = item.get("price")
        flights.append(
            {
                "airline": item.get("airline") or "Airline",
                "flight_number": item.get("flight_number") or "",
                "price": price,
                "currency": item.get("currency", "CNY"),
                "departure_time": item.get("departure_at", ""),
                "arrival_time": item.get("return_at", ""),
                "origin": origin or "SHA",
                "destination": destination,
                "duration": "N/A",
            }
        )
    if not flights:
        raise ValueError("no flight data returned")
    return flights


def search_flights(
    destination: str,
    origin: str = "",
    dates: Optional[Dict] = None
) -> List[Dict]:
    """
    搜索指定目的地和日期的航班信息。

    支持通过出发地、目的地和日期范围筛选航班。优先调用真实航班 API，
    未配置密钥或调用失败时返回示例航班数据作为降级方案。

    参数:
        destination (str): 目的地城市或机场。
        origin (str, optional): 出发地城市或机场，默认为空。
        dates (Dict, optional): 日期范围字典，包含以下键：
            - start (str): 出发日期，格式 "YYYY-MM-DD"
            - end (str): 返回日期，格式 "YYYY-MM-DD"

    返回:
        List[Dict]: 航班信息列表，每个航班包含：
            - airline (str): 航空公司名称
            - flight_number (str): 航班号
            - price (float/str): 票价，失败时为 "N/A"
            - currency (str): 货币单位
            - departure_time (str): 出发时间
            - arrival_time (str): 到达时间
            - origin (str): 出发地
            - destination (str): 目的地
            - duration (str): 飞行时长
    """
    # 未配置 API 密钥时直接返回示例航班数据
    if not settings.FLIGHTS_API_KEY:
        return _mock_flights(destination, origin, dates)

    try:
        return _call_real_api(destination, origin, dates)
    except Exception as e:  # noqa: BLE001
        # 真实 API 调用失败时降级为示例数据，避免中断调用方
        return [{"airline": f"Error: {str(e)}"}]
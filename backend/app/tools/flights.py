"""
航班查询模块

提供搜索航班信息的功能。优先调用 SerpApi Google Flights（真实票价），
未配置 API 密钥或调用失败时，优雅降级为示例航班数据。

启用真实查询所需配置（.env）：
    SERPAPI_API_KEY=<SerpApi key>   # 注册 https://serpapi.com（免费额度 100 次/月）

说明：
- SerpApi 的 google_flights 引擎返回真实票价与航班时刻，国内网络需可访问
  SerpApi（国际出口）。
- 出发/目的地使用 IATA 三字码（如 PEK/SHA），内置常见城市映射兜底。
- 返回结果采用容错归一化，兼容字段命名差异。
"""
from typing import List, Dict, Optional
import httpx
import re
from datetime import datetime
from app.schemas.config import settings

# SerpApi Google Flights 搜索端点
SERPAPI_SEARCH_URL = "https://serpapi.com/search.json"

# 常见城市 → IATA 码映射（解析失败时的兜底，避免每次查询都依赖机场搜索接口）
_CITY_IATA = {
    # 国内
    "北京": "PEK", "上海": "SHA", "广州": "CAN", "深圳": "SZX",
    "成都": "CTU", "杭州": "HGH", "西安": "XIY", "重庆": "CKG",
    "南京": "NKG", "武汉": "WUH", "三亚": "SYX", "昆明": "KMG",
    "青岛": "TAO", "厦门": "XMN", "长沙": "CSX", "郑州": "CGO",
    "天津": "TSN", "大连": "DLC", "沈阳": "SHE", "哈尔滨": "HRB",
    "乌鲁木齐": "URC", "拉萨": "LXA", "贵阳": "KWE", "福州": "FOC",
    # 国际/港澳台
    "东京": "NRT", "大阪": "KIX", "首尔": "ICN", "曼谷": "BKK",
    "新加坡": "SIN", "香港": "HKG", "澳门": "MFM", "台北": "TPE",
    "伦敦": "LHR", "巴黎": "CDG", "纽约": "JFK", "洛杉矶": "LAX",
    "旧金山": "SFO", "悉尼": "SYD", "墨尔本": "MEL", "迪拜": "DXB",
}

# 匹配已是大写三字码（如 HGH / CTU）
_IATA_RE = re.compile(r"^[A-Z]{3}$")


def _resolve_iata(place: str) -> str:
    """
    把目的地/出发地解析为 IATA 三字码。

    解析顺序：
    1. 本身是 IATA 三字码 → 直接用
    2. 内置常见城市映射命中 → 直接用
    3. 全部失败 → 返回原值（交由上游接口兜底）

    参数:
        place (str): 城市名（中/英文）或 IATA 码。

    返回:
        str: IATA 三字码；无法解析时返回原值。
    """
    place = (place or "").strip()
    if not place:
        return place
    if _IATA_RE.match(place):
        return place
    if place in _CITY_IATA:
        return _CITY_IATA[place]
    # 英文城市名先尝试映射（如 "Beijing"）
    for zh, code in _CITY_IATA.items():
        if place.lower() == zh.lower():
            return code
    return place


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


def _parse_flight(
    item: Dict, destination: str, origin: str
) -> Dict:
    """
    把一条 SerpApi best_flights 记录归一化为统一结构。

    SerpApi 返回结构示例：
    {
        "flights": [  # 航段列表（含中转）
            {"airline": "Air China", "flight_number": "CA1831",
             "departure_time": "...", "arrival_time": "...",
             "departure_airport": {...}, "arrival_airport": {...}},
        ],
        "price": 1200,
        "total_duration": 180,   # 分钟
    }

    参数:
        item (Dict): SerpApi 航班记录。
        destination (str): 目的地。
        origin (str): 出发地。

    返回:
        Dict: 归一化后的航班信息。
    """
    segments = item.get("flights") or []
    first = segments[0] if segments else {}
    last = segments[-1] if segments else {}

    # 航司/航班号：拼接多航段（如 "CA1831 / MU5100"），无航段时显示联程
    airlines = [s.get("airline", "") for s in segments if s.get("airline")]
    flight_numbers = [s.get("flight_number", "") for s in segments if s.get("flight_number")]
    airline = " / ".join(dict.fromkeys(airlines)) or "N/A"
    flight_number = " / ".join(dict.fromkeys(flight_numbers)) or "联程"

    # 出发/到达时间取首末航段；分钟时长转为 "Xh Ym"
    departure_time = first.get("departure_time", "")
    arrival_time = last.get("arrival_time", "")
    total_minutes = item.get("total_duration")
    if total_minutes:
        duration = f"{total_minutes // 60}h {total_minutes % 60}m"
    else:
        duration = "N/A"

    return {
        "airline": airline,
        "flight_number": flight_number,
        "price": item.get("price", "N/A"),
        "currency": "CNY",
        "departure_time": departure_time,
        "arrival_time": arrival_time,
        "origin": origin or "N/A",
        "destination": destination,
        "duration": duration,
    }


def _call_serpapi(destination: str, origin: str, dates: Optional[Dict]) -> List[Dict]:
    """
    调用 SerpApi Google Flights 查询真实航班，归一化为统一结构。

    参数:
        destination (str): 目的地城市或机场。
        origin (str): 出发地城市或机场。
        dates (Dict, optional): 日期范围（start/end）。

    返回:
        List[Dict]: 航班信息列表（含真实票价）。

    异常:
        ValueError / httpx 异常: 调用失败时由上层降级。
    """
    start_date = (dates or {}).get("start") or datetime.now().strftime("%Y-%m-%d")
    end_date = (dates or {}).get("end")

    from_iata = _resolve_iata(origin or "SHA")   # 未指定出发地时默认上海
    to_iata = _resolve_iata(destination)

    params = {
        "engine": "google_flights",
        "api_key": settings.SERPAPI_API_KEY,
        "departure_id": from_iata,
        "arrival_id": to_iata,
        "outbound_date": start_date,
        "currency": "CNY",
        "hl": "zh-cn",
        # 往返（return_date 存在且与出发日不同）时 type=2，否则单程 type=1
        "type": 2 if (end_date and end_date != start_date) else 1,
    }
    if end_date and end_date != start_date:
        params["return_date"] = end_date

    response = httpx.get(SERPAPI_SEARCH_URL, params=params, timeout=30.0)
    response.raise_for_status()
    data = response.json()

    # SerpApi 错误时 error 字段非空（如配额用尽 / 无效 key）
    error = data.get("error")
    if error:
        raise ValueError(f"SerpApi error: {str(error)[:200]}")

    items = data.get("best_flights") or []
    flights = [_parse_flight(item, destination, origin) for item in items]
    if not flights:
        raise ValueError(f"no flight data returned: {str(data)[:200]}")
    return flights


def search_flights(
    destination: str,
    origin: str = "",
    dates: Optional[Dict] = None
) -> List[Dict]:
    """
    搜索指定目的地和日期的航班信息。

    支持通过出发地、目的地和日期范围筛选航班。优先调用 SerpApi Google
    Flights（真实票价），未配置密钥或调用失败时返回示例航班数据作为降级方案。

    参数:
        destination (str): 目的地城市或机场。
        origin (str, optional): 出发地城市或机场，默认为空（回退上海 SHA）。
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
    if not settings.SERPAPI_API_KEY:
        return _mock_flights(destination, origin, dates)

    try:
        return _call_serpapi(destination, origin, dates)
    except Exception as e:  # noqa: BLE001
        # 真实 API 调用失败（配额用尽/端点不可达等）时降级为示例数据
        flights = _mock_flights(destination, origin, dates)
        flights[0]["note"] = f"真实航班服务暂不可用，以下为示例数据（{str(e)[:80]}）"
        return flights

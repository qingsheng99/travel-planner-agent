"""
天气查询模块

提供获取指定目的地天气预报的功能，使用 WeatherAPI 作为数据源。
支持获取当前温度、天气状况、湿度、风速以及未来 7 天的逐日预报。
"""

from typing import Dict, Optional
import httpx
from app.schemas.config import settings


def get_weather(destination: str) -> Dict:
    """
    查询指定目的地的天气预报。

    调用 WeatherAPI 的 forecast 接口获取当前天气及未来 7 天预报。
    若 API 密钥未配置或请求失败，返回包含错误信息的默认数据。

    参数:
        destination (str): 目的地名称（城市名或地址，如 "Beijing"）。

    返回:
        Dict: 包含天气信息的字典，结构如下：
            - temperature (float/str): 当前温度（摄氏度），失败时为 "N/A"
            - condition (str): 当前天气状况描述，如 "Sunny"
            - humidity (int/str): 当前湿度百分比，失败时为 "N/A"
            - wind (float/str): 当前风速（公里/小时），失败时为 "N/A"
            - forecast (list): 未来 7 天逐日预报列表，每项包含：
                - date (str): 日期，格式 "YYYY-MM-DD"
                - max_temp (float): 最高温度
                - min_temp (float): 最低温度
                - condition (str): 天气状况描述
    """
    # 检查 API 密钥是否已配置，若未配置则返回占位数据
    if not settings.WEATHER_API_KEY:
        return {
            "temperature": "N/A",
            "condition": "API key not configured",
            "forecast": []
        }
    
    try:
        # 创建 HTTP 客户端，设置 10 秒超时
        with httpx.Client(timeout=10.0) as client:
            # 请求 WeatherAPI 的 7 天预报接口
            response = client.get(
                "https://api.weatherapi.com/v1/forecast.json",
                params={
                    "key": settings.WEATHER_API_KEY,  # API 密钥
                    "q": destination,                  # 查询目的地
                    "days": 7                          # 预报天数
                }
            )
            data = response.json()  # 解析 JSON 响应
            
            # 组装并返回结构化的天气数据
            return {
                "temperature": data["current"]["temp_c"],               # 当前温度（摄氏度）
                "condition": data["current"]["condition"]["text"],      # 当前天气状况描述
                "humidity": data["current"]["humidity"],                # 当前湿度
                "wind": data["current"]["wind_kph"],                    # 当前风速（公里/小时）
                "forecast": [
                    {
                        "date": day["date"],                            # 预报日期
                        "max_temp": day["day"]["maxtemp_c"],            # 最高温度
                        "min_temp": day["day"]["mintemp_c"],            # 最低温度
                        "condition": day["day"]["condition"]["text"]    # 天气状况
                    }
                    for day in data.get("forecast", {}).get("forecastday", [])
                ]
            }
    except Exception as e:
        # 请求失败时返回错误信息，避免中断调用方
        return {
            "temperature": "N/A",
            "condition": f"Error: {str(e)}",
            "forecast": []
        }

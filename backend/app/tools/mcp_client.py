"""
公共 MCP 客户端模块

实现一个轻量 MCP（Model Context Protocol，streamable HTTP 传输方式）
JSON-RPC 客户端，供各工具模块（酒店、航班等）复用已验证的调用协议，
避免每个模块重复实现握手与 tools/call 逻辑。

调用流程（RollingGo 服务端为无状态，不返回 session-id）：
1. initialize   建立协议握手（可失败，部分实现可省略）
2. notifications/initialized  通知服务端初始化完成
3. tools/call   调用目标工具，结果封装在 result.content[].text（JSON 字符串）

典型用法:
    from app.tools.mcp_client import mcp_call_tool
    data = mcp_call_tool(url, "searchHotels", {"keyword": "北京"}, api_key=settings.ROLLINGGO_API_KEY)
"""

from typing import Dict, Union
import json
import httpx

# 默认请求超时：连接 10s，读取 60s（真实数据接口可能耗时较长）
DEFAULT_TIMEOUT = (10, 60)


def mcp_headers(api_key: str) -> Dict[str, str]:
    """
    构造 MCP 请求头。

    参数:
        api_key (str): RollingGo API key，以 Bearer 方式携带。

    返回:
        Dict[str, str]: 请求头字典。
    """
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        # RollingGo 服务端按 SSE 协议返回，需显式声明可接受该类型
        "Accept": "application/json, text/event-stream",
    }


def mcp_post(url: str, request: Dict, api_key: str) -> Dict:
    """
    发送一次 MCP JSON-RPC 请求并返回 JSON 响应。

    参数:
        url (str): MCP 端点地址。
        request (Dict): JSON-RPC 请求体。
        api_key (str): RollingGo API key。

    返回:
        Dict: 服务端返回的 JSON 对象。

    异常:
        httpx.HTTPStatusError: HTTP 状态码非 2xx 时抛出。
        httpx.TimeoutException: 请求超时时抛出。
    """
    resp = httpx.post(
        url,
        headers=mcp_headers(api_key),
        json=request,
        timeout=DEFAULT_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def mcp_call_tool(
    url: str,
    tool_name: str,
    arguments: Dict,
    api_key: str,
) -> Union[Dict, list, str]:
    """
    完整调用 MCP 服务端的 tools/call 工具，返回解析后的数据。

    内部依次执行 initialize → notifications/initialized → tools/call，
    并自动从 result.content[].text 中提取并解析 JSON 字符串。

    参数:
        url (str): MCP 端点地址。
        tool_name (str): 工具名，如 "searchHotels" / "searchFlights"。
        arguments (Dict): 工具参数（JSON-RPC 规范中的 arguments）。
        api_key (str): RollingGo API key。

    返回:
        Union[Dict, list, str]:
            - 内容为合法 JSON 时返回解析后的 dict / list；
            - 否则返回原始文本字符串；
            - 无内容时返回空 dict。
    """
    # 1. initialize 握手（无状态服务，忽略返回结果；失败不阻断后续调用）
    try:
        mcp_post(
            url,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "travel-planner", "version": "1.0"},
                },
            },
            api_key,
        )
        # 2. 通知服务端初始化完成
        mcp_post(
            url,
            {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
            api_key,
        )
    except Exception:  # noqa: BLE001
        # 握手失败不阻断 tools/call（部分实现可省略握手）
        pass

    # 3. 调用目标工具
    result = mcp_post(
        url,
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        },
        api_key,
    )
    content = (result.get("result") or {}).get("content") or []
    texts = [item.get("text", "") for item in content if item.get("type") == "text"]
    raw = "\n".join(texts).strip()
    try:
        return json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        return raw

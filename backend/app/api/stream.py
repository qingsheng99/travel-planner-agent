"""
流式对话模块 —— 基于 LangGraph 的实时流式聊天接口。

提供 /chat/stream 端点，通过 Server-Sent Events (SSE) 实时推送 AI 对话
生成的文本 token，以及工具调用的开始/结束状态。

改进点（相对旧版）：
1. 由原先“一次性 ainvoke 后再分块”的伪流式，改为基于 astream_events 的
   “真实 token 流”，即在 LLM 产出每个 token 的同时即时推送。
   - 依赖 LangGraph 为事件注入的 metadata["langgraph_node"] 精确过滤：
     只有 itinerary / respond 节点（产出最终用户回复的节点）的 token
     才会被推送，避免把意图分类器等中间结果泄漏给用户。
2. 新增 tool_start / tool_end 事件，实时反馈工具调用状态。
3. 初始状态中的 preferences 从用户画像（UserProfile）真实读取，
   而非写死的 None。
"""
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from app.db.session import AsyncSessionLocal
from app.db.models import User
from app.services.auth import get_current_active_user
from app.services.profile import get_or_create_profile
from app.services.itinerary import get_owned_trip, persist_chat_result

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

# 流式输出时，只有这些节点（产出最终用户回复）的 token 会被推送
FINAL_RESPONSE_NODES = {"itinerary", "respond"}

# 工具节点文本标签，用于 tool_start / tool_end 事件展示给前端
TOOL_LABELS = {
    "intent_router": "意图分析",
    "weather": "查询天气",
    "flights": "查询航班",
    "hotels": "查询酒店",
    "pois": "查询景点",
    "itinerary": "生成行程",
    "respond": "生成回复",
}


class ChatRequest(BaseModel):
    """聊天请求体模型。"""

    message: str  # 用户发送的消息文本
    trip_id: Optional[int] = None  # 关联的行程 ID（可选，用于上下文）
    destination: Optional[str] = None  # 目的地（可选）


@router.post("/stream")
async def stream_chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_active_user),
):
    """流式聊天接口。

    基于 LangGraph 的 travel_graph 图，以 SSE（Server-Sent Events）格式
    实时推送 AI 响应 token、工具调用开始/结束等事件。

    Args:
        request: 聊天请求体，包含消息文本及可选的行程 ID / 目的地。
        current_user: 当前登录用户（依赖注入）。

    Returns:
        StreamingResponse: SSE 流式响应，包含以下事件类型：
            - start: 开始标志
            - tool_start: 工具开始调用（含工具名）
            - token: AI 生成的文本片段（真实逐 token 流）
            - tool_end: 工具调用结束（含工具名）
            - end: 响应结束
            - error: 发生错误
    """
    # 延迟导入以避免循环依赖
    from app.graph.builder import travel_graph

    trip_context = None
    if request.trip_id:
        async with AsyncSessionLocal() as db:
            trip_context = await get_owned_trip(db, request.trip_id, current_user.id)
            if trip_context is None:
                raise HTTPException(status_code=404, detail="Trip not found")
            trip_context = {
                "destination": trip_context.destination,
                "start_date": trip_context.start_date,
                "end_date": trip_context.end_date,
                "budget": trip_context.budget,
                "travelers": trip_context.travelers,
            }

    # 读取用户画像偏好（不存在则自动创建默认画像），供行程规划参考
    preferences = None
    async with AsyncSessionLocal() as db:
        profile = await get_or_create_profile(db, current_user.id)
        preferences = profile.preferences or {}

    async def event_generator():
        """异步事件生成器，逐事件推送 SSE 数据。"""
        # 构建初始状态，包含用户消息、上下文信息与用户偏好
        initial_state = {
            "messages": [HumanMessage(content=request.message)],  # 用户消息转为 LangChain 消息格式
            "user_id": current_user.id,
            "trip_id": request.trip_id,
            "destination": request.destination or (trip_context["destination"] if trip_context else None),
            "dates": _trip_dates(trip_context),  # 后续可由 AI 工具补充
            "budget": trip_context["budget"] if trip_context else None,
            "travelers": trip_context["travelers"] if trip_context else 1,
            "preferences": preferences,  # 从用户画像读取的偏好
            "weather_info": None,  # 后续由天气查询工具填充
            "flight_info": None,  # 后续由航班查询工具填充
            "hotel_info": None,  # 后续由酒店查询工具填充
            "poi_info": None,  # 后续由景点查询工具填充
            "itinerary": None,  # 后续由行程生成工具填充
            "next": None,
        }

        # 发送开始事件
        yield f"data: {json.dumps({'type': 'start'})}\n\n"

        # 收集真实流式 token 与最终完整回复（用于持久化）
        token_parts: list[str] = []
        complete_text: Optional[str] = None
        generated_itinerary = None

        try:
            # 遍历图的实时事件流（v1 版本，事件均带 langgraph_node 元数据）
            async for event in travel_graph.astream_events(initial_state, version="v1"):
                event_type = event.get("event")
                name = event.get("name") or ""
                node = (event.get("metadata") or {}).get("langgraph_node")

                # —— 工具节点开始 / 结束（实时反馈状态） ——
                if event_type == "on_chain_start" and name in TOOL_LABELS:
                    yield _sse({"type": "tool_start", "tool": name, "label": TOOL_LABELS[name]})
                elif event_type == "on_chain_end" and name in TOOL_LABELS:
                    # 从节点返回结果中提取行程与完整回复（用于持久化兜底）
                    output = (event.get("data") or {}).get("output") or {}
                    if output.get("itinerary"):
                        generated_itinerary = output["itinerary"]
                    if output.get("assistant_response") and complete_text is None:
                        complete_text = output["assistant_response"]
                    yield _sse({"type": "tool_end", "tool": name, "label": TOOL_LABELS[name]})

                # —— 真实 token 流：仅推送产出最终回复节点的 token ——
                elif event_type == "on_chat_model_stream" and node in FINAL_RESPONSE_NODES:
                    chunk = (event.get("data") or {}).get("chunk")
                    if chunk is None:
                        continue
                    text = getattr(chunk, "content", None)
                    if text is None:
                        text = str(chunk)
                    # 部分模型以内容块列表返回，需展开提取文本
                    if isinstance(text, list):
                        text = "".join(
                            b.get("text", "") if isinstance(b, dict) else str(b)
                            for b in text
                        )
                    if text:
                        token_parts.append(text)
                        yield _sse({"type": "token", "content": text}, allow_newline=True)

            # 组装完整回复：优先用真实流式文本，兜底用节点返回的 assistant_response
            streamed_text = "".join(token_parts)
            assistant_response = streamed_text or complete_text or _fallback_response(
                {"itinerary": generated_itinerary}
            )

            # 持久化对话记录（生成完整行程时同步更新 Trip）
            if request.trip_id:
                async with AsyncSessionLocal() as db:
                    await persist_chat_result(
                        db=db,
                        trip_id=request.trip_id,
                        user_message=request.message,
                        assistant_message=assistant_response,
                        itinerary=generated_itinerary,
                    )

            # 发送结束事件
            yield f"data: {json.dumps({'type': 'end'})}\n\n"

        except Exception as e:  # noqa: BLE001
            logger.exception("stream_chat failed")
            # 发送错误事件，包含异常信息
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    # 返回 SSE 流式响应，设置必要的缓存控制头
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",  # 禁止浏览器缓存 SSE 数据
            "Connection": "keep-alive",  # 保持长连接
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲（如使用反向代理）
        },
    )


def _sse(payload: dict, allow_newline: bool = False) -> str:
    """
    将字典序列化为一条 SSE 数据帧。

    默认折叠 token 中的换行符（SSE 按行解析），当允许换行时用 \\n 表示。
    """
    if not allow_newline and isinstance(payload.get("content"), str):
        payload = {**payload, "content": payload["content"].replace("\n", "\\n")}
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _trip_dates(trip) -> Optional[dict]:
    if not trip or not trip.get("start_date"):
        return None
    dates = {"start": trip["start_date"].date().isoformat()}
    if trip.get("end_date"):
        dates["end"] = trip["end_date"].date().isoformat()
    return dates


def _fallback_response(state: dict) -> str:
    itinerary = state.get("itinerary") or {}
    if itinerary.get("content"):
        return itinerary["content"]
    return "我已经收到你的旅行需求，但暂时没有生成完整回复。请补充目的地、日期、预算或偏好后再试一次。"
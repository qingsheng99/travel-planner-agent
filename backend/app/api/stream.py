from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
from langchain_core.messages import HumanMessage
import json
from app.db.session import get_db
from app.db.models import User
from app.services.auth import get_current_active_user
from app.graph.builder import travel_graph
from app.services.itinerary import add_conversation_message

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    trip_id: Optional[int] = None
    destination: Optional[str] = None


@router.post("/stream")
async def stream_chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    async def event_generator():
        initial_state = {
            "messages": [HumanMessage(content=request.message)],
            "user_id": current_user.id,
            "trip_id": request.trip_id,
            "destination": request.destination,
            "dates": None,
            "budget": None,
            "travelers": 1,
            "preferences": None,
            "weather_info": None,
            "flight_info": None,
            "hotel_info": None,
            "poi_info": None,
            "itinerary": None,
            "next": None,
        }

        yield f"data: {json.dumps({'type': 'start'})}\n\n"

        try:
            async for event in travel_graph.astream_events(initial_state, version="v1"):
                event_type = event["event"]

                if event_type == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if chunk.content:
                        yield f"data: {json.dumps({'type': 'token', 'content': chunk.content})}\n\n"

                elif event_type == "on_tool_start":
                    yield f"data: {json.dumps({'type': 'tool_start', 'tool': event['name']})}\n\n"

                elif event_type == "on_tool_end":
                    yield f"data: {json.dumps({'type': 'tool_end', 'tool': event['name']})}\n\n"

            if request.trip_id:
                await add_conversation_message(db, request.trip_id, {
                    "role": "user",
                    "content": request.message,
                })

            yield f"data: {json.dumps({'type': 'end'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
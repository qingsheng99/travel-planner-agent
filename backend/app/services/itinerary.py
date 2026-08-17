from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Trip, Conversation
from typing import Dict, List, Optional
from datetime import datetime


async def create_trip(
    db: AsyncSession,
    user_id: int,
    title: str,
    destination: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    budget: Optional[Dict] = None,
    travelers: int = 1,
) -> Trip:
    trip = Trip(
        user_id=user_id,
        title=title,
        destination=destination,
        start_date=start_date,
        end_date=end_date,
        budget=budget or {},
        travelers=travelers,
        status="planning",
        itinerary={},
    )
    db.add(trip)
    await db.commit()
    await db.refresh(trip)

    conversation = Conversation(trip_id=trip.id, messages=[])
    db.add(conversation)
    await db.commit()

    return trip


async def get_trip(db: AsyncSession, trip_id: int) -> Optional[Trip]:
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    return result.scalar_one_or_none()


async def get_user_trips(db: AsyncSession, user_id: int) -> List[Trip]:
    result = await db.execute(
        select(Trip).where(Trip.user_id == user_id).order_by(Trip.created_at.desc())
    )
    return list(result.scalars().all())


async def update_trip_itinerary(db: AsyncSession, trip_id: int, itinerary: Dict) -> Optional[Trip]:
    trip = await get_trip(db, trip_id)
    if trip:
        trip.itinerary = itinerary
        trip.status = "planned"
        await db.commit()
        await db.refresh(trip)
    return trip


async def add_conversation_message(db: AsyncSession, trip_id: int, message: Dict) -> Optional[Conversation]:
    result = await db.execute(select(Conversation).where(Conversation.trip_id == trip_id))
    conversation = result.scalar_one_or_none()
    if conversation:
        if not conversation.messages:
            conversation.messages = []
        conversation.messages.append(message)
        await db.commit()
        await db.refresh(conversation)
    return conversation


async def get_conversation_messages(db: AsyncSession, trip_id: int) -> List[Dict]:
    result = await db.execute(select(Conversation).where(Conversation.trip_id == trip_id))
    conversation = result.scalar_one_or_none()
    if conversation:
        return conversation.messages or []
    return []
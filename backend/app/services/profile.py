from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import UserProfile
from typing import Dict, Optional


async def get_user_profile(db: AsyncSession, user_id: int) -> Optional[UserProfile]:
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    return result.scalar_one_or_none()


async def create_user_profile(db: AsyncSession, user_id: int) -> UserProfile:
    profile = UserProfile(user_id=user_id, preferences={}, travel_history=[])
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


async def update_preferences(db: AsyncSession, user_id: int, preferences: Dict) -> UserProfile:
    profile = await get_user_profile(db, user_id)
    if not profile:
        profile = await create_user_profile(db, user_id)

    if profile.preferences:
        profile.preferences.update(preferences)
    else:
        profile.preferences = preferences

    await db.commit()
    await db.refresh(profile)
    return profile


async def add_travel_history(db: AsyncSession, user_id: int, trip_data: Dict) -> UserProfile:
    profile = await get_user_profile(db, user_id)
    if not profile:
        profile = await create_user_profile(db, user_id)

    if not profile.travel_history:
        profile.travel_history = []
    profile.travel_history.append(trip_data)

    await db.commit()
    await db.refresh(profile)
    return profile
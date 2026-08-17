from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime
from app.db.session import get_db
from app.db.models import User
from app.services.auth import get_current_active_user
from app.services.itinerary import (
    create_trip,
    get_trip,
    get_user_trips,
    update_trip_itinerary,
)

router = APIRouter(prefix="/trips", tags=["trips"])


class TripCreate(BaseModel):
    title: str
    destination: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    budget: Optional[Dict] = None
    travelers: int = 1


class TripResponse(BaseModel):
    id: int
    title: str
    destination: str
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    budget: Dict
    travelers: int
    status: str
    itinerary: Dict
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/", response_model=TripResponse)
async def create_new_trip(
    trip_data: TripCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    trip = await create_trip(
        db=db,
        user_id=current_user.id,
        title=trip_data.title,
        destination=trip_data.destination,
        start_date=trip_data.start_date,
        end_date=trip_data.end_date,
        budget=trip_data.budget,
        travelers=trip_data.travelers,
    )
    return trip


@router.get("/", response_model=List[TripResponse])
async def list_trips(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return await get_user_trips(db, current_user.id)


@router.get("/{trip_id}", response_model=TripResponse)
async def get_trip_detail(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    trip = await get_trip(db, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this trip")
    return trip


@router.put("/{trip_id}/itinerary", response_model=TripResponse)
async def save_itinerary(
    trip_id: int,
    itinerary: Dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    trip = await get_trip(db, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    updated_trip = await update_trip_itinerary(db, trip_id, itinerary)
    return updated_trip
from fastapi import APIRouter, Query
from app.services.rss_service import fetch_threat_feeds

router = APIRouter()


@router.get("/feed")
async def get_threat_feed(limit: int = Query(default=30, ge=5, le=60)):
    return await fetch_threat_feeds(limit=limit)

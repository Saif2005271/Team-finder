from fastapi import APIRouter
from pydantic import BaseModel
from app.services.url_analyzer import analyze_url

router = APIRouter()


class URLRequest(BaseModel):
    url: str


@router.post("/analyze")
async def analyze_phishing(data: URLRequest):
    return await analyze_url(data.url.strip())

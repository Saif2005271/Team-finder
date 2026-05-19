from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

from app.routers import location, breach, phishing, stalkerware, webrtc, dns_leak, threat_intel

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="CyberShield Privacy Auditor",
    description="Comprehensive personal privacy, device security, and network audit platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="app/templates")

app.include_router(location.router, prefix="/api/location", tags=["Location & Privacy"])
app.include_router(breach.router, prefix="/api/breach", tags=["Breach Detection"])
app.include_router(phishing.router, prefix="/api/phishing", tags=["Phishing Detector"])
app.include_router(stalkerware.router, prefix="/api/stalkerware", tags=["Stalkerware"])
app.include_router(webrtc.router, prefix="/api/webrtc", tags=["WebRTC Leak"])
app.include_router(dns_leak.router, prefix="/api/dns", tags=["DNS Leak"])
app.include_router(threat_intel.router, prefix="/api/threats", tags=["Threat Intel"])


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

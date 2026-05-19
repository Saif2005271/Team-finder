from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional
import httpx

router = APIRouter()


class LocationData(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    accuracy: Optional[float] = None


TRACKING_METHODS = {
    "passive_gps": {
        "name": "Passive GPS / Satellite",
        "accuracy": "3–5 meters",
        "requires_permission": True,
        "passive": False,
        "description": (
            "Uses signals from a constellation of 24+ NAVSTAR satellites orbiting at ~20,000 km. "
            "The receiver calculates position by measuring signal travel-time from at least 4 satellites "
            "(trilateration). Accuracy: 3–5 m outdoors. Works without internet. Triggered ONLY when "
            "a site calls navigator.geolocation.getCurrentPosition() and the user grants permission. "
            "Your browser will show a permission dialog."
        ),
    },
    "cell_tower": {
        "name": "Cell Tower Triangulation",
        "accuracy": "50–300 meters",
        "requires_permission": False,
        "passive": True,
        "description": (
            "Mobile carriers continuously measure which towers your handset can 'see' and the signal "
            "strength (RSSI/RSRP) to each. With 3+ towers, they triangulate position to within 50–300 m "
            "in cities, up to 1–2 km in rural areas. This requires NO permission from you — your carrier "
            "always knows your location when your phone has a signal. Law enforcement can subpoena these records."
        ),
    },
    "ip_geolocation": {
        "name": "IP Address Geolocation",
        "accuracy": "City level (~1–50 km)",
        "requires_permission": False,
        "passive": True,
        "description": (
            "Every server you connect to sees your public IP. Companies like MaxMind and ipapi maintain "
            "databases mapping IP ranges to geographic regions, updating millions of records daily. "
            "Resolution: typically city-level. VPNs spoof this by routing through servers in other regions. "
            "Tor provides stronger anonymity by routing through 3+ relays."
        ),
    },
    "wifi_positioning": {
        "name": "Wi-Fi Positioning System (WPS)",
        "accuracy": "15–40 meters",
        "requires_permission": False,
        "passive": True,
        "description": (
            "Google, Apple, and Microsoft have war-driven vehicles that mapped billions of Wi-Fi access "
            "points worldwide. When your device scans visible APs and queries a WPS database, it gets "
            "location without GPS. Apple's WPS fires even with location off for network-optimisation purposes. "
            "Disable Wi-Fi scanning in privacy settings to reduce exposure."
        ),
    },
}


def _assess_risk(ip_data: dict, has_gps: bool) -> dict:
    factors = []
    score = 0

    if has_gps:
        factors.append(
            {
                "factor": "Precise GPS Exposed",
                "severity": "critical",
                "description": (
                    "Your browser shared GPS coordinates accurate to meters. "
                    "Any website you grant this permission to can pinpoint your home, workplace, or daily route."
                ),
            }
        )
        score += 35

    org = ip_data.get("org", "")
    if org:
        factors.append(
            {
                "factor": "ISP / Organisation Identified",
                "severity": "medium",
                "description": f"Your ISP or network owner ({org}) is visible to every server you connect to.",
            }
        )
        score += 15

    city = ip_data.get("city", "")
    if city:
        factors.append(
            {
                "factor": "City-Level Location Exposed",
                "severity": "low",
                "description": f"IP geolocation places you in {city}, {ip_data.get('country_name', '')}. "
                "No permission required — passive and always-on.",
            }
        )
        score += 20

    timezone = ip_data.get("timezone", "")
    if timezone:
        factors.append(
            {
                "factor": "Timezone Fingerprint",
                "severity": "low",
                "description": f"Timezone ({timezone}) combined with language and browser settings "
                "contributes to a unique device fingerprint.",
            }
        )
        score += 10

    if not ip_data.get("error"):
        factors.append(
            {
                "factor": "No VPN / Proxy Detected",
                "severity": "medium",
                "description": "Your real public IP is exposed. A VPN tunnels traffic through an "
                "intermediary server, masking your true IP and location.",
            }
        )
        score += 20

    if score >= 70:
        level, color = "CRITICAL", "#ff0040"
    elif score >= 50:
        level, color = "HIGH", "#ff6b35"
    elif score >= 30:
        level, color = "MEDIUM", "#ffd700"
    else:
        level, color = "LOW", "#00ff41"

    return {"score": min(score, 100), "level": level, "color": color, "factors": factors}


@router.post("/analyze")
async def analyze_location(request: Request, data: LocationData):
    client_ip = request.headers.get("X-Forwarded-For", request.client.host or "")
    if "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()
    # Strip port if present
    if ":" in client_ip and not client_ip.startswith("["):
        client_ip = client_ip.split(":")[0]

    ip_info: dict = {}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"https://ipapi.co/{client_ip}/json/")
            if r.status_code == 200:
                ip_info = r.json()
    except Exception:
        ip_info = {"error": "Could not reach IP geolocation service"}

    has_gps = data.latitude is not None and data.longitude is not None

    return {
        "ip": client_ip,
        "ip_location": ip_info,
        "gps": (
            {"latitude": data.latitude, "longitude": data.longitude, "accuracy_meters": data.accuracy}
            if has_gps
            else None
        ),
        "risk": _assess_risk(ip_info, has_gps),
        "tracking_methods": TRACKING_METHODS,
    }


@router.get("/ip")
async def get_ip(request: Request):
    client_ip = request.headers.get("X-Forwarded-For", request.client.host or "127.0.0.1")
    if "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()
    if ":" in client_ip and not client_ip.startswith("["):
        client_ip = client_ip.split(":")[0]
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"https://ipapi.co/{client_ip}/json/")
            if r.status_code == 200:
                return r.json()
    except Exception as exc:
        return {"error": str(exc), "ip": client_ip}
    return {"ip": client_ip}

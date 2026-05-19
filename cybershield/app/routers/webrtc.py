from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

_PRIVATE_PREFIXES = (
    "10.", "192.168.",
    "172.16.", "172.17.", "172.18.", "172.19.", "172.20.",
    "172.21.", "172.22.", "172.23.", "172.24.", "172.25.",
    "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.",
    "127.", "169.254.", "::1", "fc", "fd",
)

STUN_SERVERS = [
    {"url": "stun:stun.l.google.com:19302", "provider": "Google"},
    {"url": "stun:stun1.l.google.com:19302", "provider": "Google (backup)"},
    {"url": "stun:stun.cloudflare.com:3478", "provider": "Cloudflare"},
    {"url": "stun:stun.nextcloud.com:443", "provider": "Nextcloud"},
]


class WebRTCReport(BaseModel):
    discovered_ips: List[str] = []


@router.get("/stun-servers")
async def get_stun_servers():
    return {"servers": STUN_SERVERS}


@router.post("/report")
async def report_webrtc(request: Request, data: WebRTCReport):
    server_ip = request.headers.get("X-Forwarded-For", request.client.host or "")
    if "," in server_ip:
        server_ip = server_ip.split(",")[0].strip()
    if ":" in server_ip and not server_ip.startswith("["):
        server_ip = server_ip.split(":")[0]

    private_ips: List[str] = []
    public_ips: List[str] = []

    for ip in data.discovered_ips:
        if _is_private(ip):
            private_ips.append(ip)
        else:
            public_ips.append(ip)

    public_ips = list(set(public_ips))

    # A leak exists when WebRTC reveals a public IP different from what the server sees.
    # If behind a VPN, the server sees the VPN IP; WebRTC might reveal the real IP.
    leaked_ips = [ip for ip in public_ips if ip != server_ip]
    leak_detected = len(leaked_ips) > 0

    return {
        "server_detected_ip": server_ip,
        "webrtc_private_ips": private_ips,
        "webrtc_public_ips": public_ips,
        "leaked_ips": leaked_ips,
        "leak_detected": leak_detected,
        "risk_level": "HIGH" if leak_detected else ("MEDIUM" if private_ips else "LOW"),
        "risk_color": "#ff0040" if leak_detected else ("#ffd700" if private_ips else "#00ff41"),
        "summary": (
            f"WebRTC PUBLIC IP LEAK DETECTED. Your real IP ({', '.join(leaked_ips)}) is exposed "
            "despite your VPN/proxy. WebRTC uses ICE/STUN to find the shortest data path and "
            "deliberately bypasses proxy settings to establish direct peer connections."
            if leak_detected
            else (
                "Private/local IPs were discovered via WebRTC (this is normal — it's your LAN address). "
                "No public IP leak was detected."
                if private_ips
                else "No IP leak detected via WebRTC. Your browser or VPN is successfully blocking WebRTC IP discovery."
            )
        ),
        "technical_detail": {
            "what_is_webrtc": (
                "WebRTC (Web Real-Time Communication) is a browser API enabling peer-to-peer audio/video/data. "
                "It uses ICE (Interactive Connectivity Establishment) to discover the fastest route between peers, "
                "which involves querying STUN servers for your public IP — even when you're behind a VPN."
            ),
            "why_vpns_fail": (
                "Most VPNs only route TCP/UDP traffic through their tunnel. WebRTC uses STUN over UDP "
                "and can bypass VPN routing tables, revealing your real ISP IP before the VPN tunnel is established."
            ),
        },
        "remediation": (
            [
                "Firefox: Open about:config → search media.peerconnection.enabled → set to false",
                "Chrome/Edge: Install 'WebRTC Leak Prevent' or 'uBlock Origin' extension and enable WebRTC protection",
                "Use Brave Browser — blocks WebRTC IP leakage by default",
                "Use the Tor Browser — WebRTC is completely disabled",
                "If using a commercial VPN, enable its 'WebRTC Leak Protection' or 'DNS Leak Protection' setting",
            ]
            if leak_detected
            else []
        ),
    }


def _is_private(ip: str) -> bool:
    return any(ip.startswith(p) for p in _PRIVATE_PREFIXES)

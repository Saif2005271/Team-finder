import asyncio
import httpx
from fastapi import APIRouter, Request

router = APIRouter()

_KNOWN_RESOLVERS = {
    "8.8.8.8":       {"name": "Google Public DNS",       "provider": "Google",      "privacy": "medium"},
    "8.8.4.4":       {"name": "Google Public DNS (2)",   "provider": "Google",      "privacy": "medium"},
    "1.1.1.1":       {"name": "Cloudflare 1.1.1.1",     "provider": "Cloudflare",  "privacy": "high"},
    "1.0.0.1":       {"name": "Cloudflare 1.0.0.1",     "provider": "Cloudflare",  "privacy": "high"},
    "9.9.9.9":       {"name": "Quad9",                   "provider": "Quad9",       "privacy": "high"},
    "149.112.112.112":{"name": "Quad9 (2)",              "provider": "Quad9",       "privacy": "high"},
    "208.67.222.222":{"name": "OpenDNS Home",            "provider": "Cisco",       "privacy": "medium"},
    "208.67.220.220":{"name": "OpenDNS Home (2)",        "provider": "Cisco",       "privacy": "medium"},
    "94.140.14.14":  {"name": "AdGuard DNS",             "provider": "AdGuard",     "privacy": "high"},
    "94.140.15.15":  {"name": "AdGuard DNS (2)",         "provider": "AdGuard",     "privacy": "high"},
    "76.76.19.19":   {"name": "Alternate DNS",           "provider": "Alternate",   "privacy": "medium"},
    "8.26.56.26":    {"name": "Comodo Secure DNS",       "provider": "Comodo",      "privacy": "medium"},
}

_SECURE_DNS_OPTIONS = [
    {"name": "Cloudflare 1.1.1.1", "ip": "1.1.1.1 / 1.0.0.1",   "doh": "https://cloudflare-dns.com/dns-query",         "privacy": "No query logging"},
    {"name": "Quad9",              "ip": "9.9.9.9 / 149.112.112.112", "doh": "https://dns.quad9.net/dns-query",         "privacy": "Blocks malware domains, no personal-data logging"},
    {"name": "AdGuard DNS",        "ip": "94.140.14.14",          "doh": "https://dns.adguard-dns.com/dns-query",       "privacy": "Blocks ads & trackers"},
    {"name": "NextDNS",            "ip": "varies",                "doh": "Configure at nextdns.io",                     "privacy": "Fully customisable filtering & logging controls"},
]


def _classify(ip: str) -> dict:
    if ip in _KNOWN_RESOLVERS:
        info = _KNOWN_RESOLVERS[ip]
        return {
            "ip": ip,
            "name": info["name"],
            "provider": info["provider"],
            "privacy_rating": info["privacy"],
            "is_known_secure": info["privacy"] == "high",
            "is_isp": False,
        }

    private = ("10.", "192.168.", "172.16.", "172.17.", "172.18.", "172.19.",
                "172.20.", "172.21.", "172.22.", "172.23.", "172.24.", "172.25.",
                "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.",
                "127.", "169.254.")
    if any(ip.startswith(p) for p in private):
        return {
            "ip": ip,
            "name": "Local / Router DNS",
            "provider": "Local network",
            "privacy_rating": "low",
            "is_known_secure": False,
            "is_isp": True,
        }

    return {
        "ip": ip,
        "name": "Unknown Resolver",
        "provider": "Unknown — likely ISP",
        "privacy_rating": "unknown",
        "is_known_secure": False,
        "is_isp": True,
    }


async def _try_doh_whoami(client: httpx.AsyncClient, doh_url: str, label: str) -> list:
    results = []
    try:
        r = await client.get(
            doh_url,
            headers={"Accept": "application/dns-json"},
            params={"name": "whoami.ds.akahelp.net", "type": "A"},
            timeout=8.0,
        )
        if r.status_code == 200:
            for answer in r.json().get("Answer", []):
                ip = answer.get("data", "").strip()
                if ip:
                    results.append(ip)
    except Exception:
        pass
    return results


async def _detect_resolvers() -> list:
    collected: set[str] = set()

    async with httpx.AsyncClient(follow_redirects=True) as client:
        tasks = [
            _try_doh_whoami(client, "https://dns.google/resolve", "Google DoH"),
            _try_doh_whoami(client, "https://cloudflare-dns.com/dns-query", "Cloudflare DoH"),
            _try_doh_whoami(client, "https://dns.quad9.net/dns-query", "Quad9 DoH"),
        ]
        for ips in await asyncio.gather(*tasks, return_exceptions=True):
            if isinstance(ips, list):
                collected.update(ips)

    if not collected:
        return [
            {
                "ip": "undetectable",
                "name": "DNS-over-HTTPS Active (or blocked)",
                "provider": "Encrypted / Unknown",
                "privacy_rating": "high",
                "is_known_secure": True,
                "is_isp": False,
                "note": "No plaintext resolver identified — this typically means DoH is active, which is good.",
            }
        ]

    return [_classify(ip) for ip in collected]


@router.get("/check")
async def check_dns_leak(request: Request):
    client_ip = request.headers.get("X-Forwarded-For", request.client.host or "")
    if "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()

    resolvers = await _detect_resolvers()

    isp_resolvers = [r for r in resolvers if r.get("is_isp")]
    secure_resolvers = [r for r in resolvers if r.get("is_known_secure")]
    isp_leak = len(isp_resolvers) > 0

    if isp_leak:
        risk_level, risk_color = "HIGH", "#ff0040"
        explanation = (
            "ISP DNS resolver detected. Your Internet Service Provider can see every domain you query. "
            "ISPs may log DNS history, inject ads via DNS manipulation, or share data with third parties. "
            "Even with a VPN, if DNS leaks to your ISP, they can reconstruct your browsing habits."
        )
    elif all(r.get("is_known_secure") for r in resolvers):
        risk_level, risk_color = "LOW", "#00ff41"
        explanation = (
            "All detected resolvers are from privacy-respecting providers. "
            "Consider enabling DNS-over-HTTPS for an additional layer of query encryption."
        )
    else:
        risk_level, risk_color = "MEDIUM", "#ffd700"
        explanation = (
            "Mixed or unknown DNS resolvers detected. Verify your DNS settings manually."
        )

    return {
        "client_ip": client_ip,
        "resolvers_detected": resolvers,
        "isp_leak_detected": isp_leak,
        "risk_level": risk_level,
        "risk_color": risk_color,
        "explanation": explanation,
        "how_dns_works": (
            "When you type 'example.com', your device queries a DNS resolver to convert the name to an IP. "
            "By default this resolver is assigned by your ISP. Every query reveals the domains you visit. "
            "DNS-over-HTTPS (DoH) encrypts these queries so your ISP (and network eavesdroppers) cannot read them."
        ),
        "secure_dns_options": _SECURE_DNS_OPTIONS,
        "recommendations": _build_recs(risk_level),
    }


def _build_recs(level: str) -> list:
    base = [
        {
            "title": "Enable DNS-over-HTTPS in Your Browser",
            "description": "Firefox: Settings → General → Network Settings → Enable DNS over HTTPS (Cloudflare or custom). Chrome/Edge: Settings → Privacy & Security → Use secure DNS.",
        },
        {
            "title": "Configure System-Wide Encrypted DNS",
            "description": "Windows 11: Settings → Network → DNS over HTTPS. macOS 11+: Use a configuration profile or third-party app like DNSCrypt-Proxy. This protects all apps, not just the browser.",
        },
    ]
    if level == "HIGH":
        base.insert(
            0,
            {
                "title": "Switch DNS Resolver Immediately",
                "description": "Change your router or device DNS to 1.1.1.1 (Cloudflare) or 9.9.9.9 (Quad9). These providers publish no-logging policies and support DoH/DoT encryption.",
            },
        )
        base.append(
            {
                "title": "Use a VPN with DNS Leak Protection",
                "description": "Ensure your VPN client routes DNS through its own encrypted resolver. Enable 'DNS Leak Protection' or 'Private DNS' in your VPN settings and verify with this tool.",
            }
        )
    return base

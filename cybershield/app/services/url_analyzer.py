import re
import unicodedata
import urllib.parse
from datetime import datetime, timezone
from typing import Optional

import httpx
import tldextract

# Cyrillic / Greek / Armenian characters that are visually identical to Latin equivalents
_CONFUSABLES: dict[str, str] = {
    # Cyrillic
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x",
    "і": "i", "ї": "i", "ј": "j", "ѕ": "s", "ԁ": "d", "ԛ": "q",
    "ԝ": "w", "ᴀ": "a", "ᴄ": "c", "ᴅ": "d", "ᴇ": "e", "ᴋ": "k",
    # Greek
    "ο": "o", "ρ": "p", "ν": "v", "κ": "k", "υ": "u", "ω": "w",
    # Armenian
    "ո": "n", "հ": "h", "տ": "s",
}

_SUSPICIOUS_KEYWORDS = [
    "login", "signin", "sign-in", "logon", "log-in",
    "account", "verify", "verification", "secure", "security",
    "update", "confirm", "banking", "paypal", "amazon",
    "google", "microsoft", "apple", "netflix", "instagram",
    "facebook", "password", "credential", "wallet", "crypto",
    "urgent", "suspended", "locked", "validate", "restore",
    "unusual", "alert", "limited", "expire",
]

_HIGH_RISK_TLDS = {
    ".tk", ".ml", ".ga", ".cf", ".gq", ".pw", ".top", ".xyz",
    ".click", ".link", ".work", ".loan", ".online", ".site",
    ".info", ".buzz", ".icu",
}

_SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly",
    "short.link", "tiny.cc", "is.gd", "buff.ly", "rb.gy",
    "cutt.ly", "shorturl.at", "clck.ru",
}

_IP_RE = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")


async def analyze_url(url: str) -> dict:
    if "://" not in url:
        url = "https://" + url

    try:
        parsed = urllib.parse.urlparse(url)
        ext = tldextract.extract(url)
    except Exception as exc:
        return {"error": f"Could not parse URL: {exc}"}

    hostname = parsed.hostname or ""
    registered_domain = ext.registered_domain or hostname
    tld_str = f".{ext.suffix}" if ext.suffix else ""
    subdomain_parts = [p for p in (ext.subdomain or "").split(".") if p]
    url_lower = url.lower()

    risk_factors = []
    score = 0

    # ── 1. Homograph / IDN detection ──────────────────────────────────────────
    hg = _check_homograph(hostname)
    if hg["detected"]:
        risk_factors.append(
            {
                "id": "homograph",
                "severity": "critical",
                "title": "Homograph / IDN Spoofing Attack",
                "description": (
                    f"Non-ASCII characters found in domain that visually impersonate ASCII equivalents: "
                    f"{', '.join(hg['suspicious_chars'])}. This is a hallmark of IDN homograph phishing."
                ),
            }
        )
        score += 45

    # ── 2. Mixed Unicode scripts ───────────────────────────────────────────────
    if hg["mixed_scripts"]:
        risk_factors.append(
            {
                "id": "mixed_scripts",
                "severity": "critical",
                "title": "Mixed Unicode Scripts in Domain",
                "description": (
                    f"Domain mixes scripts: {', '.join(hg['scripts'])}. "
                    "Browsers may render mixed-script domains as visually identical to well-known sites."
                ),
            }
        )
        score += 20

    # ── 3. Suspicious brand keywords ──────────────────────────────────────────
    found_kw = [kw for kw in _SUSPICIOUS_KEYWORDS if kw in url_lower]
    if found_kw:
        risk_factors.append(
            {
                "id": "suspicious_keywords",
                "severity": "medium",
                "title": "Suspicious Keywords in URL",
                "description": f"Phishing-associated keywords detected: {', '.join(found_kw[:6])}.",
            }
        )
        score += min(len(found_kw) * 8, 30)

    # ── 4. High-risk TLD ──────────────────────────────────────────────────────
    if tld_str in _HIGH_RISK_TLDS:
        risk_factors.append(
            {
                "id": "high_risk_tld",
                "severity": "high",
                "title": f"High-Risk TLD: {tld_str}",
                "description": (
                    f"The '{tld_str}' TLD is heavily abused in phishing and spam campaigns "
                    "due to free or near-free registration with minimal identity verification."
                ),
            }
        )
        score += 25

    # ── 5. No HTTPS ───────────────────────────────────────────────────────────
    if parsed.scheme != "https":
        risk_factors.append(
            {
                "id": "no_https",
                "severity": "medium",
                "title": "No HTTPS Encryption",
                "description": "Connection is unencrypted. Credentials or data entered on this page are transmitted in plaintext.",
            }
        )
        score += 15

    # ── 6. Excessive subdomains ───────────────────────────────────────────────
    if len(subdomain_parts) > 2:
        risk_factors.append(
            {
                "id": "excessive_subdomains",
                "severity": "medium",
                "title": f"Excessive Subdomain Depth ({len(subdomain_parts)} levels)",
                "description": (
                    "Phishing sites use deep subdomain nesting to hide the actual registered domain. "
                    f"Example: legitimate-brand.{registered_domain}"
                ),
            }
        )
        score += 20

    # ── 7. Raw IP host ────────────────────────────────────────────────────────
    if _IP_RE.match(hostname):
        risk_factors.append(
            {
                "id": "ip_host",
                "severity": "high",
                "title": "Raw IP Address as Host",
                "description": "Legitimate websites use domain names, not raw IPs. Phishing pages commonly use IP addresses to avoid domain registrar abuse checks.",
            }
        )
        score += 30

    # ── 8. URL shortener ──────────────────────────────────────────────────────
    if any(s in hostname for s in _SHORTENERS):
        risk_factors.append(
            {
                "id": "shortener",
                "severity": "medium",
                "title": "URL Shortener Detected",
                "description": "Shortened URLs hide the true destination, a common phishing technique. The final redirect target could be entirely different.",
            }
        )
        score += 20

    # ── 9. Excessive URL length ───────────────────────────────────────────────
    if len(url) > 100:
        risk_factors.append(
            {
                "id": "long_url",
                "severity": "low",
                "title": f"Unusually Long URL ({len(url)} chars)",
                "description": "Phishing URLs are often padded with random paths or parameters to obscure the real domain and confuse filters.",
            }
        )
        score += 10

    # ── 10. Domain age via RDAP ───────────────────────────────────────────────
    age_info = await _get_domain_age(registered_domain)
    if age_info.get("days_old") is not None and age_info["days_old"] < 30:
        risk_factors.append(
            {
                "id": "new_domain",
                "severity": "high",
                "title": f"Newly Registered Domain ({age_info['days_old']} days old)",
                "description": (
                    "Attackers register throwaway domains for phishing campaigns immediately before launching them. "
                    "Legitimate businesses rarely operate on domains less than 30 days old."
                ),
            }
        )
        score += 35

    score = min(score, 100)
    if score >= 70:
        level, color = "CRITICAL", "#ff0040"
    elif score >= 50:
        level, color = "HIGH", "#ff6b35"
    elif score >= 25:
        level, color = "MEDIUM", "#ffd700"
    else:
        level, color = "LOW", "#00ff41"

    return {
        "url": url,
        "parsed": {
            "scheme": parsed.scheme,
            "hostname": hostname,
            "registered_domain": registered_domain,
            "tld": tld_str,
            "subdomain": ext.subdomain or "",
            "path": parsed.path,
        },
        "risk_score": score,
        "risk_level": level,
        "risk_color": color,
        "risk_factors": risk_factors,
        "homograph_analysis": hg,
        "domain_age": age_info,
        "total_checks": 10,
        "checks_flagged": len(risk_factors),
    }


def _check_homograph(domain: str) -> dict:
    suspicious: list[str] = []
    scripts: set[str] = set()

    for ch in domain:
        if ch in (".", "-", "_") or ch.isdigit():
            continue

        if ch in _CONFUSABLES:
            suspicious.append(f"U+{ord(ch):04X} '{ch}' → looks like '{_CONFUSABLES[ch]}'")

        try:
            name = unicodedata.name(ch, "")
        except Exception:
            name = ""

        for script in ("LATIN", "CYRILLIC", "GREEK", "ARMENIAN", "ARABIC", "CJK", "HANGUL", "HEBREW"):
            if script in name:
                scripts.add(script)
                break
        else:
            if not ch.isascii():
                scripts.add("OTHER")

    return {
        "detected": bool(suspicious) or len(scripts) > 1,
        "suspicious_chars": suspicious,
        "scripts": list(scripts),
        "mixed_scripts": len(scripts) > 1,
    }


async def _get_domain_age(domain: str) -> dict:
    if not domain or _IP_RE.match(domain):
        return {"registration_date": None, "days_old": None, "status": "n/a"}

    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            r = await client.get(f"https://rdap.org/domain/{domain}")
            if r.status_code == 200:
                for event in r.json().get("events", []):
                    if event.get("eventAction") == "registration":
                        date_str = event.get("eventDate", "")
                        if date_str:
                            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                            days = (datetime.now(timezone.utc) - dt).days
                            return {
                                "registration_date": date_str[:10],
                                "days_old": days,
                                "status": "new" if days < 30 else "recent" if days < 365 else "established",
                            }
    except Exception:
        pass

    return {"registration_date": None, "days_old": None, "status": "unknown"}

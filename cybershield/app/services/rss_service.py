import asyncio
import html
import re
from datetime import datetime, timezone
from typing import Optional

import feedparser
import httpx

_FEEDS = [
    {"name": "Krebs on Security",   "url": "https://krebsonsecurity.com/feed/",                       "category": "Investigative",  "reliability": "authoritative"},
    {"name": "The Hacker News",     "url": "https://feeds.feedburner.com/TheHackersNews",              "category": "Breaking",       "reliability": "high"},
    {"name": "Bleeping Computer",   "url": "https://www.bleepingcomputer.com/feed/",                   "category": "Malware",        "reliability": "high"},
    {"name": "CISA Advisories",     "url": "https://www.cisa.gov/cybersecurity-advisories/all.xml",    "category": "Government",     "reliability": "authoritative"},
    {"name": "Dark Reading",        "url": "https://www.darkreading.com/rss.xml",                      "category": "Enterprise",     "reliability": "high"},
    {"name": "Threatpost",          "url": "https://threatpost.com/feed/",                             "category": "Exploits",       "reliability": "high"},
    {"name": "Schneier on Security","url": "https://www.schneier.com/feed/atom/",                      "category": "Analysis",       "reliability": "authoritative"},
]

_STRIP_TAGS = re.compile(r"<[^>]+>")
_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

_CRITICAL_KW  = {"zero-day","0-day","actively exploited","remote code execution","rce","critical patch","emergency update","patch tuesday","in the wild"}
_HIGH_KW      = {"ransomware","data breach","backdoor","botnet","nation-state","supply chain","apt","privilege escalation","authentication bypass"}
_MEDIUM_KW    = {"phishing","malware","spyware","trojan","worm","vulnerability","cve","adware","stalkerware"}
_LOW_KW       = {"scam","fraud","social engineering","spam"}
_MOBILE_KW    = {"android","ios","iphone","ipad","mobile","smartphone","app store","google play","pixel","samsung galaxy"}
_IOS_KW       = {"ios","iphone","ipad","apple","webkit","safari","testflight","app store"}
_ANDROID_KW   = {"android","google play","pixel","samsung","oneplus","huawei","aosp"}


def _clean(text: str) -> str:
    return html.unescape(_STRIP_TAGS.sub(" ", text or "")).strip()


def _classify(title: str, summary: str) -> dict:
    blob = (title + " " + summary).lower()

    severity = "info"
    for kw in _CRITICAL_KW:
        if kw in blob:
            severity = "critical"
            break
    if severity == "info":
        for kw in _HIGH_KW:
            if kw in blob:
                severity = "high"
                break
    if severity == "info":
        for kw in _MEDIUM_KW:
            if kw in blob:
                severity = "medium"
                break
    if severity == "info":
        for kw in _LOW_KW:
            if kw in blob:
                severity = "low"
                break

    tags: list[str] = []
    if any(k in blob for k in _MOBILE_KW):
        tags.append("mobile")
    if any(k in blob for k in _IOS_KW):
        tags.append("iOS")
    if any(k in blob for k in _ANDROID_KW):
        tags.append("Android")
    if "zero-day" in blob or "0-day" in blob:
        tags.append("zero-day")
    if "ransomware" in blob:
        tags.append("ransomware")
    if "cve-" in blob:
        # extract first CVE id
        m = re.search(r"cve-\d{4}-\d+", blob)
        if m:
            tags.append(m.group().upper())
    if "phishing" in blob:
        tags.append("phishing")
    if "supply chain" in blob:
        tags.append("supply-chain")

    return {"severity": severity, "tags": list(dict.fromkeys(tags))}


async def _fetch_one(feed_cfg: dict, per_feed: int) -> list[dict]:
    articles: list[dict] = []
    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            r = await client.get(
                feed_cfg["url"],
                headers={"User-Agent": "CyberShield-Privacy-Auditor/1.0 RSS Reader"},
            )
        if r.status_code != 200:
            return articles

        feed = feedparser.parse(r.text)
        for entry in feed.entries[:per_feed]:
            title   = _clean(entry.get("title", "No Title"))
            summary = _clean(entry.get("summary", entry.get("description", "")))
            if len(summary) > 320:
                summary = summary[:320].rsplit(" ", 1)[0] + " …"

            pub = entry.get("published", entry.get("updated", ""))
            cls = _classify(title, summary)

            articles.append(
                {
                    "title":       title,
                    "url":         entry.get("link", "#"),
                    "summary":     summary,
                    "published":   pub,
                    "source":      feed_cfg["name"],
                    "category":    feed_cfg["category"],
                    "reliability": feed_cfg["reliability"],
                    "severity":    cls["severity"],
                    "tags":        cls["tags"],
                }
            )
    except Exception:
        pass
    return articles


async def fetch_threat_feeds(limit: int = 30) -> dict:
    per_feed = max(5, limit // len(_FEEDS) + 2)
    tasks = [_fetch_one(f, per_feed) for f in _FEEDS]
    gathered = await asyncio.gather(*tasks, return_exceptions=True)

    all_articles: list[dict] = []
    sources_ok = 0
    for res in gathered:
        if isinstance(res, list) and res:
            all_articles.extend(res)
            sources_ok += 1

    # Sort by severity then recency (published string, lexicographic works for RFC-822 dates)
    all_articles.sort(
        key=lambda a: (
            _SEVERITY_ORDER.get(a["severity"], 9),
            # invert published so newest first within same severity
            "".join(reversed(a.get("published", ""))),
        )
    )

    articles = all_articles[:limit]
    stats = {s: sum(1 for a in articles if a["severity"] == s) for s in _SEVERITY_ORDER}
    stats["sources_online"] = sources_ok
    stats["sources_total"] = len(_FEEDS)

    return {
        "articles":     articles,
        "total_fetched": len(all_articles),
        "returned":     len(articles),
        "stats":        stats,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }

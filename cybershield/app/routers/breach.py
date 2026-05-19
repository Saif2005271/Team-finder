import hashlib
import os
import httpx
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class BreachRequest(BaseModel):
    query: str
    type: str  # "email" | "password"


@router.post("/check")
async def check_breach(data: BreachRequest):
    if data.type == "password":
        return await _check_password(data.query)
    elif data.type == "email":
        return await _check_email(data.query)
    return {"error": "type must be 'email' or 'password'"}


async def _check_password(password: str) -> dict:
    sha1 = hashlib.sha1(password.encode()).hexdigest().upper()
    prefix, suffix = sha1[:5], sha1[5:]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"https://api.pwnedpasswords.com/range/{prefix}",
                headers={"User-Agent": "CyberShield-Privacy-Auditor/1.0"},
            )
            if r.status_code == 403:
                return {
                    "network_restricted": True,
                    "type": "password",
                    "message": "The HaveIBeenPwned API is not reachable from this server's IP (cloud environments are often blocked by HIBP). Run CyberShield locally for full breach checking.",
                    "how_it_works": (
                        "Locally: your password is hashed with SHA-1, only the first 5 hex characters are sent to "
                        "api.pwnedpasswords.com/range/{prefix}. The server returns ~500 matching suffix:count pairs. "
                        "Your browser checks for a match — your plaintext password never leaves your machine."
                    ),
                    "direct_url": "https://haveibeenpwned.com/Passwords",
                }
            if r.status_code == 200:
                for line in r.text.splitlines():
                    h_suffix, count_str = line.split(":")
                    if h_suffix == suffix:
                        count = int(count_str)
                        return {
                            "breached": True,
                            "type": "password",
                            "count": count,
                            "severity": "critical" if count > 10_000 else "high",
                            "message": f"This password appeared in {count:,} known data breaches. Change it immediately on every site where it's used.",
                            "recommendations": [
                                "Change this password on ALL sites that use it — right now.",
                                "Use a password manager (Bitwarden, 1Password) to generate unique 20+ char passwords.",
                                "Enable hardware or app-based 2FA on every account.",
                                "Never reuse passwords — each service must get a unique credential.",
                                "Consider a passphrase: 4 random words are harder to crack than complex short strings.",
                            ],
                        }
                return {
                    "breached": False,
                    "type": "password",
                    "message": "Password not found in any known breach database. Good start — but unique, long passwords are still recommended.",
                    "recommendations": [
                        "Store it in a password manager rather than memorising it.",
                        "Enable 2FA wherever supported.",
                        "Re-check periodically — new breaches are published daily.",
                    ],
                }
    except Exception as exc:
        return {"error": f"Could not reach breach database: {exc}"}


async def _check_email(email: str) -> dict:
    api_key = os.environ.get("HIBP_API_KEY", "")
    if not api_key:
        return {
            "demo": True,
            "type": "email",
            "message": "HaveIBeenPwned API key not configured.",
            "instructions": "Add HIBP_API_KEY=<your_key> to your .env file. Keys are available at https://haveibeenpwned.com/API/Key",
            "sample_output": {
                "breached": True,
                "breach_count": 4,
                "breaches": [
                    {
                        "name": "LinkedIn",
                        "date": "2012-05-05",
                        "data_types": ["Email addresses", "Passwords"],
                    },
                    {
                        "name": "Adobe",
                        "date": "2013-10-04",
                        "data_types": ["Email addresses", "Password hints", "Usernames"],
                    },
                ],
            },
        }

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            r = await client.get(
                f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}",
                headers={
                    "hibp-api-key": api_key,
                    "User-Agent": "CyberShield-Privacy-Auditor/1.0",
                },
                params={"truncateResponse": "false"},
            )

            if r.status_code == 200:
                breaches = r.json()
                count = len(breaches)
                return {
                    "breached": True,
                    "type": "email",
                    "breach_count": count,
                    "severity": "critical" if count > 5 else "high",
                    "breaches": [
                        {
                            "name": b.get("Name"),
                            "domain": b.get("Domain"),
                            "date": b.get("BreachDate"),
                            "pwn_count": b.get("PwnCount"),
                            "data_types": b.get("DataClasses", []),
                            "description": b.get("Description", ""),
                        }
                        for b in breaches
                    ],
                    "recommendations": [
                        "Change passwords on all listed services immediately.",
                        "Enable 2FA on every breached account.",
                        "This email may be sold to spam and phishing lists — watch for targeted attacks.",
                        "Check if this email is used for password-reset on other critical services.",
                        "Consider using email aliases (SimpleLogin, Apple Hide My Email) to limit exposure.",
                    ],
                }
            elif r.status_code == 404:
                return {
                    "breached": False,
                    "type": "email",
                    "message": "Great news — this email was not found in any publicly known data breaches.",
                    "recommendations": [
                        "Continue using unique passwords per service.",
                        "Enable 2FA everywhere.",
                        "Re-check every 3 months — new breaches surface regularly.",
                    ],
                }
            elif r.status_code == 429:
                return {"error": "Rate limited by HIBP. Please wait 60 seconds before retrying."}
            else:
                return {"error": f"HIBP API returned HTTP {r.status_code}"}

    except Exception as exc:
        return {"error": f"Could not reach HIBP: {exc}"}

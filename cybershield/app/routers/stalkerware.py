from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

router = APIRouter()

QUESTIONS = [
    {
        "id": "q01",
        "category": "Battery & Thermal",
        "icon": "🔋",
        "question": "Has your device's battery started draining significantly faster (30%+ more) without any change in your usage habits?",
        "weight": 15,
        "explanation": "Stalkerware runs 24/7 background processes — GPS polling, audio sampling, screen capture — keeping the CPU and radio active and consuming 15–40% extra battery.",
    },
    {
        "id": "q02",
        "category": "Data Usage",
        "icon": "📡",
        "question": "Have you noticed unexplained spikes in mobile data usage, particularly during nighttime hours or when your phone is 'idle'?",
        "weight": 20,
        "explanation": "Spyware exfiltrates intercepted data (recordings, photos, location logs, message copies) to remote C2 servers. It often waits for idle or overnight periods to upload large payloads and avoid detection.",
    },
    {
        "id": "q03",
        "category": "Thermal",
        "icon": "🌡️",
        "question": "Does your device feel warm or hot to the touch even when you haven't been using it intensively?",
        "weight": 14,
        "explanation": "Continuous background processing keeps the CPU active. Sustained CPU loads above 30% generate perceptible heat even during screen-off states.",
    },
    {
        "id": "q04",
        "category": "Call Behaviour",
        "icon": "📞",
        "question": "Have you heard clicking, static, faint voices, or background noise during phone calls that cannot be explained by signal quality?",
        "weight": 16,
        "explanation": "Some call-interception tools inject audio artefacts. However, poor network conditions also cause noise — treat this as a weak signal requiring corroboration from other indicators.",
    },
    {
        "id": "q05",
        "category": "Physical Access",
        "icon": "🔓",
        "question": "Has someone had unsupervised physical access to your unlocked device for more than 5 minutes in the past 6 months?",
        "weight": 25,
        "explanation": "Installing most commercial stalkerware (FlexiSPY, Hoverwatch, mSpy) requires 3–7 minutes of hands-on device access. This is the single highest-risk factor — it is the attack vector.",
    },
    {
        "id": "q06",
        "category": "Unknown Apps",
        "icon": "📱",
        "question": "Have you found unfamiliar apps in your application list that you have no memory of installing?",
        "weight": 22,
        "explanation": "Stalkerware typically disguises itself with benign names (System Service, Device Health, Phone Manager) or mimics utility apps. On Android, check Settings → Apps → Show system apps. On iOS, jailbreaks are usually required.",
    },
    {
        "id": "q07",
        "category": "Screen Behaviour",
        "icon": "💡",
        "question": "Does your screen light up, LED flash, or device vibrate when it should be in deep sleep with no notifications expected?",
        "weight": 12,
        "explanation": "Some spyware periodically wakes the device to take screenshots, sync location, or start a covert recording session. Random wake events with no associated notification are a notable anomaly.",
    },
    {
        "id": "q08",
        "category": "Permissions",
        "icon": "🛡️",
        "question": "Have apps requested permissions (microphone, camera, contacts, location, call logs) that don't match their stated function?",
        "weight": 18,
        "explanation": "A flashlight app with microphone access is a red flag. Stalkerware disguised as utility apps requires broad permissions to operate. Audit permissions regularly in your OS settings.",
    },
    {
        "id": "q09",
        "category": "Account Activity",
        "icon": "🔑",
        "question": "Have you received unexpected login alerts, found messages marked 'read' that you never opened, or noticed account activity you didn't initiate?",
        "weight": 18,
        "explanation": "This indicates either stolen credentials or active device monitoring. A keylogger or screen recorder can capture passwords; some stalkerware directly accesses cloud account syncs.",
    },
    {
        "id": "q10",
        "category": "Information Leakage",
        "icon": "🕵️",
        "question": "Has someone in your life demonstrated knowledge of private conversations, your location, or activities they could only know through surveillance?",
        "weight": 30,
        "explanation": "This is the most definitive behavioural indicator. If someone consistently 'knows things they shouldn't', it strongly suggests active monitoring via device, account access, or physical surveillance.",
    },
]


class QuizAnswers(BaseModel):
    answers: List[dict]  # [{"question_id": str, "answer": bool}]


@router.get("/questions")
async def get_questions():
    return {
        "questions": [
            {
                "id": q["id"],
                "category": q["category"],
                "icon": q["icon"],
                "question": q["question"],
            }
            for q in QUESTIONS
        ],
        "total": len(QUESTIONS),
    }


@router.post("/assess")
async def assess_risk(data: QuizAnswers):
    answer_map = {a["question_id"]: a.get("answer", False) for a in data.answers}
    max_score = sum(q["weight"] for q in QUESTIONS)

    triggered = []
    total = 0
    for q in QUESTIONS:
        if answer_map.get(q["id"], False):
            total += q["weight"]
            triggered.append(
                {
                    "category": q["category"],
                    "icon": q["icon"],
                    "question": q["question"],
                    "explanation": q["explanation"],
                    "weight": q["weight"],
                }
            )

    pct = round((total / max_score) * 100, 1)

    if pct >= 60:
        level, color = "HIGH RISK", "#ff0040"
        summary = (
            "Multiple high-severity behavioural indicators are present. "
            "The pattern is consistent with active device surveillance. "
            "Follow the HIGH-priority remediation steps immediately."
        )
    elif pct >= 35:
        level, color = "MODERATE RISK", "#ff6b35"
        summary = (
            "Several indicators align with common stalkerware behaviour. "
            "While not conclusive individually, the combination warrants a thorough audit."
        )
    elif pct >= 15:
        level, color = "LOW RISK", "#ffd700"
        summary = (
            "A few minor anomalies detected. These could have innocent explanations, "
            "but basic precautionary steps are advisable."
        )
    else:
        level, color = "MINIMAL RISK", "#00ff41"
        summary = (
            "No significant behavioural indicators of stalkerware detected. "
            "Maintain regular security hygiene to stay protected."
        )

    return {
        "score": pct,
        "level": level,
        "color": color,
        "summary": summary,
        "triggered_factors": triggered,
        "remediation": _build_remediation(pct, triggered),
    }


def _build_remediation(score: float, factors: list) -> list:
    categories = {f["category"] for f in factors}
    steps = []

    steps.append(
        {
            "priority": "IMMEDIATE",
            "title": "Audit All App Permissions",
            "description": "Go to your device privacy settings and systematically review which apps hold microphone, camera, location, contacts, and call-log permissions. Revoke anything that seems unnecessary.",
            "ios": "Settings → Privacy & Security → each permission category",
            "android": "Settings → Apps → Permissions Manager",
        }
    )

    if "Physical Access" in categories or score >= 40:
        steps.append(
            {
                "priority": "IMMEDIATE",
                "title": "Run a Mobile Security Scan",
                "description": "Install Malwarebytes for Mobile or Lookout Security and run a full scan. On Android, check for unknown Device Administrators and uninstall them.",
                "ios": "App Store → Malwarebytes",
                "android": "Settings → Security → Device Admin Apps → investigate unknowns",
            }
        )

    if "Unknown Apps" in categories or score >= 35:
        steps.append(
            {
                "priority": "HIGH",
                "title": "Audit Your Complete App List",
                "description": "Review every installed app. On Android, enable 'Show system apps'. Look for apps with no icons, generic names (System Service, Device Manager), or no Play Store listing.",
                "ios": "Settings → General → iPhone Storage",
                "android": "Settings → Apps → ⋮ → Show system apps",
            }
        )

    if "Data Usage" in categories:
        steps.append(
            {
                "priority": "HIGH",
                "title": "Investigate Data Usage Anomalies",
                "description": "Sort apps by data consumption. Any unrecognised app consuming significant data — especially at night — should be uninstalled immediately.",
                "ios": "Settings → Cellular → scroll to per-app usage",
                "android": "Settings → Network → Mobile data usage → sort by app",
            }
        )

    if score >= 50:
        steps.append(
            {
                "priority": "HIGH",
                "title": "Factory Reset (Nuclear Option)",
                "description": "A factory reset is the most reliable stalkerware removal method. Back up contacts and essential files to a trusted computer first. Restore apps manually — do NOT restore from a cloud backup as it may reinstall the spyware.",
                "ios": "Settings → General → Transfer or Reset iPhone → Erase All Content",
                "android": "Settings → General Management → Reset → Factory data reset",
            }
        )

    steps.append(
        {
            "priority": "ONGOING",
            "title": "Enable App-Based Two-Factor Authentication",
            "description": "Protect all critical accounts (email, banking, social) with an authenticator app, not SMS. SMS can be intercepted; app-based 2FA cannot.",
            "ios": "Use built-in passkeys or Duo/Google Authenticator",
            "android": "Use Google Authenticator, Aegis, or Duo",
        }
    )

    steps.append(
        {
            "priority": "ONGOING",
            "title": "Keep OS and Apps Updated",
            "description": "Security patches close the vulnerabilities stalkerware exploits. Enable automatic updates. Check your OS version against the latest release.",
            "ios": "Settings → General → Software Update",
            "android": "Settings → Software Update",
        }
    )

    if score >= 40:
        steps.append(
            {
                "priority": "SAFETY",
                "title": "Safety Planning & Support Resources",
                "description": "If you believe you're being monitored by a domestic partner or abuser, contact these organisations from a trusted device you control.",
                "resources": [
                    "Coalition Against Stalkerware: stopstalkerware.org",
                    "National DV Hotline (US): 1-800-799-7233 | thehotline.org",
                    "Safety Net (NNEDV): techsafety.org",
                    "UK: Refuge — 0808 2000 247",
                ],
                "ios": "Use a library computer or trusted friend's device for these contacts.",
                "android": "Use a library computer or trusted friend's device for these contacts.",
            }
        )

    return steps

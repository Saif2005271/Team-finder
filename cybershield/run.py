import uvicorn
import os
import sys
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 8000))

    # reload=True uses multiprocessing on Windows and requires the
    # __main__ guard — which we have — but watchfiles can still cause
    # an immediate shutdown on some Windows setups. Disable it so the
    # server stays alive; restart manually after code changes instead.
    reload = sys.platform != "win32"

    print(f"\n  CyberShield is running at:  http://{host}:{port}\n")

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )

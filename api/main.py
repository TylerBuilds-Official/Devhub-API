"""
DevHub API entrypoint.

Run interactively:
    python -m api.main

Or via uvicorn directly (with reload during development):
    uvicorn api.main:app --reload --host 0.0.0.0 --port 8766

Once deployed, NSSM points at this same module on the eventual DevHub VM.

Workers is intentionally 1 for now — lifespan holds a single shared
UpdateSuiteClient on app.state, so additional workers would each create
their own (independent) client and connection pool.

.env is loaded BEFORE api.build is imported so every module that reads
os.getenv at import time (db.py, upstream_client.py, health_poller.py)
sees the resolved values.
"""
from dotenv import load_dotenv

load_dotenv()

import uvicorn

from api.build.build_api import build_api


app = build_api()


if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host    = "0.0.0.0",
        port    = 8766,
        reload  = False,
        workers = 1,
    )

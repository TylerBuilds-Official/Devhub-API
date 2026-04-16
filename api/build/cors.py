"""
CORS configuration.

Wide-open for MVP while the frontend is on localhost. Tighten to the
dev-hub frontend origin(s) once the deploy URL is known.
"""
from fastapi                    import FastAPI
from fastapi.middleware.cors    import CORSMiddleware


def attach_cors(app: FastAPI) -> None:
    """Mount the CORS middleware. Wide-open for MVP."""

    app.add_middleware(
        CORSMiddleware,
        allow_origins     = ["*"],
        allow_credentials = False,
        allow_methods     = ["*"],
        allow_headers     = ["*"],
    )

"""Explicit browser origins; CORS is not authentication or an upload quota."""
import os
from urllib.parse import urlsplit


def allowed_origins():
    origins = [value.strip() for value in os.getenv(
        "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",") if value.strip()]
    for origin in origins:
        parsed = urlsplit(origin)
        if (parsed.scheme not in {"http", "https"} or not parsed.netloc
                or parsed.username or parsed.password or parsed.path
                or parsed.query or parsed.fragment or "*" in origin):
            raise ValueError("CORS_ORIGINS must contain exact HTTP(S) origins without paths")
    return origins


def cors_options():
    return dict(allow_origins=allowed_origins(), allow_credentials=False,
                allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

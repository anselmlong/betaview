"""
Modal deployment entrypoint for the BetaView FastAPI backend.
"""

import sys

import modal


image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg", "libgl1")
    .pip_install_from_requirements("backend/requirements.txt")
    .add_local_dir("backend", remote_path="/root/backend", copy=True)
)

app = modal.App("betaview-api", image=image)


# Exact browser origins allowed by backend/cors_config.py; the default is localhost only.
cors = modal.Secret.from_dict(
    {"CORS_ORIGINS": "https://betaview.anselmlong.com,https://betaview.vercel.app"}
)


@app.function(cpu=4, memory=8192, timeout=900, secrets=[cors])
@modal.asgi_app()
def fastapi_app():
    sys.path.insert(0, "/root/backend")
    from main import app as backend_app

    return backend_app

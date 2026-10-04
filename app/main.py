import os
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.downloader import download_service

app = FastAPI(title="YouTube Downloader Local")

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
VALID_DOMAINS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
}
VALID_FORMATS = {"mp4", "mp3"}
VALID_QUALITIES = {"best", "1080p", "720p", "480p"}


def is_valid_youtube_url(url: str) -> bool:
    """Verifica si la URL tiene un esquema válido y pertenece a un dominio de YouTube."""
    try:
        parsed = urlparse(url.strip())
        if parsed.scheme not in ("http", "https"):
            return False
        netloc = parsed.netloc.lower()
        domain = netloc.split(":")[0]
        return domain in VALID_DOMAINS
    except Exception:
        return False


class DownloadRequest(BaseModel):
    url: str = Field(..., description="URL del vídeo de YouTube")
    format: str = Field(default="mp4", description="Formato de salida: 'mp4' o 'mp3'")
    quality: str = Field(
        default="best",
        description="Calidad para MP4: 'best', '1080p', '720p', '480p'",
    )


# Montar archivos estáticos
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def read_root():
    """Sirve la interfaz web principal."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="Interfaz no encontrada")
    return FileResponse(index_path)


@app.post("/api/download", status_code=status.HTTP_202_ACCEPTED)
def request_download(payload: DownloadRequest):
    """Inicia una descarga en segundo plano."""
    url = payload.url.strip()
    fmt = payload.format.strip().lower()
    quality = payload.quality.strip().lower()

    if not is_valid_youtube_url(url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La URL debe ser un enlace válido de YouTube (ej. youtube.com o youtu.be).",
        )

    if fmt not in VALID_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato no admitido. Utiliza 'mp4' o 'mp3'.",
        )

    if fmt == "mp4" and quality not in VALID_QUALITIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Calidad no admitida para MP4. Utiliza 'best', '1080p', '720p' o '480p'.",
        )

    # Intento de inicio de descarga
    started = download_service.start_download(url=url, format_type=fmt, quality=quality)
    if not started:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una descarga activa en curso. Espera a que finalice.",
        )

    return {"status": "started", "message": "Descarga iniciada en segundo plano."}


@app.get("/api/status")
def check_status():
    """Devuelve el estado actual de la descarga."""
    return download_service.get_status()

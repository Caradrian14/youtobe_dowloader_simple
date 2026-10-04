from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
import yt_dlp

from app.downloader import DownloadService, check_ffmpeg, download_service
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_service_state():
    """Restaura el estado del servicio de descarga antes de cada test."""
    with download_service._lock:
        download_service._state = {
            "status": "idle",
            "percent": 0.0,
            "filename": None,
            "error": None,
        }
    yield
    with download_service._lock:
        download_service._state = {
            "status": "idle",
            "percent": 0.0,
            "filename": None,
            "error": None,
        }


def test_get_root_ui():
    """1. GET de la interfaz retorna 200 y sirve el HTML principal."""
    response = client.get("/")
    assert response.status_code == 200
    assert "YouTube Downloader" in response.text
    assert "<form id=\"downloadForm\"" in response.text


@pytest.mark.parametrize(
    "invalid_url",
    [
        "https://vimeo.com/123456",
        "https://dailymotion.com/video/x7",
        "ftp://youtube.com/watch?v=123",
        "notaurl",
        "",
    ],
)
def test_url_validation_invalid(invalid_url):
    """2. Validación de URL: rechaza URLs que no sean HTTP/HTTPS de YouTube."""
    response = client.post(
        "/api/download",
        json={"url": invalid_url, "format": "mp4", "quality": "best"},
    )
    # Pydantic o el endpoint devuelven 400 o 422 para entrada no válida
    assert response.status_code in (400, 422)


@pytest.mark.parametrize(
    "valid_url",
    [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "http://youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
    ],
)
def test_url_validation_valid(valid_url):
    """2b. Validación de URL: acepta los diferentes formatos de URL de YouTube."""
    with patch.object(download_service, "start_download", return_value=True):
        response = client.post(
            "/api/download",
            json={"url": valid_url, "format": "mp4", "quality": "best"},
        )
        assert response.status_code == 202
        assert response.json()["status"] == "started"


def test_format_validation():
    """3. Validación de formato y calidad."""
    # Formato no soportado
    resp1 = client.post(
        "/api/download",
        json={"url": "https://youtu.be/abc", "format": "avi"},
    )
    assert resp1.status_code == 400
    assert "Formato no admitido" in resp1.json()["detail"]

    # Calidad no soportada para MP4
    resp2 = client.post(
        "/api/download",
        json={"url": "https://youtu.be/abc", "format": "mp4", "quality": "4k"},
    )
    assert resp2.status_code == 400
    assert "Calidad no admitida" in resp2.json()["detail"]


def test_valid_post_download():
    """4. POST válido inicia la descarga y responde 202 Accepted."""
    with patch.object(download_service, "start_download", return_value=True) as mock_start:
        response = client.post(
            "/api/download",
            json={
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "format": "mp4",
                "quality": "1080p",
            },
        )
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "started"
        mock_start.assert_called_once_with(
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            format_type="mp4",
            quality="1080p",
        )


def test_post_conflict_when_already_downloading():
    """5. POST mientras existe otra descarga retorna 409 Conflict."""
    with download_service._lock:
        download_service._state["status"] = "downloading"

    response = client.post(
        "/api/download",
        json={
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "format": "mp4",
            "quality": "720p",
        },
    )
    assert response.status_code == 409
    assert "Ya existe una descarga activa" in response.json()["detail"]


def test_get_status():
    """6. GET /api/status retorna el estado actual del servicio."""
    with download_service._lock:
        download_service._state = {
            "status": "downloading",
            "percent": 45.5,
            "filename": None,
            "error": None,
        }

    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "downloading"
    assert data["percent"] == 45.5
    assert data["filename"] is None
    assert data["error"] is None


def test_mp4_configuration():
    """7. Comprobar opciones de configuración para MP4 (fallback y muxing)."""
    service = DownloadService()

    # Calidad 1080p
    opts_1080 = service._get_ydl_opts("mp4", "1080p")
    assert opts_1080["merge_output_format"] == "mp4"
    assert "height<=1080" in opts_1080["format"]
    assert opts_1080["noplaylist"] is True

    # Calidad 720p
    opts_720 = service._get_ydl_opts("mp4", "720p")
    assert "height<=720" in opts_720["format"]

    # Calidad 480p
    opts_480 = service._get_ydl_opts("mp4", "480p")
    assert "height<=480" in opts_480["format"]

    # Calidad best
    opts_best = service._get_ydl_opts("mp4", "best")
    assert opts_best["merge_output_format"] == "mp4"
    assert "bestvideo" in opts_best["format"]


def test_mp3_configuration():
    """8. Comprobar opciones de configuración para MP3 (audio extraction y FFmpeg)."""
    service = DownloadService()
    opts_mp3 = service._get_ydl_opts("mp3", "best")

    assert opts_mp3["format"] == "bestaudio/best"
    assert "postprocessors" in opts_mp3
    assert len(opts_mp3["postprocessors"]) == 1

    pp = opts_mp3["postprocessors"][0]
    assert pp["key"] == "FFmpegExtractAudio"
    assert pp["preferredcodec"] == "mp3"
    assert pp["preferredquality"] == "192"


def test_ffmpeg_missing_behavior():
    """9. Comportamiento cuando FFmpeg no está disponible."""
    service = DownloadService()

    with patch("app.downloader.check_ffmpeg", return_value=False):
        service._run_download(
            url="https://youtube.com/watch?v=123",
            format_type="mp4",
            quality="best",
        )
        status = service.get_status()
        assert status["status"] == "error"
        assert "FFmpeg no está instalado" in status["error"]


def test_ytdlp_mocked_execution_success():
    """10a. Ejecución de descarga mockeada exitosa."""
    service = DownloadService()

    mock_ydl_instance = MagicMock()
    mock_ydl_instance.extract_info.return_value = {
        "title": "Prueba de Video",
        "ext": "mp4",
    }
    mock_ydl_instance.prepare_filename.return_value = "/tmp/downloads/Prueba de Video.mp4"

    with patch("app.downloader.check_ffmpeg", return_value=True), \
         patch("yt_dlp.YoutubeDL") as mock_ydl_cls:
        mock_ydl_cls.return_value.__enter__.return_value = mock_ydl_instance

        service._run_download(
            url="https://youtube.com/watch?v=123",
            format_type="mp4",
            quality="1080p",
        )

        status = service.get_status()
        assert status["status"] == "finished"
        assert status["percent"] == 100.0
        assert status["filename"] == "Prueba de Video.mp4"
        assert status["error"] is None


def test_ytdlp_mocked_execution_download_error():
    """10b. Manejo de DownloadError de yt-dlp."""
    service = DownloadService()

    mock_ydl_instance = MagicMock()
    mock_ydl_instance.extract_info.side_effect = yt_dlp.utils.DownloadError(
        "ERROR: [youtube] 123: Video unavailable"
    )

    with patch("app.downloader.check_ffmpeg", return_value=True), \
         patch("yt_dlp.YoutubeDL") as mock_ydl_cls:
        mock_ydl_cls.return_value.__enter__.return_value = mock_ydl_instance

        service._run_download(
            url="https://youtube.com/watch?v=123",
            format_type="mp4",
            quality="1080p",
        )

        status = service.get_status()
        assert status["status"] == "error"
        assert "[youtube] 123: Video unavailable" in status["error"]

import os
import shutil
import threading
from typing import Any, Dict, Optional
import yt_dlp

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")


def check_ffmpeg() -> bool:
    """Verifica si FFmpeg está instalado y disponible en el PATH del sistema."""
    return shutil.which("ffmpeg") is not None


class DownloadService:
    def __init__(self, downloads_dir: str = DOWNLOADS_DIR):
        self.downloads_dir = downloads_dir
        self._lock = threading.Lock()
        self._state: Dict[str, Any] = {
            "status": "idle",
            "percent": 0.0,
            "filename": None,
            "error": None,
        }
        os.makedirs(self.downloads_dir, exist_ok=True)

    def get_status(self) -> Dict[str, Any]:
        """Devuelve una copia segura del estado actual."""
        with self._lock:
            return dict(self._state)

    def is_active(self) -> bool:
        """Indica si existe una descarga en curso."""
        with self._lock:
            return self._state["status"] == "downloading"

    def start_download(self, url: str, format_type: str, quality: str = "best") -> bool:
        """
        Inicia la descarga en un hilo secundario si no hay ninguna activa.
        Retorna True si se inició la descarga, False si ya había una activa.
        """
        with self._lock:
            if self._state["status"] == "downloading":
                return False

            self._state = {
                "status": "downloading",
                "percent": 0.0,
                "filename": None,
                "error": None,
            }

        thread = threading.Thread(
            target=self._run_download,
            args=(url, format_type, quality),
            daemon=True,
        )
        thread.start()
        return True

    def _get_ydl_opts(self, format_type: str, quality: str) -> Dict[str, Any]:
        """Construye las opciones de configuración para yt-dlp."""
        outtmpl = os.path.join(self.downloads_dir, "%(title)s.%(ext)s")

        opts: Dict[str, Any] = {
            "outtmpl": outtmpl,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [self._progress_hook],
        }

        if format_type.lower() == "mp3":
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ]
        else:
            # Formato MP4 con selección de resolución y fallback automático hacia abajo
            if quality == "best":
                opts["format"] = (
                    "bestvideo[ext=mp4]+bestaudio[ext=m4a]/"
                    "bestvideo+bestaudio/best"
                )
            else:
                height = quality.lower().replace("p", "")
                opts["format"] = (
                    f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/"
                    f"bestvideo[height<={height}]+bestaudio/"
                    f"best[height<={height}]/best"
                )
            opts["merge_output_format"] = "mp4"

        return opts

    def _progress_hook(self, d: Dict[str, Any]) -> None:
        """Callback invocado periódicamente por yt-dlp."""
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            if total > 0:
                percent = round((downloaded / total) * 100, 1)
                with self._lock:
                    if self._state["status"] == "downloading":
                        # Limitar a 99.9% hasta que finalice el postprocesado
                        self._state["percent"] = min(percent, 99.9)
        elif status == "finished":
            with self._lock:
                if self._state["status"] == "downloading":
                    self._state["percent"] = 100.0

    def _run_download(self, url: str, format_type: str, quality: str) -> None:
        """Ejecución de la descarga en el hilo de trabajo."""
        # Verificar disponibilidad de FFmpeg
        if not check_ffmpeg():
            with self._lock:
                self._state["status"] = "error"
                self._state["error"] = (
                    "FFmpeg no está instalado en el sistema. "
                    "Es necesario para procesar y empaquetar el archivo."
                )
            return

        try:
            ydl_opts = self._get_ydl_opts(format_type, quality)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=True)

                # Determinar el nombre final del archivo generado
                final_filename: Optional[str] = None
                if info_dict:
                    base_path = ydl.prepare_filename(info_dict)
                    if format_type.lower() == "mp3":
                        final_path = os.path.splitext(base_path)[0] + ".mp3"
                    else:
                        final_path = os.path.splitext(base_path)[0] + ".mp4"
                    final_filename = os.path.basename(final_path)

                with self._lock:
                    self._state["status"] = "finished"
                    self._state["percent"] = 100.0
                    self._state["filename"] = final_filename

        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            if error_msg.startswith("ERROR: "):
                error_msg = error_msg[7:]
            with self._lock:
                self._state["status"] = "error"
                self._state["error"] = error_msg

        except Exception as e:
            with self._lock:
                self._state["status"] = "error"
                self._state["error"] = f"Error inesperado: {str(e)}"


# Instancia única para el backend local
download_service = DownloadService()

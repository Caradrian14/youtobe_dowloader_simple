#!/usr/bin/env bash
set -e

# Obtener el directorio raíz del proyecto independientemente de desde dónde se ejecute
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Verificar si existe el entorno virtual; si no, crearlo e instalar dependencias
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    echo "Entorno virtual no detectado en $PROJECT_DIR/.venv."
    echo "Creando entorno virtual..."
    python3 -m venv "$PROJECT_DIR/.venv"
    echo "Instalando dependencias..."
    "$PROJECT_DIR/.venv/bin/pip" install --upgrade pip
    "$PROJECT_DIR/.venv/bin/pip" install -r "$PROJECT_DIR/requirements.txt"
fi

# Advertir si FFmpeg no está instalado
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  ADVERTENCIA: 'ffmpeg' no está instalado en el sistema."
    echo "   Es necesario para la conversión a MP3 y el empaquetado de vídeo en alta calidad."
    echo "   Puedes instalarlo con: sudo apt install -y ffmpeg"
    echo ""
fi

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

echo "=========================================="
echo "  YouTube Downloader Local"
echo "=========================================="
echo "Servidor disponible en: http://${HOST}:${PORT}"
echo "Presiona Ctrl+C para detenerlo."
echo "=========================================="

exec "$PROJECT_DIR/.venv/bin/python" -m uvicorn app.main:app --host "$HOST" --port "$PORT" "$@"

# YouTube Downloader (MVP Local)

YouTube Downloader es una aplicación web local ligera y sencilla diseñada para Linux que permite descargar vídeos de YouTube en formato MP4 (vídeo + audio) o extraer su pista de audio en formato MP3.

La aplicación opera exclusivamente en tu máquina local (`127.0.0.1`), sin necesidad de bases de datos, cuentas de usuario ni servicios externos complejos.

---

## Requisitos del sistema

Antes de comenzar, asegúrate de contar con las siguientes herramientas instaladas en tu sistema Linux:

1. **Python 3.10 o superior** (incluyendo el módulo `venv`).
2. **FFmpeg**: Necesario para el empaquetado (*muxing*) de flujos de audio y vídeo de alta definición y para la transcodificación de audio a MP3.

En distribuciones basadas en Debian o Ubuntu puedes instalar FFmpeg ejecutando:

```bash
sudo apt update && sudo apt install -y ffmpeg python3-venv
```

---

## Instalación

Sigue estos pasos para clonar y preparar el entorno de la aplicación:

### 1. Crear el entorno virtual

Desde la carpeta raíz del proyecto, crea un entorno virtual de Python:

```bash
python3 -m venv .venv
```

### 2. Activar el entorno virtual

Activa el entorno antes de instalar paquetes o ejecutar el servidor:

```bash
source .venv/bin/activate
```

### 3. Instalar dependencias

Instala los paquetes de Python requeridos utilizando `pip`:

```bash
pip install -r requirements.txt
```

---

## Ejecución

Para iniciar el servidor web local con Uvicorn, ejecuta el siguiente comando con el entorno virtual activo:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

El servidor quedará vinculado de forma segura únicamente a la interfaz local (`127.0.0.1`).

---

## Acceso desde el navegador

Una vez iniciado el servidor, abre tu navegador web e ingresa a:

```text
http://127.0.0.1:8000
```

Desde la interfaz podrás:

1. Pegar la URL del vídeo de YouTube.
2. Elegir entre el formato **MP4** o **MP3**.
3. Si seleccionas **MP4**, elegir la resolución máxima deseada (**Mejor disponible**, **1080p**, **720p**, **480p**). Si la resolución elegida no está disponible en el vídeo, se descargará automáticamente la mejor resolución inferior disponible.
4. Pulsar el botón **Descargar** para seguir el porcentaje de avance en tiempo real.

---

## Ubicación de los archivos descargados

Todos los archivos completados se guardan automáticamente en la carpeta local:

```text
./downloads/
```

El nombre del archivo corresponde al título original del vídeo saneado por el motor de descarga.

---

## Limitaciones conocidas del MVP

Este proyecto es un prototipo inicial y deliberadamente no incluye:

* **Descargas múltiples concurrentes:** Sólo se admite una descarga activa a la vez; cualquier intento adicional mientras una descarga está en progreso es rechazado con código HTTP 409.
* **Cola de descargas:** No existe encolado en segundo plano ni almacenamiento persistente de peticiones.
* **Listas de reproducción (*playlists*):** Solo se procesan vídeos individuales (`noplaylist = True`).
* **Cancelación activa:** Una vez iniciada una descarga, debe finalizar o fallar por error de red/servidor.
* **Selección de ruta personalizada:** El destino está fijado estrictamente en `./downloads/` por motivos de seguridad y simplicidad.

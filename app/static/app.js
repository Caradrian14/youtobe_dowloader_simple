document.addEventListener("DOMContentLoaded", () => {
  const downloadForm = document.getElementById("downloadForm");
  const urlInput = document.getElementById("urlInput");
  const formatRadios = document.querySelectorAll('input[name="format"]');
  const qualityGroup = document.getElementById("qualityGroup");
  const qualitySelect = document.getElementById("qualitySelect");
  const submitBtn = document.getElementById("submitBtn");

  const statusText = document.getElementById("statusText");
  const progressBar = document.getElementById("progressBar");
  const percentText = document.getElementById("percentText");
  const resultBox = document.getElementById("resultBox");
  const filenameText = document.getElementById("filenameText");
  const errorBox = document.getElementById("errorBox");
  const errorText = document.getElementById("errorText");

  let pollInterval = null;

  // Manejar cambio de formato (MP4 vs MP3)
  function handleFormatChange() {
    const selectedFormat = document.querySelector('input[name="format"]:checked').value;
    if (selectedFormat === "mp3") {
      qualityGroup.classList.add("hidden");
      qualitySelect.disabled = true;
    } else {
      qualityGroup.classList.remove("hidden");
      qualitySelect.disabled = false;
    }
  }

  formatRadios.forEach((radio) => {
    radio.addEventListener("change", handleFormatChange);
  });

  // Habilitar / deshabilitar controles del formulario
  function setFormDisabled(disabled) {
    urlInput.disabled = disabled;
    formatRadios.forEach((radio) => (radio.disabled = disabled));
    if (!qualityGroup.classList.contains("hidden")) {
      qualitySelect.disabled = disabled;
    }
    submitBtn.disabled = disabled;
    submitBtn.textContent = disabled ? "Descargando..." : "Descargar";
  }

  // Actualizar indicadores visuales de estado
  function updateUIState(state) {
    statusText.className = "status-badge";
    const status = state.status || "idle";

    switch (status) {
      case "downloading":
        statusText.classList.add("status-downloading");
        statusText.textContent = "Descargando...";
        break;
      case "finished":
        statusText.classList.add("status-finished");
        statusText.textContent = "Completado";
        break;
      case "error":
        statusText.classList.add("status-error");
        statusText.textContent = "Error";
        break;
      case "idle":
      default:
        statusText.classList.add("status-idle");
        statusText.textContent = "En espera";
        break;
    }

    const pct = typeof state.percent === "number" ? state.percent : 0;
    progressBar.style.width = `${pct}%`;
    percentText.textContent = `${pct.toFixed(1)}%`;

    if (status === "finished") {
      resultBox.classList.remove("hidden");
      filenameText.textContent = state.filename || "Archivo guardado";
      errorBox.classList.add("hidden");
    } else if (status === "error") {
      errorBox.classList.remove("hidden");
      errorText.textContent = state.error || "Ocurrió un error inesperado";
      resultBox.classList.add("hidden");
    } else if (status === "downloading") {
      resultBox.classList.add("hidden");
      errorBox.classList.add("hidden");
    }
  }

  // Sondeo de estado periódicamente
  async function pollStatus() {
    try {
      const res = await fetch("/api/status");
      if (!res.ok) {
        throw new Error(`Error en el servidor: HTTP ${res.status}`);
      }
      const data = await res.json();
      updateUIState(data);

      if (data.status === "finished" || data.status === "error") {
        clearInterval(pollInterval);
        pollInterval = null;
        setFormDisabled(false);
      }
    } catch (err) {
      clearInterval(pollInterval);
      pollInterval = null;
      setFormDisabled(false);
      updateUIState({
        status: "error",
        percent: 0,
        error: `No se pudo consultar el estado: ${err.message}`,
      });
    }
  }

  function startPolling() {
    if (pollInterval) clearInterval(pollInterval);
    pollInterval = setInterval(pollStatus, 1000);
  }

  // Envío del formulario
  downloadForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const url = urlInput.value.trim();
    if (!url) return;

    const format = document.querySelector('input[name="format"]:checked').value;
    const quality = qualitySelect.value;

    setFormDisabled(true);
    resultBox.classList.add("hidden");
    errorBox.classList.add("hidden");
    updateUIState({ status: "downloading", percent: 0 });

    try {
      const res = await fetch("/api/download", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          url: url,
          format: format,
          quality: quality,
        }),
      });

      if (res.status === 202) {
        startPolling();
      } else {
        const errorData = await res.json().catch(() => ({}));
        const message = errorData.detail || `Error inesperado (HTTP ${res.status})`;
        setFormDisabled(false);
        updateUIState({
          status: "error",
          percent: 0,
          error: message,
        });
      }
    } catch (err) {
      setFormDisabled(false);
      updateUIState({
        status: "error",
        percent: 0,
        error: `Error al conectar con el servidor: ${err.message}`,
      });
    }
  });

  // Comprobar estado inicial por si ya existía una descarga en curso
  fetch("/api/status")
    .then((r) => r.json())
    .then((state) => {
      if (state.status === "downloading") {
        setFormDisabled(true);
        updateUIState(state);
        startPolling();
      } else {
        updateUIState(state);
      }
    })
    .catch(() => {
      // Si falla la primera carga, se mantiene en idle
      updateUIState({ status: "idle", percent: 0 });
    });
});

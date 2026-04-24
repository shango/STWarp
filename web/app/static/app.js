(() => {
  const form = document.getElementById("export-form");
  const shotInput = document.getElementById("shot_name");
  const btn = document.getElementById("export-btn");
  const status = document.getElementById("status");
  const progress = document.getElementById("progress");
  const progressFill = document.getElementById("progress-fill");
  const progressLabel = document.getElementById("progress-label");

  const drops = Array.from(document.querySelectorAll(".drop"));

  const state = {
    shotOk: false,
    files: { undistort: null, distort: null },
  };

  const SHOT_RE = /^[A-Za-z0-9][A-Za-z0-9_.\-]*$/;

  function setStatus(text, kind) {
    status.textContent = text || "";
    status.classList.remove("error", "success");
    if (kind) status.classList.add(kind);
  }

  function clearTransientStatus() {
    if (status.classList.contains("error") || status.classList.contains("success")) {
      setStatus("");
    }
  }

  function refresh() {
    btn.disabled = !(state.shotOk && state.files.undistort && state.files.distort);

    // Don't clobber an active error or success message from the last upload;
    // it gets cleared the moment the user changes any input.
    if (status.classList.contains("error") || status.classList.contains("success")) {
      return;
    }

    const missing = [];
    if (!state.shotOk) missing.push("a shot name");
    if (!state.files.undistort) missing.push("the undistort STMap");
    if (!state.files.distort) missing.push("the distort STMap");
    setStatus(missing.length ? `Add ${missing.join(" and ")} to continue.` : "");
  }

  shotInput.addEventListener("input", () => {
    state.shotOk = SHOT_RE.test(shotInput.value.trim());
    clearTransientStatus();
    refresh();
  });

  function attachDrop(el) {
    const slot = el.dataset.slot;
    const input = el.querySelector('input[type="file"]');
    const filenameEl = el.querySelector(".drop-filename");
    const emptyText = filenameEl.dataset.empty;

    const onFile = (file) => {
      if (!file) return;
      if (!file.name.toLowerCase().endsWith(".exr")) {
        setStatus(`${slot}: must be a .exr file`, "error");
        return;
      }
      state.files[slot] = file;
      filenameEl.textContent = `${file.name} (${formatBytes(file.size)})`;
      el.classList.add("filled");
      setStatus("");
      refresh();
    };

    el.addEventListener("click", () => input.click());
    el.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        input.click();
      }
    });
    el.tabIndex = 0;

    input.addEventListener("change", () => onFile(input.files[0]));

    ["dragenter", "dragover"].forEach((ev) =>
      el.addEventListener(ev, (e) => {
        e.preventDefault();
        el.classList.add("dragover");
      }),
    );
    ["dragleave", "drop"].forEach((ev) =>
      el.addEventListener(ev, (e) => {
        e.preventDefault();
        el.classList.remove("dragover");
      }),
    );
    el.addEventListener("drop", (e) => {
      const file = e.dataTransfer && e.dataTransfer.files[0];
      if (file) {
        // Sync the actual <input> so required/validation behaves.
        const dt = new DataTransfer();
        dt.items.add(file);
        input.files = dt.files;
        onFile(file);
      }
    });
  }

  drops.forEach(attachDrop);

  function resetForm() {
    shotInput.value = "";
    state.shotOk = false;
    state.files.undistort = null;
    state.files.distort = null;
    drops.forEach((el) => {
      el.classList.remove("filled");
      const input = el.querySelector('input[type="file"]');
      input.value = "";
      const filenameEl = el.querySelector(".drop-filename");
      filenameEl.textContent = filenameEl.dataset.empty;
    });
    progress.hidden = true;
    progressFill.style.width = "0%";
  }

  // Show the initial "what's missing" hint on load.
  refresh();

  function formatBytes(n) {
    if (n < 1024) return `${n} B`;
    if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
    return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (btn.disabled) return;

    const data = new FormData();
    data.append("shot_name", shotInput.value.trim());
    data.append("undistort", state.files.undistort);
    data.append("distort", state.files.distort);

    btn.disabled = true;
    setStatus("");
    progress.hidden = false;
    progressFill.style.width = "0%";
    progressLabel.textContent = "Uploading…";

    try {
      const blob = await uploadWithProgress(data);
      const zipName = `${shotInput.value.trim()}_AE_mesh_warp_presets.zip`;
      triggerDownload(blob, zipName);
      setStatus(`Downloaded ${zipName}. Ready for the next shot.`, "success");
      resetForm();
    } catch (err) {
      setStatus(err.message || "Export failed.", "error");
      progress.hidden = true;
    } finally {
      refresh();
    }
  });

  function uploadWithProgress(formData) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", "/export");
      xhr.responseType = "blob";

      xhr.upload.addEventListener("progress", (e) => {
        if (!e.lengthComputable) return;
        const pct = Math.min(99, Math.round((e.loaded / e.total) * 100));
        progressFill.style.width = `${pct}%`;
        progressLabel.textContent =
          pct >= 99 ? "Processing…" : `Uploading… ${pct}%`;
      });

      xhr.addEventListener("load", async () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(xhr.response);
          return;
        }
        // Try to extract error detail from JSON body.
        let msg = `Server returned ${xhr.status}`;
        try {
          const text = await xhr.response.text();
          const parsed = JSON.parse(text);
          if (parsed && parsed.detail) msg = parsed.detail;
        } catch (_) { /* ignore */ }
        reject(new Error(msg));
      });

      xhr.addEventListener("error", () => reject(new Error("Network error.")));
      xhr.addEventListener("abort", () => reject(new Error("Upload aborted.")));

      xhr.send(formData);
    });
  }

  function triggerDownload(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
})();

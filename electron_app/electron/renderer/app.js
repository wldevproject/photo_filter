const CATEGORY_NAMES = ["Bagus", "Lumayan", "Jelek"];
const RAW_EXTENSIONS = new Set([
  ".nef",
  ".cr2",
  ".cr3",
  ".arw",
  ".dng",
  ".rw2",
  ".orf",
  ".raf",
  ".pef",
  ".srw",
  ".3fr",
  ".fff",
  ".iiq",
  ".raw",
  ".erf",
  ".kdc",
  ".mef",
  ".mos",
  ".mrw",
  ".nrw",
  ".rwl",
  ".x3f",
  ".dcr",
  ".cap",
  ".bay",
  ".gpr"
]);

const state = {
  sourceFolder: null,
  queue: [],
  index: 0,
  counts: {
    Bagus: 0,
    Lumayan: 0,
    Jelek: 0
  },
  history: [],
  theme: localStorage.getItem("photoSorterTheme") || "light"
};

const refs = {
  openFolderBtn: document.getElementById("open-folder-btn"),
  themeBtn: document.getElementById("theme-btn"),
  folderLabel: document.getElementById("folder-label"),
  progressFill: document.getElementById("progress-fill"),
  progressLabel: document.getElementById("progress-label"),
  remainingChip: document.getElementById("remaining-chip"),
  fileName: document.getElementById("file-name"),
  statusLine: document.getElementById("status-line"),
  previewImage: document.getElementById("preview-image"),
  previewPlaceholder: document.getElementById("preview-placeholder"),
  countBagus: document.getElementById("count-bagus"),
  countLumayan: document.getElementById("count-lumayan"),
  countJelek: document.getElementById("count-jelek"),
  skipBtn: document.getElementById("skip-btn"),
  prevBtn: document.getElementById("prev-btn"),
  undoBtn: document.getElementById("undo-btn"),
  quitBtn: document.getElementById("quit-btn"),
  categoryButtons: document.querySelectorAll(".btn-category")
};

let previewRenderToken = 0;

function fileNameFromPath(filePath) {
  const normalized = (filePath || "").replaceAll("\\", "/");
  const parts = normalized.split("/");
  return parts[parts.length - 1] || filePath;
}

function fileExt(filePath) {
  const name = fileNameFromPath(filePath);
  const dotIndex = name.lastIndexOf(".");
  if (dotIndex < 0) {
    return "";
  }
  return name.slice(dotIndex).toLowerCase();
}

function themeLabel(theme) {
  return theme === "dark" ? "Light Mode" : "Dark Mode";
}

async function applyTheme(themeName) {
  state.theme = themeName === "dark" ? "dark" : "light";
  document.documentElement.dataset.theme = state.theme;
  refs.themeBtn.textContent = themeLabel(state.theme);
  localStorage.setItem("photoSorterTheme", state.theme);
  await window.photoSorter.setTheme(state.theme);
}

function renderDashboard() {
  const processed = state.counts.Bagus + state.counts.Lumayan + state.counts.Jelek;
  const remaining = state.queue.length;
  const total = processed + remaining;
  const ratio = total > 0 ? processed / total : 0;

  refs.progressFill.style.width = `${Math.round(ratio * 100)}%`;
  refs.progressLabel.textContent = `${processed}/${total} selesai`;
  refs.remainingChip.textContent = `Tersisa ${remaining} foto`;
  refs.countBagus.textContent = String(state.counts.Bagus);
  refs.countLumayan.textContent = String(state.counts.Lumayan);
  refs.countJelek.textContent = String(state.counts.Jelek);
}

function showPlaceholder(message) {
  refs.previewImage.style.display = "none";
  refs.previewImage.removeAttribute("src");
  refs.previewPlaceholder.style.display = "block";
  refs.previewPlaceholder.textContent = message;
}

async function renderPreview(filePath) {
  const extension = fileExt(filePath);
  const token = ++previewRenderToken;
  try {
    const result = await window.photoSorter.getPreviewUrl(filePath);
    if (token !== previewRenderToken) {
      return;
    }

    if (!result || !result.url) {
      if (RAW_EXTENSIONS.has(extension) && result?.kind === "raw-missing-decoder") {
        showPlaceholder(
          "Preview RAW butuh exiftool (bundled/terpasang). Tambahkan binary exiftool agar thumbnail DNG/NEF bisa tampil, sorting 1/2/3 tetap jalan."
        );
        return;
      }

      showPlaceholder(
        "Preview belum tersedia untuk format ini di Electron, tapi file tetap bisa disortir dengan tombol 1/2/3."
      );
      return;
    }

    refs.previewImage.src = result.url;
    refs.previewImage.style.display = "block";
    refs.previewPlaceholder.style.display = "none";
  } catch {
    showPlaceholder("Preview gagal dimuat, tapi file tetap bisa disortir.");
  }
}

async function renderCurrent() {
  renderDashboard();

  if (!state.sourceFolder) {
    refs.folderLabel.textContent = "Folder aktif: belum dipilih";
    refs.fileName.textContent = "Belum ada folder dipilih";
    refs.statusLine.textContent = "Klik Open Folder untuk mulai.";
    showPlaceholder("Aplikasi siap. Klik Open Folder untuk pilih folder foto.");
    return;
  }

  refs.folderLabel.textContent = `Folder aktif: ${state.sourceFolder}`;

  if (state.queue.length === 0) {
    refs.fileName.textContent = "Semua foto selesai diproses";
    refs.statusLine.textContent =
      "Tidak ada foto tersisa di root folder. Counter tetap mengikuti isi folder kategori.";
    showPlaceholder("Sorting selesai. Tambahkan foto baru atau pilih folder lain.");
    return;
  }

  state.index = Math.max(0, Math.min(state.index, state.queue.length - 1));
  const currentPath = state.queue[state.index];
  const ext = fileExt(currentPath);

  refs.fileName.textContent = fileNameFromPath(currentPath);
  refs.statusLine.textContent = `Foto ${state.index + 1}/${state.queue.length} di antrian | Format: ${ext || "-"}`;
  await renderPreview(currentPath);
}

async function loadFolder(folderPath) {
  const result = await window.photoSorter.scanFolder(folderPath);
  state.sourceFolder = result.sourceFolder;
  state.queue = result.queue;
  state.counts = result.counts;
  state.history = [];
  state.index = 0;
  await renderCurrent();
}

async function openFolderFlow() {
  try {
    const selected = await window.photoSorter.pickFolder();
    if (!selected) {
      return;
    }
    await loadFolder(selected);
  } catch (error) {
    showPlaceholder(`Gagal membuka folder.\n${error.message || error}`);
  }
}

async function moveCurrent(category) {
  if (!state.sourceFolder || state.queue.length === 0) {
    return;
  }

  const sourcePath = state.queue[state.index];
  try {
    const result = await window.photoSorter.moveToCategory({
      sourcePath,
      sourceFolder: state.sourceFolder,
      category
    });

    state.history.push({
      movedPath: result.movedPath,
      restorePath: sourcePath,
      category,
      insertIndex: state.index
    });

    state.counts[category] += 1;
    state.queue.splice(state.index, 1);

    if (state.index >= state.queue.length) {
      state.index = 0;
    }
    await renderCurrent();
  } catch (error) {
    showPlaceholder(`Gagal memindahkan file.\n${error.message || error}`);
  }
}

async function undoMove() {
  if (!state.sourceFolder || state.history.length === 0) {
    return;
  }

  const lastMove = state.history.pop();
  try {
    const result = await window.photoSorter.undoMove({
      movedPath: lastMove.movedPath,
      restorePath: lastMove.restorePath,
      sourceFolder: state.sourceFolder
    });

    state.counts[lastMove.category] = Math.max(0, state.counts[lastMove.category] - 1);

    const insertAt = Math.min(lastMove.insertIndex, state.queue.length);
    state.queue.splice(insertAt, 0, result.restoredPath);
    state.index = insertAt;
    await renderCurrent();
  } catch (error) {
    showPlaceholder(`Gagal undo.\n${error.message || error}`);
  }
}

async function nextImage() {
  if (state.queue.length === 0) {
    return;
  }
  state.index = (state.index + 1) % state.queue.length;
  await renderCurrent();
}

async function prevImage() {
  if (state.queue.length === 0) {
    return;
  }
  state.index = (state.index - 1 + state.queue.length) % state.queue.length;
  await renderCurrent();
}

function bindEvents() {
  refs.openFolderBtn.addEventListener("click", openFolderFlow);
  refs.themeBtn.addEventListener("click", async () => {
    await applyTheme(state.theme === "light" ? "dark" : "light");
  });

  refs.categoryButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const category = button.dataset.category;
      moveCurrent(category);
    });
  });

  refs.skipBtn.addEventListener("click", nextImage);
  refs.prevBtn.addEventListener("click", prevImage);
  refs.undoBtn.addEventListener("click", undoMove);
  refs.quitBtn.addEventListener("click", () => window.photoSorter.closeWindow());

  document.addEventListener("keydown", async (event) => {
    if (event.repeat) {
      return;
    }

    if (event.key === "1") {
      await moveCurrent("Bagus");
    } else if (event.key === "2") {
      await moveCurrent("Lumayan");
    } else if (event.key === "3") {
      await moveCurrent("Jelek");
    } else if (event.key === "0" || event.key === "ArrowRight") {
      await nextImage();
    } else if (event.key === "ArrowLeft") {
      await prevImage();
    } else if (event.key.toLowerCase() === "u") {
      await undoMove();
    } else if (event.key.toLowerCase() === "q" || event.key === "Escape") {
      await window.photoSorter.closeWindow();
    }
  });
}

async function bootstrap() {
  await applyTheme(state.theme);
  bindEvents();
  await renderCurrent();

  const initialFolder = await window.photoSorter.getInitialFolder();
  if (initialFolder) {
    await loadFolder(initialFolder);
  }
}

bootstrap();

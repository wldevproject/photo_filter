const path = require("node:path");
const fs = require("node:fs/promises");
const { existsSync } = require("node:fs");
const crypto = require("node:crypto");
const { execFile } = require("node:child_process");
const { promisify } = require("node:util");
const { pathToFileURL } = require("node:url");
const { app, BrowserWindow, dialog, ipcMain, nativeTheme } = require("electron");

const CATEGORY_NAMES = ["Bagus", "Lumayan", "Jelek"];
const execFileAsync = promisify(execFile);
const PREVIEWABLE_EXTENSIONS = new Set([
  ".jpg",
  ".jpeg",
  ".png",
  ".webp",
  ".bmp",
  ".gif"
]);
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
const SUPPORTED_EXTENSIONS = new Set([
  ".jpg",
  ".jpeg",
  ".png",
  ".webp",
  ".bmp",
  ".tif",
  ".tiff",
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
const RAW_PREVIEW_TAGS = ["PreviewImage", "JpgFromRaw", "ThumbnailImage", "OtherImage", "PreviewTIFF"];
const NEGATIVE_EXIFTOOL_CACHE_MS = 15000;
const EXIFTOOL_BIN_CANDIDATES =
  process.platform === "win32" ? ["exiftool.exe", "exiftool", "exiftool(-k).exe"] : ["exiftool"];
const RAW_PREVIEW_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff"];
const BUNDLED_EXIFTOOL_RELATIVE_CANDIDATES_BY_PLATFORM = {
  win32: ["win32/exiftool.exe", "win32/exiftool(-k).exe", "windows/exiftool.exe", "windows/exiftool(-k).exe"],
  darwin: ["darwin/exiftool", "macos/exiftool", "mac/exiftool"],
  linux: ["linux/exiftool", "linux/exiftool.pl"]
};

let mainWindow = null;
let exiftoolBinary = null;
let exiftoolLastCheckTs = 0;
const cliFolder = getCliFolder();
const previewTaskByKey = new Map();

function getCliFolder() {
  const candidate = process.argv.find((arg) => arg && !arg.startsWith("-"));
  if (!candidate) {
    return null;
  }
  const resolved = path.resolve(candidate);
  return resolved;
}

function createWindow() {
  const iconPath = path.join(__dirname, "..", "assets", "app_icon.ico");
  const win = new BrowserWindow({
    width: 1380,
    height: 880,
    minWidth: 1024,
    minHeight: 700,
    show: false,
    backgroundColor: "#e9eef6",
    icon: existsSync(iconPath) ? iconPath : undefined,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false
    }
  });

  win.loadFile(path.join(__dirname, "renderer", "index.html"));
  win.once("ready-to-show", () => win.show());
  return win;
}

function extname(filePath) {
  return path.extname(filePath).toLowerCase();
}

function isSupportedFile(fileName) {
  return SUPPORTED_EXTENSIONS.has(extname(fileName));
}

function isRawFile(filePath) {
  return RAW_EXTENSIONS.has(extname(filePath));
}

function getPreviewCacheDir() {
  return path.join(app.getPath("temp"), "photo-sorter-preview-cache");
}

function buildRawCacheKey(filePath, stat) {
  const fingerprint = `${path.resolve(filePath)}|${stat.size}|${stat.mtimeMs}`;
  return crypto.createHash("sha1").update(fingerprint).digest("hex");
}

function detectImageExtension(buffer) {
  if (!Buffer.isBuffer(buffer) || buffer.length < 4) {
    return null;
  }

  if (buffer[0] === 0xff && buffer[1] === 0xd8) {
    return ".jpg";
  }
  if (
    buffer.length >= 8 &&
    buffer[0] === 0x89 &&
    buffer[1] === 0x50 &&
    buffer[2] === 0x4e &&
    buffer[3] === 0x47 &&
    buffer[4] === 0x0d &&
    buffer[5] === 0x0a &&
    buffer[6] === 0x1a &&
    buffer[7] === 0x0a
  ) {
    return ".png";
  }
  if (buffer.length >= 6) {
    const gifHeader = buffer.toString("ascii", 0, 6);
    if (gifHeader === "GIF87a" || gifHeader === "GIF89a") {
      return ".gif";
    }
  }
  if (buffer[0] === 0x42 && buffer[1] === 0x4d) {
    return ".bmp";
  }
  if (
    buffer.length >= 12 &&
    buffer.toString("ascii", 0, 4) === "RIFF" &&
    buffer.toString("ascii", 8, 12) === "WEBP"
  ) {
    return ".webp";
  }
  if (
    (buffer[0] === 0x49 && buffer[1] === 0x49 && buffer[2] === 0x2a && buffer[3] === 0x00) ||
    (buffer[0] === 0x4d && buffer[1] === 0x4d && buffer[2] === 0x00 && buffer[3] === 0x2a)
  ) {
    return ".tif";
  }

  return null;
}

function getBundledToolsRoots() {
  return Array.from(
    new Set([
      path.resolve(__dirname, "..", "assets", "tools"),
      path.join(process.resourcesPath, "tools"),
      path.join(process.resourcesPath, "assets", "tools")
    ])
  );
}

function getBundledExiftoolCandidates() {
  const relCandidates = BUNDLED_EXIFTOOL_RELATIVE_CANDIDATES_BY_PLATFORM[process.platform] || [];
  const candidates = [];
  for (const root of getBundledToolsRoots()) {
    for (const rel of relCandidates) {
      candidates.push(path.join(root, rel));
    }
  }
  return candidates;
}

async function ensureBinaryExecutable(binaryPath) {
  if (process.platform === "win32" || !path.isAbsolute(binaryPath)) {
    return;
  }
  try {
    await fs.chmod(binaryPath, 0o755);
  } catch {
    // chmod may fail in some read-only environments; probing still continues.
  }
}

function getExiftoolCandidates() {
  const candidates = [];
  const fromEnv = process.env.EXIFTOOL_PATH;
  if (fromEnv && fromEnv.trim()) {
    candidates.push(fromEnv.trim());
  }
  candidates.push(...getBundledExiftoolCandidates(), ...EXIFTOOL_BIN_CANDIDATES);
  return Array.from(new Set(candidates));
}

async function detectExiftool() {
  const now = Date.now();
  if (typeof exiftoolBinary === "string" && exiftoolBinary.length > 0) {
    return exiftoolBinary;
  }
  if (exiftoolBinary === false && now - exiftoolLastCheckTs < NEGATIVE_EXIFTOOL_CACHE_MS) {
    return null;
  }

  for (const bin of getExiftoolCandidates()) {
    if (path.isAbsolute(bin) && !existsSync(bin)) {
      continue;
    }

    try {
      await ensureBinaryExecutable(bin);
      await execFileAsync(bin, ["-ver"], {
        encoding: "utf8",
        windowsHide: true,
        timeout: 7000
      });
      exiftoolBinary = bin;
      exiftoolLastCheckTs = now;
      return exiftoolBinary;
    } catch {
      continue;
    }
  }

  exiftoolBinary = false;
  exiftoolLastCheckTs = now;
  return null;
}

async function extractRawPreviewData(filePath) {
  const exiftoolBin = await detectExiftool();
  if (!exiftoolBin) {
    return null;
  }

  for (const tag of RAW_PREVIEW_TAGS) {
    try {
      const { stdout } = await execFileAsync(
        exiftoolBin,
        ["-b", `-${tag}`, filePath],
        {
          encoding: "buffer",
          windowsHide: true,
          maxBuffer: 64 * 1024 * 1024
        }
      );
      const extension = detectImageExtension(stdout);
      if (extension) {
        return {
          buffer: stdout,
          extension
        };
      }
    } catch {
      continue;
    }
  }

  return null;
}

async function getCachedPreviewPath(cacheKey) {
  const cacheDir = getPreviewCacheDir();
  for (const extension of RAW_PREVIEW_EXTENSIONS) {
    const candidate = path.join(cacheDir, `${cacheKey}${extension}`);
    try {
      await fs.access(candidate);
      return candidate;
    } catch {
      continue;
    }
  }
  return null;
}

async function getRawPreviewUrl(rawPath) {
  const fileStat = await fs.stat(rawPath);
  const key = buildRawCacheKey(rawPath, fileStat);
  const existingTask = previewTaskByKey.get(key);
  if (existingTask) {
    return existingTask;
  }

  const task = (async () => {
    try {
      const cachedPath = await getCachedPreviewPath(key);
      if (cachedPath) {
        return pathToFileURL(cachedPath).href;
      }

      await fs.mkdir(getPreviewCacheDir(), { recursive: true });
      const previewData = await extractRawPreviewData(rawPath);
      if (!previewData) {
        return null;
      }

      const cachePath = path.join(getPreviewCacheDir(), `${key}${previewData.extension}`);
      await fs.writeFile(cachePath, previewData.buffer);
      return pathToFileURL(cachePath).href;
    } finally {
      previewTaskByKey.delete(key);
    }
  })();

  previewTaskByKey.set(key, task);
  return task;
}

function assertDirectory(folderPath) {
  if (!folderPath) {
    throw new Error("Folder tidak valid.");
  }
  const resolved = path.resolve(folderPath);
  return resolved;
}

function isPathInside(childPath, parentPath) {
  const relative = path.relative(parentPath, childPath);
  return relative === "" || (!relative.startsWith("..") && !path.isAbsolute(relative));
}

async function ensureCategoryDirectories(rootFolder) {
  const dirs = {};
  for (const category of CATEGORY_NAMES) {
    const dir = path.join(rootFolder, category);
    await fs.mkdir(dir, { recursive: true });
    dirs[category] = dir;
  }
  return dirs;
}

async function countCategoryFiles(categoryDir) {
  let count = 0;
  const entries = await fs.readdir(categoryDir, { withFileTypes: true });
  for (const entry of entries) {
    if (entry.isFile() && isSupportedFile(entry.name)) {
      count += 1;
    }
  }
  return count;
}

async function scanFolder(folderPath) {
  const rootFolder = assertDirectory(folderPath);
  const categoryDirs = await ensureCategoryDirectories(rootFolder);

  const entries = await fs.readdir(rootFolder, { withFileTypes: true });
  const queue = entries
    .filter((entry) => entry.isFile() && isSupportedFile(entry.name))
    .map((entry) => path.join(rootFolder, entry.name))
    .sort((a, b) => path.basename(a).localeCompare(path.basename(b), undefined, { numeric: true }));

  const counts = {};
  for (const category of CATEGORY_NAMES) {
    counts[category] = await countCategoryFiles(categoryDirs[category]);
  }

  return {
    sourceFolder: rootFolder,
    queue,
    counts
  };
}

async function resolveUniqueDestination(targetPath) {
  const parsed = path.parse(targetPath);
  let nextPath = targetPath;
  let counter = 1;

  while (true) {
    try {
      await fs.access(nextPath);
      nextPath = path.join(parsed.dir, `${parsed.name}_${counter}${parsed.ext}`);
      counter += 1;
    } catch {
      return nextPath;
    }
  }
}

async function moveFileSafe(sourcePath, destinationPath) {
  try {
    await fs.rename(sourcePath, destinationPath);
    return;
  } catch (error) {
    if (error && error.code === "EXDEV") {
      await fs.copyFile(sourcePath, destinationPath);
      await fs.unlink(sourcePath);
      return;
    }
    throw error;
  }
}

ipcMain.handle("dialog:pick-folder", async () => {
  if (!mainWindow) {
    return null;
  }

  const result = await dialog.showOpenDialog(mainWindow, {
    title: "Pilih folder foto",
    properties: ["openDirectory", "dontAddToRecent"]
  });

  if (result.canceled || result.filePaths.length === 0) {
    return null;
  }
  return result.filePaths[0];
});

ipcMain.handle("folder:get-initial", async () => {
  if (!cliFolder) {
    return null;
  }

  try {
    const stat = await fs.stat(cliFolder);
    if (stat.isDirectory()) {
      return cliFolder;
    }
  } catch {
    return null;
  }
  return null;
});

ipcMain.handle("folder:scan", async (_event, folderPath) => {
  return scanFolder(folderPath);
});

ipcMain.handle("file:move-category", async (_event, payload) => {
  const { sourcePath, sourceFolder, category } = payload || {};
  if (!CATEGORY_NAMES.includes(category)) {
    throw new Error("Kategori tidak valid.");
  }

  const rootFolder = assertDirectory(sourceFolder);
  const resolvedSource = path.resolve(sourcePath || "");
  if (!isPathInside(resolvedSource, rootFolder)) {
    throw new Error("Lokasi file di luar folder aktif.");
  }

  const categoryDirs = await ensureCategoryDirectories(rootFolder);
  const destinationBase = path.join(categoryDirs[category], path.basename(resolvedSource));
  const destinationPath = await resolveUniqueDestination(destinationBase);
  await moveFileSafe(resolvedSource, destinationPath);

  return { movedPath: destinationPath };
});

ipcMain.handle("file:undo-move", async (_event, payload) => {
  const { movedPath, restorePath, sourceFolder } = payload || {};
  const rootFolder = assertDirectory(sourceFolder);
  const resolvedMoved = path.resolve(movedPath || "");
  const resolvedRestoreBase = path.resolve(restorePath || "");

  if (!isPathInside(resolvedMoved, rootFolder)) {
    throw new Error("File undo di luar folder aktif.");
  }
  if (!isPathInside(resolvedRestoreBase, rootFolder)) {
    throw new Error("Tujuan undo di luar folder aktif.");
  }

  const restoreTarget = await resolveUniqueDestination(resolvedRestoreBase);
  await moveFileSafe(resolvedMoved, restoreTarget);
  return { restoredPath: restoreTarget };
});

ipcMain.handle("file:to-url", async (_event, filePath) => {
  return pathToFileURL(filePath).href;
});

ipcMain.handle("preview:get-url", async (_event, filePath) => {
  const resolvedPath = path.resolve(filePath || "");
  const extension = extname(resolvedPath);

  if (PREVIEWABLE_EXTENSIONS.has(extension)) {
    return {
      url: pathToFileURL(resolvedPath).href,
      kind: "direct"
    };
  }

  if (!isRawFile(resolvedPath)) {
    return {
      url: null,
      kind: "unsupported"
    };
  }

  try {
    const url = await getRawPreviewUrl(resolvedPath);
    const hasExiftool = Boolean(await detectExiftool());
    if (url) {
      return {
        url,
        kind: "raw"
      };
    }
    return {
      url: null,
      kind: hasExiftool ? "raw-no-embedded-preview" : "raw-missing-decoder"
    };
  } catch {
    return {
      url: null,
      kind: "error"
    };
  }
});

ipcMain.handle("window:close", async () => {
  if (mainWindow) {
    mainWindow.close();
  }
});

ipcMain.handle("theme:set", async (_event, themeName) => {
  if (themeName === "dark" || themeName === "light" || themeName === "system") {
    nativeTheme.themeSource = themeName;
  }
});

app.whenReady().then(() => {
  mainWindow = createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      mainWindow = createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("photoSorter", {
  pickFolder: () => ipcRenderer.invoke("dialog:pick-folder"),
  getInitialFolder: () => ipcRenderer.invoke("folder:get-initial"),
  scanFolder: (folderPath) => ipcRenderer.invoke("folder:scan", folderPath),
  moveToCategory: (payload) => ipcRenderer.invoke("file:move-category", payload),
  undoMove: (payload) => ipcRenderer.invoke("file:undo-move", payload),
  toFileUrl: (filePath) => ipcRenderer.invoke("file:to-url", filePath),
  getPreviewUrl: (filePath) => ipcRenderer.invoke("preview:get-url", filePath),
  setTheme: (themeName) => ipcRenderer.invoke("theme:set", themeName),
  closeWindow: () => ipcRenderer.invoke("window:close")
});

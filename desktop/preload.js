const { contextBridge } = require('electron')

// Expose a minimal API if you want to detect platform from the web UI
contextBridge.exposeInMainWorld('vmixDesktop', {
  platform: process.platform,
})

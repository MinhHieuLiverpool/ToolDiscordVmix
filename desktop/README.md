# vmixmonitor Desktop Wrapper

Minimal Electron app that opens the production web UI at `https://vmixmonitor.vercel.app/`.

Quick start

1. Open PowerShell or CMD in the `desktop` folder.
2. Run:

```powershell
npm install
npm run start
```

Notes
- The app is intentionally minimal: it loads the remote URL in a frameless window.

Packaging (Windows example)

1. Put your icon file at `desktop/assets/icon.ico` (ICO format, 256x256 recommended). For macOS use `assets/icon.icns`.
2. From the `desktop` folder run:

```powershell
npm install
npm run dist:win
```

3. The installer and artifacts will be created in `desktop/dist`.

If you want a signed installer or cross-platform packages, configure `electron-builder` accordingly.

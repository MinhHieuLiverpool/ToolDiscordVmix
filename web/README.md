# Vmix Monitor Web - Full Project Structure and Detailed Logic

Tai lieu nay phan tich toan bo cau truc va logic cua project web theo yeu cau: chi tiet nhat co the, tap trung vao cong nghe, logic giai thuat, tat ca chuc nang tren left sidebar, va 2 chuc nang quan trong ViewSync + Speedtest. Cuoi cung co phan so sanh voi JS/HTML thong thuong.

--------------------------------------------------------------------
## 1) Muc tieu va tong quan

Vmix Monitor Web la SPA (single-page application) de:
- Giam sat realtime trang thai may trong fleet.
- Tong hop du lieu SRT, Stream, URL/Key, FFmpeg.
- Thong ke CPU/RAM/GPU theo realtime va theo lich su.
- Giam sat vMix (REC/LIVE/EXT) va bieu do Sender/Receiver.
- Cung cap ViewSync de dong bo xem nhieu video YouTube.
- Cung cap Speedtest trong trinh duyet (client-side).

Ung dung bao gom 2 lop tuong tac:
- Backend (REST + WebSocket) tra ve log va statistics.
- Frontend (React + TypeScript + Vite) xu ly, normalize, hien thi.

--------------------------------------------------------------------
## 2) Cong nghe va thu vien

### Runtime / Core
- React 19.2.4 (UI, hooks, state).
- React DOM 19.2.4 (render vao DOM).
- React Router DOM 7.13.1 (routing, protected routes, layout).
- TypeScript ~5.9.3 (type safety, auto-complete, strict).
- Vite 5.4.19 (dev server, bundling, HMR).

### UI, Charts, 3D
- Tailwind CSS 3.4.19 + PostCSS + Autoprefixer (styling).
- ECharts 6 + echarts-for-react (chart CPU/RAM/GPU).
- Three.js 0.183.2 + @react-three/fiber + @react-three/drei (login 3D canvas, stars).
- maath (random point generation cho stars).

### Networking
- axios (REST API, base URL, timeout).
- WebSocket native (realtime log stream).

### Linting
- ESLint 9 + eslint-plugin-react-hooks + eslint-plugin-react-refresh.
- typescript-eslint.

--------------------------------------------------------------------
## 3) Cau truc thu muc (web/)

Phan nay mo ta tung file/thu muc quan trong.

```
web/
   .env                 # env local (khong commit)
   .env.example         # mau env
   .env.local           # env local rieng
   .env.prod            # env production
   eslint.config.js     # ESLint config
   index.html           # root HTML
   package.json         # dependencies + scripts
   pnpm-lock.yaml       # lockfile
   postcss.config.js    # postcss
   tailwind.config.js   # tailwind config
   tsconfig.json        # TS project refs
   tsconfig.app.json    # TS config app
   tsconfig.node.json   # TS config for vite config
   vercel.json          # deploy Vercel + SPA rewrite
   vite.config.ts       # Vite config
   public/
      desktop_pc/        # model 3D login (GLTF + textures)
   src/
      main.tsx           # boot React
      App.tsx            # router + protected layout
      index.css          # global styles + tailwind layers
      layout.css         # sidebar + layout styles
      App.css            # legacy (Vite template, khong import)
      types.ts           # type + helper (MetricPoint, buildPath...)
      config/
         constants.ts     # base URL, WS URL, endpoints, timeout
      services/
         api.ts           # REST API + normalize data
         auth.ts          # login + localStorage auth
      hooks/
         useDashboardContext.ts  # outlet context helper
         useDashboardData.ts     # core data pipeline
      components/
         Sidebar.tsx       # left sidebar
         PageHeaderBar.tsx # top header on layout
         Header.tsx        # header cu (Dashboard.tsx)
         FilterBar.tsx     # filter + dropdown
         ChartSection.tsx  # grid charts
         MachineChartCard.tsx
         StatusSection.tsx
         MachineStatusCard.tsx
         DialogHelpers.tsx
         ui/
            Dialog.tsx
            Toast.tsx
         login/
            CanvasLoader.tsx
            ComputersCanvas.tsx
            StarsCanvas.tsx
      pages/
         DashboardLayout.tsx
         OverviewPage.tsx
         SrtPage.tsx
         StreamPage.tsx
         UrlKeyPage.tsx
         FfmpegPage.tsx
         StatisticsPage.tsx
         VmixMonitorPage.tsx
         ViewSync.tsx
         ViewSyncMulti.tsx
         SpeedtestPage.tsx
         AccountPage.tsx
         RolePage.tsx
         Role.tsx
         Login.tsx
         Login.css
         status/
            StatusByMachinePage.tsx
            StatusByTablePage.tsx
```

--------------------------------------------------------------------
## 4) Entry, routing, layout

### 4.1 main.tsx
- React render vao #root.
- Dung StrictMode de canh bao effect bat loi va side-effects.

### 4.2 App.tsx
- BrowserRouter + Routes.
- ProtectedLayout: neu da login thi vao layout; neu chua login thi redirect /login.
- Route chinh:
   - /dashboard -> OverviewPage
   - /srt, /stream, /url-key, /ffmpeg
   - /statistics
   - /vmix-monitor
   - /viewsync
   - /speedtest
   - /account, /account/roles
   - /viewsync/multi (khong qua layout; man hinh multiview)

### 4.3 DashboardLayout.tsx
- Layout 2 cot: Sidebar ben trai + main ben phai.
- PageHeaderBar o tren main.
- Outlet context = useDashboardData.

--------------------------------------------------------------------
## 5) Authentication

### auth.ts
- authenticate(username, password) -> POST /login
- Neu success: localStorage AUTH true + username.
- isAuthenticated() doc AUTH flag.
- logout() xoa AUTH + username.

### Login.tsx
- Form login + showToast.
- Neu login ok -> /dashboard.
- giao dien 3D: StarsCanvas + ComputersCanvas (React Three Fiber).

--------------------------------------------------------------------
## 6) Config va ENV

### .env.example
```
VITE_BACKEND_BASE_URL=http://localhost:8000
VITE_BACKEND_WS_URL=wss://localhost:8000/ws
VITE_REQUEST_TIMEOUT_MS=30000
```

### constants.ts
- BACKEND_BASE_URL: tu env, fallback to localhost.
- BACKEND_WS_URL: tu env hoac tu BACKEND_BASE_URL (replace http -> ws) + /ws.
- REQUEST_TIMEOUT_MS: tu env hoac 30000.
- API_ENDPOINTS: logs, ws, login, accounts, speedtest, statistics, statistic_hours.

--------------------------------------------------------------------
## 7) API layer va data model

### api.ts
- axios client = baseURL + timeout.
- Type definition cho log, stream, srt, ffmpeg, speedtest, statistic_hours.
- normalizeSrtList / normalizeStreamList / normalizeStreamKeysList / normalizeFfmpegList:
   - backend co the tra array hoac 1 object. Ham normalize luon tra array.
- fetchAllLogs -> GET /logs.
- fetchStatistics -> GET /statistics/{id}?limit=.
- fetchAllStatisticHours -> GET /statistic_hours.
- fetchStatisticHours -> GET /statistic_hours/{id}.
- fetchSpeedtest -> GET /speedtest.
- fetchAccounts -> GET /accounts.

### types.ts
- MetricPoint, MachineMetrics, DeviceFilter, TimeFilter.
- toNumber: parse string/number an toan.
- buildPath / buildAreaPath: helper ve SVG line/area.

--------------------------------------------------------------------
## 8) Core data pipeline (useDashboardData)

useDashboardData la trung tam luan chuyen du lieu cho dashboard.

### 8.1 Xac dinh Machine ID
```
id = ip + ':' + port
neu port khong co -> lay port dau tien trong SRT
neu ip va port rong -> fallback name
```
Muc tieu: trung khop voi backend statistics id.

### 8.2 WebSocket flow
1) Mo WS theo BACKEND_WS_URL.
2) onmessage: parse JSON -> rows (BackendLogItem[]).
3) onclose: auto reconnect sau 3s.
4) wsStatus: connecting / connected / disconnected.

### 8.3 Realtime metrics
- Lan dau: fetch /statistics cho tung may (limit 60).
- Bien history duoc clamp theo 3 phut (REALTIME_WINDOW_MS).
- Khi WS co log moi: append point moi vao history.
- Luu cache vao localStorage de tai nhanh (TTL 3 phut).

### 8.4 Daily metrics
- Chi load 1 lan cho view daily.
- Neu loc 1 may: GET /statistic_hours/{id}.
- Neu loc tat ca: GET /statistic_hours (bulk).
- Neu thieu data: fallback tu log realtime.

### 8.5 Filter va mapping
- deviceFilter: '__all__' hoac id may.
- activeView: 'realtime' hoac 'daily'.
- onlineMachineOptions: chi may statusapp = 1.

--------------------------------------------------------------------
## 9) UI components quan trong

### Sidebar.tsx (left sidebar)
- Danh sach menu + menu con.
- Nhom "Stream" va "Nguoi dung" co expand/collapse.
- Co che collapse sidebar (compact mode).

### PageHeaderBar.tsx
- Hien title theo route.
- Hien username + logout.

### FilterBar.tsx
- Dropdown loc may (searchable).
- Toggle realtime/daily.
- Nut Refresh.

### ChartSection + MachineChartCard
- Dung ECharts line chart.
- CPU/RAM/GPU line, area gradient.
- Axis label tu dong an/hien theo view.

### StatusSection
- Toggle view: theo card (StatusByMachinePage) va bang (StatusByTablePage).
- Luu view mode vao localStorage.

### Dialog + Toast
- Dialog dung createPortal, dong khi click overlay/ESC.
- Toast global (showToast) dung cho login va thong bao.

--------------------------------------------------------------------
## 10) Tat ca chuc nang tren left sidebar

Left sidebar tao thanh cac nhom chuc nang sau (theo Sidebar.tsx).

### 10.1 Tong quan (/dashboard)
- Hien danh sach may theo card (StatusByMachinePage) hoac bang (StatusByTablePage).
- Lay data tu useDashboardData rows.
- Thong tin chinh: CPU, RAM, GPU, ping, statusapp, REC/LIVE/EXT, Sender/Receiver, resolution.

### 10.2 SRT (/srt)
- Group theo may.
- Summary card: tong SRT, dang chay, tat.
- Table: may, IP, ten SRT, port, quality, status.
- Search theo ten may, IP, ten SRT.

### 10.3 Stream (nhom menu)

#### 10.3.1 Thong so Stream (/stream)
- Group stream theo may.
- Summary: tong stream, dang chay, dung.
- Table co merged rows theo may.
- Column: stream name, runtime, health, bitrate, preset, keyframe, dropped...
- Search theo may/IP/ten stream.

#### 10.3.2 URL & Key (/url-key)
- Group stream keys theo may.
- Summary: so may, tong stream, so stream co URL.
- Mask key, nut Eye de hien/hidden.
- Search theo may/IP/URL/key.

#### 10.3.3 FFmpeg (/ffmpeg)
- Group ffmpeg process theo may.
- Summary: so may, tong process, so process dang send.
- Table: process name, PID, send/recv Mbps.
- Search theo may/IP/PID.

### 10.4 Thong ke (/statistics)
- Bieu do CPU/RAM/GPU cho may online.
- Loc theo may va view (realtime / daily).
- Realtime: window 3 phut.
- Daily: avg theo 15 phut (statistic_hours).

### 10.5 Vmix Monitor (/vmix-monitor)
- Card layout show thong so PC + vMix.
- Highlight overload (CPU/RAM/GPU > 50).
- Hien Sender/Receiver, REC/LIVE/EXT.
- Search theo ten may hoac IP.

### 10.6 ViewSync (/viewsync)
- Quan ly danh sach video YouTube, sinh share URL.
- Chon bo cuc tu dong hoac co dinh.
- Mo man hinh multiview (viewsync/multi).
- Chi tiet logic o phan 11.

### 10.7 Speedtest (/speedtest)
- Do ping, download, upload tren trinh duyet.
- Hien progress ring + thong tin IP/ISP.
- Chi tiet logic o phan 12.

### 10.8 Nguoi dung (nhom menu)

#### 10.8.1 Tai khoan (/account)
- GET /accounts, mapping sang list.
- Hien username, status, lastActive, password (mask/show).

#### 10.8.2 Phan quyen (/account/roles)
- UI placeholder role list (hien empty state).
- Co nut them role (chua co logic).

--------------------------------------------------------------------
## 11) ViewSync - logic chi tiet

ViewSync cho phep dong bo nhieu video YouTube va mo che do multiview.

### 11.1 Them video
- Nhap YouTube URL.
- extractVideoId tu URL (regex).
- Validate: URL phai co id 11 ky tu, khong trung lap, toi da 10 video.
- Moi video co:
   - id (YouTube videoId)
   - url (original)
   - title (Video N)
   - startTime (default currentTime = 0)

### 11.2 Layout
- Co danh sach layout L1..L9.
- layoutId = 'auto' hoac layout cu the.
- Auto: chon layout dua vao so video.
- Neu layout co dinh ma vuot max -> fallback auto.
- gridStyle = gridTemplateColumns/Rows theo layout.

### 11.3 Share URL
- buildShareUrl: encode danh sach video vao query string:
   - video0, start0, video1, start1, ...
   - layout=auto
- Copy URL vao clipboard.

### 11.4 Open Multiview
- buildMultiUrl (layout co the auto hoac fixed).
- window.open('/viewsync/multi?...')
- window name: viewsync-multi.

### 11.5 UI states
- Input + list video.
- Preview grid (show URL, label MASTER/SYNC).
- Layout selection grid.

--------------------------------------------------------------------
## 12) ViewSync Multi - logic chi tiet

### 12.1 Nhap tu query string
- Doc video0..videoN + startN.
- extractVideoId tu URL.
- setVideos[] tu query.
- layoutId tu query (default auto).

### 12.2 YouTube Iframe API
- Them script https://www.youtube.com/iframe_api.
- Dung window.onYouTubeIframeAPIReady de khoi tao player.
- Player duoc tao trong div container.
- Fallback: neu API chua ready, render iframe (youtube-nocookie).

### 12.3 Play/Pause tat ca
- playersRef luu player instance theo videoId.
- playAll(): goi playVideo() theo thu tu, co delay nho.
- pauseAll(): goi pauseVideo() cho tat ca.

### 12.4 Layout
- Giong ViewSync: auto/fixed, span theo layout.

--------------------------------------------------------------------
## 13) Speedtest - logic chi tiet

Speedtest chay hoan toan o browser (khong can backend).

### 13.1 Ping
- Goi nhieu lan (PING_ATTEMPTS=5) vao:
   https://speed.cloudflare.com/cdn-cgi/trace
- Do thoi gian round-trip bang performance.now.
- Lay trung binh (avg).

### 13.2 Download
- Download endpoint:
   https://speed.cloudflare.com/__down?bytes=50000000
- Do thoi gian, tinh bps:
   bps = (bytes * 8) / seconds

### 13.3 Upload
- Upload endpoint:
   https://speed.cloudflare.com/__up
- POST payload text co kich thuoc 10,000,000 bytes.
- mode: no-cors (chi can do thoi gian).

### 13.4 IP / ISP
- Thu tu fallback:
   1) ipwho.is
   2) ipapi.co
   3) ipinfo.io
- Neu fail: fallback tu Cloudflare trace.

### 13.5 Progress ring
- progress 0..1
- requestAnimationFrame lam muot displayProgress.
- Vong tron SVG co strokeDashoffset theo progress.

--------------------------------------------------------------------
## 14) Logic giai thuat va xu ly du lieu

### 14.1 Normalize du lieu backend
- Backend co the tra object hoac array.
- Normalize ham bao dam UI luon xu ly array.

### 14.2 Deduplicate + latest row
- Map id -> row moi nhat (theo timestamp) de tranh trung lap.
- O Dashboard.tsx co ham dedupeRowsByMachine.

### 14.3 Realtime window va clamp
- realTime window = 3 phut.
- clampRealtimeHistory cat bot diem cu.
- MAX points = 360 (1 diem/0.5s-1s tu log).

### 14.4 Fallback metric
- Neu API statistics thieu, dung du lieu log de ve 1 diem.

--------------------------------------------------------------------
## 15) Tuong tac voi server

### 15.1 REST
- /logs: danh sach log hien tai.
- /statistics/{id}: du lieu realtime theo may.
- /statistic_hours: du lieu daily da rollup.
- /speedtest: (dang co, co the dung server-side).
- /accounts: danh sach account.
- /login: auth.

### 15.2 WebSocket
- /ws: stream realtime log.
- Frontend reconnect moi 3s neu mat ket noi.

### 15.3 Tich hop WS + REST
- WS cho UI cap nhat nhanh.
- REST cho lich su va fallback.
- Ket hop de tranh "mat du lieu" khi WS cham.

--------------------------------------------------------------------
## 16) So sanh voi JS/HTML thong thuong

### 16.1 Routing
- JS/HTML thuong: moi trang la 1 file HTML, refresh la load lai toan bo.
- SPA: React Router thay doi view khong reload, state giu nguyen.

### 16.2 Data flow
- JS/HTML: fetch data va update DOM bang querySelector.
- React: state -> UI tu dong render, giam loi DOM manipulation.

### 16.3 Type safety
- JS/HTML: khong co type check compile-time.
- TypeScript: bao loi som khi data sai shape.

### 16.4 Build system
- JS/HTML thuong: khong bundler, khong HMR.
- Vite: dev server nhanh, HMR, build toi uu.

### 16.5 Realtime
- JS/HTML: phai tu quan ly state, reconnection, diff DOM.
- React + hooks: useEffect + state + memo de toi uu.

--------------------------------------------------------------------
## 17) Deployment va build

### 17.1 Local dev
```bash
pnpm install
pnpm dev
```

### 17.2 Build + preview
```bash
pnpm build
pnpm preview
```

### 17.3 Vercel
- vercel.json co rewrite den index.html (SPA).
- Root directory: web
- Output: dist
- Env: VITE_BACKEND_BASE_URL, VITE_REQUEST_TIMEOUT_MS, (optional) VITE_BACKEND_WS_URL

--------------------------------------------------------------------
## 18) Ghi chu thuc te

- App.css la file legacy (Vite template), khong duoc import o main.tsx.
- Dashboard.tsx la layout cu (co Header rieng). Hien tai route chinh dung OverviewPage + StatisticsPage + etc.
- ViewSyncMulti khong nam trong sidebar, mo qua URL hoac nut Open Multiview.
- Speedtest su dung Cloudflare speed test endpoints, phu thuoc ket noi internet va CORS.

--------------------------------------------------------------------
## 19) Checklist quick verify

- /login load duoc 3D canvas va form.
- /dashboard hien card may + status.
- /statistics co chart realtime va daily.
- /viewsync add video -> open multiview.
- /speedtest chay duoc ping/download/upload.

--------------------------------------------------------------------
## 20) Ket luan

Project duoc to chuc theo SPA hien dai, tach layer ro rang:
- config / services / hooks / components / pages.
- logic realtime su dung WS + REST.
- UI giai thich ro tung phan theo left sidebar.

Neu can bo sung them tai lieu, co the mo rong phan API contract va dau vao dau ra theo backend.

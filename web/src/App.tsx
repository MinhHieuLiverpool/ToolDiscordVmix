import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import ToastContainer from './components/ui/Toast'
import DashboardLayout from './pages/DashboardLayout'
import OverviewPage from './pages/OverviewPage'
import SrtPage from './pages/SrtPage'
import StreamPage from './pages/StreamPage'
import UrlKeyPage from './pages/UrlKeyPage'
import FfmpegPage from './pages/FfmpegPage'
import StatisticsPage from './pages/StatisticsPage'
import VmixMonitorPage from './pages/VmixMonitorPage'
import MobileMonitorPage from './pages/MobileMonitorPage'
import SpeedtestPage from './pages/SpeedtestPage'
import AccountPage from './pages/AccountPage'
import RolePage from './pages/RolePage'
import ViewSyncPage from './pages/ViewSync'
import ViewSyncMultiPage from './pages/ViewSyncMulti'
import LoginPage from './pages/Login'
import DebugLogPage from './pages/DebugLogPage'
import ImportDebugPage from './pages/ImportDebug'
import CreateWebUrlPage from './pages/CreateWebUrlPage'
import SharedDashboardPage from './pages/SharedDashboardPage'
import { isAuthenticated } from './services/auth'
import { Outlet, useParams } from 'react-router-dom'
import { useEffect, useState, useMemo } from 'react'
import { useDashboardData } from './hooks/useDashboardData'
import { fetchSharedWebConfig, type SharedWebConfig } from './services/api'


function ProtectedLayout() {
  return isAuthenticated() ? <DashboardLayout /> : <Navigate to="/login" replace />
}

function SharedLayout() {
  const { uuid } = useParams<{ uuid: string }>()
  const [config, setConfig] = useState<SharedWebConfig | null>(null)
  const [loadingConfig, setLoadingConfig] = useState(true)
  const [configError, setConfigError] = useState('')
  
  useEffect(() => {
    if (!uuid) return
    fetchSharedWebConfig(uuid)
      .then(res => {
        if (res.success && res.data) {
          setConfig(res.data)
        } else {
          setConfigError(res.message || 'Không tìm thấy cấu hình hoặc liên kết đã bị thu hồi.')
        }
      })
      .catch(err => {
        console.error(err)
        setConfigError('Lỗi kết nối đến máy chủ.')
      })
      .finally(() => {
        setLoadingConfig(false)
      })
  }, [uuid])

  const data = useDashboardData()

  const filteredContextValue = useMemo(() => {
    if (!config) {
      return {
        ...data,
        loading: data.loading || loadingConfig,
        error: data.error || configError,
        allowedFeatures: [] as string[],
        allowedMachines: [] as string[],
        isGameLocked: false
      }
    }
    
    const allowed = config.allowed_machines || []
    const game = config.selected_game || '__all__'
    
    let filteredAllRows = data.allRows.filter(r => allowed.includes(r.data.name))
    if (game !== '__all__') {
      const assignment = data.gameAssignments.find(a => a.game === game)
      if (assignment) {
        filteredAllRows = filteredAllRows.filter(r => assignment.machines.includes(r.data.name))
      } else {
        filteredAllRows = []
      }
    }
    const filteredRows = filteredAllRows
    
    return {
      ...data,
      allRows: filteredAllRows,
      rows: filteredRows,
      selectedGame: game,
      isGameLocked: game !== '__all__',
      loading: data.loading || loadingConfig,
      error: data.error || configError,
      allowedFeatures: config.allowed_features || [],
      allowedMachines: allowed
    }
  }, [data, config, loadingConfig, configError])

  return <Outlet context={filteredContextValue} />
}

function App() {
  const authenticated = isAuthenticated()

  return (
    <BrowserRouter>
      <ToastContainer />
      <Routes>
        <Route path="/viewsync/multi" element={<ViewSyncMultiPage />} />
        
        {/* Shared views without login or sidebar */}
        <Route element={<SharedLayout />}>
          <Route path="/shared/:uuid" element={<SharedDashboardPage />} />
        </Route>

        {/* Protected routes with sidebar layout */}
        <Route element={<ProtectedLayout />}>
          <Route path="/dashboard" element={<OverviewPage />} />
          <Route path="/create-web-url" element={<CreateWebUrlPage />} />
          <Route path="/srt" element={<SrtPage />} />
          <Route path="/stream" element={<StreamPage />} />
          <Route path="/url-key" element={<UrlKeyPage />} />
          <Route path="/ffmpeg" element={<FfmpegPage />} />
          <Route path="/statistics" element={<StatisticsPage />} />
          <Route path="/vmix-monitor" element={<VmixMonitorPage />} />
          <Route path="/mobile-monitor" element={<MobileMonitorPage />} />
          <Route path="/viewsync" element={<ViewSyncPage />} />
          <Route path="/speedtest" element={<SpeedtestPage />} />
          <Route path="/account" element={<AccountPage />} />
          <Route path="/account/roles" element={<RolePage />} />
          <Route path="/debug-logs" element={<DebugLogPage />} />
          <Route path="/debug-logs/import" element={<ImportDebugPage />} />
        </Route>

        {/* Login */}
        <Route path="/Login" element={<LoginPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="*" element={<Navigate to={authenticated ? '/dashboard' : '/login'} replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App

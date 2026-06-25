import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import ToastContainer from './components/ui/Toast'
import DashboardLayout from './pages/DashboardLayout'
import OverviewPage from './pages/OverviewPage'
import SrtPage from './pages/SrtPage'
import StreamPage from './pages/StreamPage'
import UrlKeyPage from './pages/UrlKeyPage'
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
import ImportDebugChartsPage from './pages/ImportDebugCharts'
import CreateWebUrlPage from './pages/CreateWebUrlPage'
import SharedDashboardPage from './pages/SharedDashboardPage'
import GameChannelsPage from './pages/GameChannelsPage'
import { isAuthenticated } from './services/auth'
import { Outlet, useParams } from 'react-router-dom'
import { useEffect, useState, useMemo } from 'react'
import { useDashboardData } from './hooks/useDashboardData'
import { fetchSharedWebConfig, type SharedWebConfig, normalizeSrtList } from './services/api'


function ProtectedLayout() {
  return isAuthenticated() ? <DashboardLayout /> : <Navigate to="/login" replace />
}

function ProtectedNoSidebarLayout() {
  const data = useDashboardData()
  return isAuthenticated() ? <Outlet context={data} /> : <Navigate to="/login" replace />
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
        isConfigInvalid: !!configError,
        allowedFeatures: [] as string[],
        allowedMachines: [] as string[],
        isGameLocked: false
      }
    }
    
    const allowed = config.allowed_machines || []
    const game = config.selected_game || '__all__'
    const shareType = config.share_type || 'machines'
    
    let filteredAllRows = data.allRows
    if (shareType === 'game') {
      if (game !== '__all__') {
        const assignment = data.gameAssignments.find(a => a.game === game)
        if (assignment && assignment.visible_status !== 'OFF') {
          const hiddenMachines = assignment.hidden_machines || []
          filteredAllRows = data.allRows.filter(r => assignment.machines.includes(r.data.name) && !hiddenMachines.includes(r.data.name))
        } else {
          filteredAllRows = []
        }
      } else {
        filteredAllRows = data.allRows.filter((row) => {
          const machineName = row.data.name
          const memberChannels = data.gameAssignments.filter(a => a.machines.includes(machineName))
          if (memberChannels.length === 0) return true
          return memberChannels.some(a => {
            const channelIsOn = a.visible_status !== 'OFF'
            const machineIsNotHiddenInChannel = !(a.hidden_machines || []).includes(machineName)
            return channelIsOn && machineIsNotHiddenInChannel
          })
        })
      }
    } else {
      filteredAllRows = data.allRows.filter(r => allowed.includes(r.data.name))
    }
    // Build allowed machine IDs for onlineMachineOptions filtering
    const map = new Map<string, string>()
    const allowedMachineNames = filteredAllRows.map(r => r.data.name)
    filteredAllRows.forEach((item) => {
      const ip = String(item.data.ip || '').trim()
      const port = String(item.data.port || '').trim()
      const srtList = normalizeSrtList(item.data.SRT)
      const srtPort = port || String(srtList[0]?.port || '').trim()
      const id = (ip || srtPort) ? `${ip}:${srtPort}` : String(item.data.name || '').trim()
      if (id) {
        map.set(id, item.data.name)
      }
    })
    const allowedMachineIds = new Set(map.keys())
    
    const onlineMachineOptions = data.onlineMachineOptions.filter((opt: any) => allowedMachineIds.has(opt.id))
    const filteredMachines = data.filteredMachines.filter((m: any) => {
      const name = m.latestItem?.data.name
      return name && allowedMachineNames.includes(name)
    })
    const totalOnline = filteredAllRows.filter((item) => Number(item.data.statusapp ?? 0) === 1).length
    
    return {
      ...data,
      allRows: filteredAllRows,
      rows: filteredAllRows,
      selectedGame: game,
      isGameLocked: true,
      isConfigInvalid: !!configError,
      loading: data.loading || loadingConfig,
      error: data.error || configError,
      allowedFeatures: config.allowed_features || [],
      allowedMachines: allowed,
      onlineMachineOptions,
      filteredMachines,
      totalOnline
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
          <Route path="/game-channels" element={<GameChannelsPage />} />
          <Route path="/srt" element={<SrtPage />} />
          <Route path="/stream" element={<StreamPage />} />
          <Route path="/url-key" element={<UrlKeyPage />} />
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

        {/* Protected routes without sidebar layout */}
        <Route element={<ProtectedNoSidebarLayout />}>
          <Route path="/debug-logs/import/charts" element={<ImportDebugChartsPage />} />
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

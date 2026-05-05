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
import AccountPage from './pages/AccountPage'
import RolePage from './pages/RolePage'
import LoginPage from './pages/Login'
import { isAuthenticated } from './services/auth'

function ProtectedLayout() {
  return isAuthenticated() ? <DashboardLayout /> : <Navigate to="/login" replace />
}

function App() {
  const authenticated = isAuthenticated()

  return (
    <BrowserRouter>
      <ToastContainer />
      <Routes>
        {/* Protected routes with sidebar layout */}
        <Route element={<ProtectedLayout />}>
          <Route path="/dashboard" element={<OverviewPage />} />
          <Route path="/srt" element={<SrtPage />} />
          <Route path="/stream" element={<StreamPage />} />
          <Route path="/url-key" element={<UrlKeyPage />} />
          <Route path="/ffmpeg" element={<FfmpegPage />} />
          <Route path="/statistics" element={<StatisticsPage />} />
          <Route path="/vmix-monitor" element={<VmixMonitorPage />} />
          <Route path="/account" element={<AccountPage />} />
          <Route path="/account/roles" element={<RolePage />} />
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

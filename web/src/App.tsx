import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import ToastContainer from './components/ui/Toast'
import Dashboard from './pages/Dashboard'
import LoginPage from './pages/Login'
import { isAuthenticated } from './services/auth'

function ProtectedDashboard() {
  return isAuthenticated() ? <Dashboard /> : <Navigate to="/login" replace />
}

function App() {
  const authenticated = isAuthenticated()

  return (
    <BrowserRouter>
      <ToastContainer />
      <Routes>
        <Route path="/dashboard" element={<ProtectedDashboard />} />
        <Route path="/Login" element={<LoginPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="*" element={<Navigate to={authenticated ? '/dashboard' : '/login'} replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App

import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import ComputersCanvas from '../components/login/ComputersCanvas'
import StarsCanvas from '../components/login/StarsCanvas'
import { showToast } from '../components/ui/Toast'
import { authenticate, isAuthenticated } from '../services/auth'
import './Login.css'

const LoginPage = () => {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (isAuthenticated()) {
      navigate('/dashboard', { replace: true })
    }
  }, [navigate])

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    if (!username.trim() || !password) {
      showToast('Vui lòng nhập đầy đủ tài khoản và mật khẩu.', 'warning')
      return
    }

    setLoading(true)

    const result = await authenticate(username, password)

    if (!result.success) {
      showToast(result.message || 'Tài khoản hoặc mật khẩu không đúng.', 'error')
      setLoading(false)
      return
    }

    showToast('Đăng nhập thành công! Đang chuyển hướng...', 'success')
    setTimeout(() => {
      navigate('/dashboard', { replace: true })
    }, 800)
  }

  return (
    <section className="login-hero">
      <StarsCanvas />

      <nav className="login-nav" aria-label="Header">
        <div className="login-brand">
          <img className="login-corner-icon" src="/favicon.svg" alt="VmixMonitor" />
          <span className="login-brand-title">Vmix Monitor</span>
        </div>
      </nav>

      <div className="login-content">
        <div className="login-accent">
          <div className="login-accent-dot" />
          <div className="login-accent-line" />
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          <h1 className="login-title">Đăng nhập vào Dashboard VmixMonitor</h1>
          <input
            className="login-input"
            type="text"
            placeholder="Tài khoản"
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            disabled={loading}
          />
          <input
            className="login-input"
            type="password"
            placeholder="Mật khẩu"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            disabled={loading}
          />
          <button className="login-button" type="submit" disabled={loading}>
            {loading ? (
              <span className="login-btn-loading">
                <span className="login-spinner" />
                Đang xử lý...
              </span>
            ) : (
              'Đăng nhập'
            )}
          </button>
        </form>

        <aside className="login-madeby" aria-label="Author Information">
          <img className="login-madeby-logo" src="/garena.png" alt="Logo" />
          <div className="login-madeby-text">
            <p className="login-madeby-label">Made by</p>
            <h2 className="login-madeby-name">TEAM STUDIO</h2>
          </div>
        </aside>
      </div>

      <div className="login-canvas-wrap">
        <ComputersCanvas />
      </div>
    </section>
  )
}

export default LoginPage
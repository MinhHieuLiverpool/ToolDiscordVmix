import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import ComputersCanvas from '../components/login/ComputersCanvas'
import StarsCanvas from '../components/login/StarsCanvas'
import { authenticate, isAuthenticated } from '../services/auth'
import './Login.css'

const LoginPage = () => {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    if (isAuthenticated()) {
      navigate('/dashboard', { replace: true })
    }
  }, [navigate])

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    if (!username.trim() || !password) {
      setError('Vui long nhap day du tai khoan va mat khau.')
      return
    }

    const result = await authenticate(username, password)
    if (!result.success) {
      setError(result.message || 'Tai khoan hoac mat khau khong dung.')
      return
    }

    setError('')
    navigate('/dashboard', { replace: true })
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
          />
          <input
            className="login-input"
            type="password"
            placeholder="Mật khẩu"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          {error ? <p className="login-error">{error}</p> : null}
          <button className="login-button" type="submit">
            Đăng nhập
          </button>
        </form>

        <aside className="login-madeby" aria-label="Author Information">
          <img className="login-madeby-logo" src="/garena.png" alt="Logo" />
          <div className="login-madeby-text">
            <p className="login-madeby-label">Made by</p>
            <h2 className="login-madeby-name">NGUYEN CUNG CHANH</h2>
            <h2 className="login-madeby-name">BUI QUANG MINH HIEU</h2>
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
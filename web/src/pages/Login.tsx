import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import ComputersCanvas from '../components/login/ComputersCanvas'
import StarsCanvas from '../components/login/StarsCanvas'
import { showToast } from '../components/ui/Toast'
import { authenticate, isAuthenticated } from '../services/auth'
import { useLanguage } from '../config/i18n'
import LanguageToggle from '../components/LanguageToggle'
import './Login.css'

const LoginPage = () => {
  const navigate = useNavigate()
  const { t } = useLanguage()
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
      showToast(t('auth.loginRequired'), 'warning')
      return
    }

    setLoading(true)

    const result = await authenticate(username, password)

    if (!result.success) {
      showToast(result.message || t('auth.loginError'), 'error')
      setLoading(false)
      return
    }

    showToast(t('auth.loginSuccess'), 'success')
    setTimeout(() => {
      navigate('/dashboard', { replace: true })
    }, 800)
  }

  return (
    <section className="login-hero">
      <StarsCanvas />

      <nav className="login-nav" aria-label="Header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div className="login-brand">
          <img className="login-corner-icon" src="/favicon.svg" alt="VmixMonitor" />
          <span className="login-brand-title">Vmix Monitor</span>
        </div>
        <div style={{ marginRight: '1.5rem' }}>
          <LanguageToggle />
        </div>
      </nav>

      <div className="login-content">
        <div className="login-accent">
          <div className="login-accent-dot" />
          <div className="login-accent-line" />
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          <h1 className="login-title">{t('auth.loginTitle')}</h1>
          <input
            className="login-input"
            type="text"
            placeholder={t('auth.username')}
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            disabled={loading}
          />
          <input
            className="login-input"
            type="password"
            placeholder={t('auth.password')}
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            disabled={loading}
          />
          <button className="login-button" type="submit" disabled={loading}>
            {loading ? (
              <span className="login-btn-loading">
                <span className="login-spinner" />
                {t('auth.loggingIn')}
              </span>
            ) : (
              t('auth.loginButton')
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
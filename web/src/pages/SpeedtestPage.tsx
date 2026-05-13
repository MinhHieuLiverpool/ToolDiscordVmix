import { useState } from 'react'
import { fetchSpeedtest, type SpeedtestResponse } from '../services/api'

export default function SpeedtestPage() {
    const [result, setResult] = useState<SpeedtestResponse | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')

    const formatNumber = (value?: number | null) => {
        if (value === null || value === undefined) return '--'
        return value.toFixed(2)
    }

    const formatTimestamp = (value?: string | null) => {
        if (!value) return '--'
        const parsed = new Date(value)
        if (Number.isNaN(parsed.getTime())) return '--'
        return parsed.toLocaleString('vi-VN', { hour12: false })
    }

    const statusTone = loading
        ? 'is-loading'
        : error
          ? 'is-error'
          : result
            ? 'is-ready'
            : 'is-idle'
    const statusText = loading
        ? 'Đang đo băng thông...'
        : error
          ? 'Có lỗi khi đo'
          : result
            ? 'Hoàn tất'
            : 'Chưa chạy'

    const handleRun = async () => {
        if (loading) return
        setLoading(true)
        setError('')
        try {
            const data = await fetchSpeedtest()
            if (!data.success) {
                setError(data.message || data.error || 'Speedtest thất bại.')
                setResult(null)
            } else {
                setResult(data)
            }
        } catch (err) {
            console.error(err)
            setError('Không thể gọi speedtest từ backend.')
            setResult(null)
        } finally {
            setLoading(false)
        }
    }

    const ipWanValue = result?.ipwan || result?.raw?.client?.ip || '--'
    const ispValue =
        result?.isp ||
        result?.raw?.client?.isp ||
        result?.raw?.client?.isp_name ||
        result?.raw?.client?.ispName ||
        '--'

    return (
        <section className="card-light speedtest-card">
            <div className="speedtest-hero">
                <div className="speedtest-header">
                    <div className="speedtest-tag">Network Lab</div>
                    <h2 className="speedtest-title">Speedtest</h2>
                </div>
            </div>
            <div className="speedtest-actions">
                <div className="speedtest-action-center">
                    <div
                        className={`speedtest-btn ${loading ? 'is-disabled' : ''}`}
                        role="button"
                        tabIndex={0}
                        onClick={handleRun}
                        onKeyDown={(event) => {
                            if (event.key === 'Enter' || event.key === ' ') {
                                event.preventDefault()
                                handleRun()
                            }
                        }}
                        aria-disabled={loading}
                    >
                        <svg className="speedtest-ring" viewBox="0 0 120 120" aria-hidden="true">
                            <circle className="speedtest-ring-base" cx="60" cy="60" r="50" />
                            <circle className="speedtest-ring-active" cx="60" cy="60" r="50" />
                        </svg>
                        <span className="speedtest-btn-label">{loading ? 'Dang do' : 'Start'}</span>
                    </div>
                </div>
                <div className={`speedtest-status ${statusTone}`}>
                    <span className="speedtest-status-dot" />
                    <span>{statusText}</span>
                </div>
            </div>

            <div className="speedtest-grid">
                <div className="speedtest-stat speedtest-download">
                    <span className="speedtest-label">Download</span>
                    <div className="speedtest-value-row">
                        <span className="speedtest-value">{formatNumber(result?.download_mbps)}</span>
                        <span className="speedtest-unit">Mbps</span>
                    </div>
                    <span className="speedtest-caption">Băng thông tải xuống</span>
                </div>
                <div className="speedtest-stat speedtest-upload">
                    <span className="speedtest-label">Upload</span>
                    <div className="speedtest-value-row">
                        <span className="speedtest-value">{formatNumber(result?.upload_mbps)}</span>
                        <span className="speedtest-unit">Mbps</span>
                    </div>
                    <span className="speedtest-caption">Băng thông tải lên</span>
                </div>
                <div className="speedtest-stat speedtest-ping">
                    <span className="speedtest-label">Ping</span>
                    <div className="speedtest-value-row">
                        <span className="speedtest-value">{formatNumber(result?.ping_ms)}</span>
                        <span className="speedtest-unit">ms</span>
                    </div>
                    <span className="speedtest-caption">Độ trễ trung bình</span>
                </div>
            </div>

            <div className="speedtest-meta">
                <div className="speedtest-meta-item">
                    <span className="speedtest-meta-label">Thời điểm</span>
                    <span className="speedtest-meta-value">{formatTimestamp(result?.timestamp)}</span>
                </div>
                <div className="speedtest-meta-item">
                    <span className="speedtest-meta-label">IP WAN</span>
                    <span className="speedtest-meta-value">{ipWanValue}</span>
                </div>
                <div className="speedtest-meta-item">
                    <span className="speedtest-meta-label">Nha mang</span>
                    <span className="speedtest-meta-value">{ispValue}</span>
                </div>
            </div>

            {error ? <div className="speedtest-note is-error">{error}</div> : null}
        </section>
    )
}

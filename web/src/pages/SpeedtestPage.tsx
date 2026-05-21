import { useEffect, useState } from 'react'
import { type SpeedtestResponse } from '../services/api'

const SPEEDTEST_HOST = 'https://speed.cloudflare.com'
const DOWNLOAD_BYTES = 50_000_000
const UPLOAD_BYTES = 10_000_000
const PING_ATTEMPTS = 5
const RING_CIRCUMFERENCE = 339.3

type BrowserSpeedtestResult = SpeedtestResponse

const getNow = () => (typeof performance !== 'undefined' ? performance.now() : Date.now())

const buildCacheBuster = () => `${Date.now()}-${Math.random().toString(16).slice(2)}`

const fetchTraceIp = async () => {
    try {
        const response = await fetch(`${SPEEDTEST_HOST}/cdn-cgi/trace?cache=${buildCacheBuster()}`, {
            cache: 'no-store',
        })
        if (!response.ok) return null
        const text = await response.text()
        const ipLine = text.split('\n').find((line) => line.startsWith('ip='))
        return ipLine ? ipLine.replace('ip=', '').trim() : null
    } catch {
        return null
    }
}

const fetchIpInfo = async () => {
    const sources = [
        {
            url: 'https://ipwho.is/?fields=ip,isp,success',
            parse: (data: any) =>
                data?.success
                    ? { ip: data?.ip, isp: data?.isp }
                    : null,
        },
        {
            url: 'https://ipapi.co/json/',
            parse: (data: any) => ({ ip: data?.ip, isp: data?.org || data?.isp }),
        },
        {
            url: 'https://ipinfo.io/json',
            parse: (data: any) => ({ ip: data?.ip, isp: data?.org }),
        },
    ]

    for (const source of sources) {
        try {
            const response = await fetch(source.url, { cache: 'no-store' })
            if (!response.ok) continue
            const data = await response.json()
            const parsed = source.parse(data)
            if (parsed?.ip) {
                return {
                    ip: typeof parsed.ip === 'string' ? parsed.ip : null,
                    isp: typeof parsed.isp === 'string' ? parsed.isp : null,
                }
            }
        } catch {
            // try next source
        }
    }
    return null
}

const measurePing = async () => {
    const samples: number[] = []
    for (let i = 0; i < PING_ATTEMPTS; i += 1) {
        const start = getNow()
        try {
            await fetch(`${SPEEDTEST_HOST}/cdn-cgi/trace?cache=${buildCacheBuster()}`, {
                cache: 'no-store',
            })
        } catch {
            // ignore failed ping sample
        }
        const end = getNow()
        samples.push(end - start)
    }
    if (samples.length === 0) return null
    const avg = samples.reduce((sum, value) => sum + value, 0) / samples.length
    return Number.isFinite(avg) ? avg : null
}

const measureDownload = async () => {
    const url = `${SPEEDTEST_HOST}/__down?bytes=${DOWNLOAD_BYTES}&cache=${buildCacheBuster()}`
    const start = getNow()
    const response = await fetch(url, { cache: 'no-store' })
    if (!response.ok) {
        throw new Error('Download test failed.')
    }
    await response.arrayBuffer()
    const end = getNow()
    const seconds = Math.max(0.001, (end - start) / 1000)
    return (DOWNLOAD_BYTES * 8) / seconds
}

const measureUpload = async () => {
    const url = `${SPEEDTEST_HOST}/__up?cache=${buildCacheBuster()}`
    const payload = '0'.repeat(UPLOAD_BYTES)
    const start = getNow()
    await fetch(url, {
        method: 'POST',
        cache: 'no-store',
        mode: 'no-cors',
        body: payload,
    })
    const end = getNow()
    const seconds = Math.max(0.001, (end - start) / 1000)
    return (UPLOAD_BYTES * 8) / seconds
}

const runBrowserSpeedtest = async (
    onProgress: (value: number, stage?: string) => void,
): Promise<BrowserSpeedtestResult> => {
    onProgress(0.05, 'Ping')
    const [traceIp, ping_ms, ipInfo] = await Promise.all([
        fetchTraceIp(),
        measurePing(),
        fetchIpInfo(),
    ])
    onProgress(0.3, 'Download')
    const ipwan = ipInfo?.ip || traceIp
    const isp = ipInfo?.isp || null
    const download_bps = await measureDownload()
    onProgress(0.75, 'Upload')
    const upload_bps = await measureUpload()
    onProgress(1, 'Hoan tat')
    return {
        success: true,
        timestamp: new Date().toISOString(),
        ping_ms,
        download_bps,
        upload_bps,
        download_mbps: download_bps / 1_000_000,
        upload_mbps: upload_bps / 1_000_000,
        ipwan,
        isp,
    }
}

export default function SpeedtestPage() {
    const [result, setResult] = useState<SpeedtestResponse | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const [progress, setProgress] = useState(0)
    const [progressLabel, setProgressLabel] = useState('')
    const [displayProgress, setDisplayProgress] = useState(0)

    useEffect(() => {
        let frameId: number

        const tick = () => {
            setDisplayProgress((current) => {
                const diff = progress - current
                if (Math.abs(diff) < 0.001) return progress
                return current + diff * 0.15
            })
            frameId = requestAnimationFrame(tick)
        }

        frameId = requestAnimationFrame(tick)
        return () => cancelAnimationFrame(frameId)
    }, [progress])

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
        setProgress(0)
        setProgressLabel('')
        try {
            const data = await runBrowserSpeedtest((value, stage) => {
                setProgress(value)
                if (stage) setProgressLabel(stage)
            })
            setResult(data)
        } catch (err) {
            console.error(err)
            setError('Không thể đo speedtest trên trình duyệt.')
            setResult(null)
        } finally {
            setLoading(false)
        }
    }

    const showResult = !loading && !!result
    const ipWanValue = showResult ? (result?.ipwan || result?.raw?.client?.ip || '--') : '--'
    const ispValue = showResult
        ? (
            result?.isp ||
            result?.raw?.client?.isp ||
            result?.raw?.client?.isp_name ||
            result?.raw?.client?.ispName ||
            '--'
        )
        : '--'

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
                            <circle
                                className="speedtest-ring-active"
                                cx="60"
                                cy="60"
                                r="50"
                                style={{
                                    strokeDashoffset: RING_CIRCUMFERENCE * (1 - displayProgress),
                                }}
                            />
                        </svg>
                        <span className="speedtest-btn-label">
                            {loading
                                ? `${progressLabel || 'Dang do'} ${Math.round(displayProgress * 100)}%`
                                : 'Start'}
                        </span>
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
                        <span className="speedtest-value">{showResult ? formatNumber(result?.download_mbps) : '--'}</span>
                        <span className="speedtest-unit">Mbps</span>
                    </div>
                    <span className="speedtest-caption">Băng thông tải xuống</span>
                </div>
                <div className="speedtest-stat speedtest-upload">
                    <span className="speedtest-label">Upload</span>
                    <div className="speedtest-value-row">
                        <span className="speedtest-value">{showResult ? formatNumber(result?.upload_mbps) : '--'}</span>
                        <span className="speedtest-unit">Mbps</span>
                    </div>
                    <span className="speedtest-caption">Băng thông tải lên</span>
                </div>
                <div className="speedtest-stat speedtest-ping">
                    <span className="speedtest-label">Ping</span>
                    <div className="speedtest-value-row">
                        <span className="speedtest-value">{showResult ? formatNumber(result?.ping_ms) : '--'}</span>
                        <span className="speedtest-unit">ms</span>
                    </div>
                    <span className="speedtest-caption">Độ trễ trung bình</span>
                </div>
            </div>

            <div className="speedtest-meta">
                <div className="speedtest-meta-item">
                    <span className="speedtest-meta-label">Thời điểm</span>
                    <span className="speedtest-meta-value">{showResult ? formatTimestamp(result?.timestamp) : '--'}</span>
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

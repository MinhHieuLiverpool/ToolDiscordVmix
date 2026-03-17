import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { BACKEND_WS_URL } from './config/constants'
import { fetchAllLogs, fetchStatistics } from './services/api'
import type { BackendLogItem } from './services/api'

type MetricPoint = {
  timeLabel: string
  cpu: number
  ram: number
}

function toNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === '') {
    return null
  }

  const parsed = Number.parseFloat(String(value).replace(',', '.'))
  return Number.isFinite(parsed) ? parsed : null
}

function buildPath(values: number[], chartWidth: number, chartHeight: number, maxValue: number): string {
  if (values.length === 0) {
    return ''
  }

  if (values.length === 1) {
    const y = chartHeight - (values[0] / maxValue) * chartHeight
    return `M 0 ${y}`
  }

  const stepX = chartWidth / (values.length - 1)
  return values
    .map((value, index) => {
      const x = index * stepX
      const y = chartHeight - (value / maxValue) * chartHeight
      return `${index === 0 ? 'M' : 'L'} ${x} ${y}`
    })
    .join(' ')
}

function buildAreaPath(values: number[], chartWidth: number, chartHeight: number, maxValue: number): string {
  const linePath = buildPath(values, chartWidth, chartHeight, maxValue)
  if (!linePath) {
    return ''
  }

  if (values.length === 1) {
    const y = chartHeight - (values[0] / maxValue) * chartHeight
    return `M 0 ${chartHeight} L 0 ${y} L 0 ${chartHeight} Z`
  }

  return `${linePath} L ${chartWidth} ${chartHeight} L 0 ${chartHeight} Z`
}

function MetricChart({
  title,
  values,
  labels,
  colorClass,
  maxValue,
  unit,
}: {
  title: string
  values: number[]
  labels: string[]
  colorClass: string
  maxValue: number
  unit: string
}) {
  const chartWidth = 640
  const plotHeight = 160
  const axisHeight = 28
  const chartHeight = plotHeight + axisHeight
  const safeMax = Math.max(maxValue, 1)
  const path = buildPath(values, chartWidth, plotHeight, safeMax)
  const areaPath = buildAreaPath(values, chartWidth, plotHeight, safeMax)
  const isCpuChart = colorClass.includes('emerald')
  const strokeColor = isCpuChart ? '#10b981' : '#0ea5e9'
  const fillColor = isCpuChart ? 'rgba(16, 185, 129, 0.16)' : 'rgba(14, 165, 233, 0.16)'
  const latestValue = values.length > 0 ? values[values.length - 1] : 0
  const latestLabel = labels.length > 0 ? labels[labels.length - 1] : '--:--:--'

  const xTickIndices = useMemo(() => {
    if (labels.length === 0) {
      return [] as number[]
    }

    const desiredTicks = Math.min(7, labels.length)
    if (desiredTicks <= 1) {
      return [0]
    }

    const indices = Array.from({ length: desiredTicks }, (_, i) =>
      Math.round((i * (labels.length - 1)) / (desiredTicks - 1)),
    )
    return Array.from(new Set(indices))
  }, [labels])

  const stepX = labels.length > 1 ? chartWidth / (labels.length - 1) : 0

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-bold uppercase tracking-wide text-slate-700">{title}</h3>
        <span className={`rounded-lg px-2 py-1 text-xs font-semibold ${colorClass}`}>
          {latestValue.toFixed(1)}{unit} @ {latestLabel}
        </span>
      </div>
      <svg className="h-52 w-full" viewBox={`0 0 ${chartWidth} ${chartHeight}`} preserveAspectRatio="none">
        <line x1="0" y1={plotHeight} x2={chartWidth} y2={plotHeight} className="stroke-slate-200" />
        <line x1="0" y1={plotHeight / 2} x2={chartWidth} y2={plotHeight / 2} className="stroke-slate-100" />
        <line x1="0" y1="0" x2={chartWidth} y2="0" className="stroke-slate-100" />
        {xTickIndices.map((index) => {
          const x = stepX * index
          return <line key={`grid-${index}`} x1={x} y1="0" x2={x} y2={plotHeight} className="stroke-slate-100" />
        })}
        {areaPath ? <path d={areaPath} style={{ fill: fillColor }} /> : null}
        {path ? (
          <path d={path} fill="none" style={{ stroke: strokeColor, strokeWidth: 3 }} />
        ) : null}
        {xTickIndices.map((index) => {
          const x = stepX * index
          return (
            <text
              key={`tick-${index}`}
              x={x}
              y={plotHeight + 16}
              textAnchor="middle"
              className="fill-slate-500 text-[10px]"
            >
              {labels[index]}
            </text>
          )
        })}
      </svg>
      <div className="mt-1 flex justify-between text-[11px] text-slate-500">
        <span>{labels[0] || '--:--:--'}</span>
        <span>{latestLabel}</span>
      </div>
    </article>
  )
}

function App() {
  const [rows, setRows] = useState<BackendLogItem[]>([])
  const [metricHistory, setMetricHistory] = useState<MetricPoint[]>([])
  const [selectedStatisticsId, setSelectedStatisticsId] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting')

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimerRef = useRef<number | null>(null)

  const loadData = useCallback(async () => {
    try {
      setError('')
      const data = await fetchAllLogs()
      setRows(data)
    } catch (err) {
      setError('Khong the lay du lieu tu backend. Vui long thu lai.')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [])

  const connectWebSocket = useCallback(() => {
    setWsStatus('connecting')

    const ws = new WebSocket(BACKEND_WS_URL)
    wsRef.current = ws

    ws.onopen = () => {
      setWsStatus('connected')
      setError('')
    }

    ws.onmessage = (event) => {
      try {
        const incoming = JSON.parse(event.data) as BackendLogItem[]
        setRows(incoming)
        setLoading(false)
      } catch (parseError) {
        console.error(parseError)
      }
    }

    ws.onerror = () => {
      setError('WebSocket gap loi, dang thu ket noi lai...')
    }

    ws.onclose = () => {
      setWsStatus('disconnected')
      if (reconnectTimerRef.current) {
        window.clearTimeout(reconnectTimerRef.current)
      }
      reconnectTimerRef.current = window.setTimeout(() => {
        connectWebSocket()
      }, 3000)
    }
  }, [])

  const statisticOptions = useMemo(() => {
    const map = new Map<string, { id: string; label: string }>()
    rows.forEach((item) => {
      const ip = String(item.data.ip || '').trim()
      const port = String(item.data.port || '').trim()
      if (!ip && !port) {
        return
      }
      const id = `${ip}:${port}`
      const name = String(item.data.name || 'Unknown')
      map.set(id, { id, label: `${name} (${id})` })
    })
    return Array.from(map.values())
  }, [rows])

  useEffect(() => {
    if (!selectedStatisticsId && statisticOptions.length > 0) {
      setSelectedStatisticsId(statisticOptions[0].id)
    }
  }, [selectedStatisticsId, statisticOptions])

  const loadStatisticsHistory = useCallback(async () => {
    if (!selectedStatisticsId) {
      setMetricHistory([])
      return
    }

    try {
      const payload = await fetchStatistics(selectedStatisticsId, 200)
      const history = (payload.data || [])
        .map((point) => {
          const cpu = toNumber(point.cpu) ?? 0
          const ram = toNumber(point.ram) ?? 0
          const date = new Date(point.time)
          const timeLabel = Number.isNaN(date.getTime())
            ? String(point.time || '').slice(11, 19)
            : date.toLocaleTimeString('vi-VN', { hour12: false })

          return { timeLabel, cpu, ram }
        })
        .slice(-200)

      setMetricHistory(history)
    } catch (err) {
      console.error(err)
    }
  }, [selectedStatisticsId])

  useEffect(() => {
    void loadStatisticsHistory()
    const intervalId = window.setInterval(() => {
      void loadStatisticsHistory()
    }, 5000)

    return () => {
      window.clearInterval(intervalId)
    }
  }, [loadStatisticsHistory])

  useEffect(() => {
    connectWebSocket()
    return () => {
      if (reconnectTimerRef.current) {
        window.clearTimeout(reconnectTimerRef.current)
      }
      wsRef.current?.close()
    }
  }, [connectWebSocket])

  const totalOnline = useMemo(
    () => rows.filter((item) => ['ONLINE', 'ON'].includes(item.data.status?.toUpperCase())).length,
    [rows],
  )

  const cpuSeries = useMemo(() => metricHistory.map((point) => point.cpu), [metricHistory])
  const ramSeries = useMemo(() => metricHistory.map((point) => point.ram), [metricHistory])
  const timeLabels = useMemo(() => metricHistory.map((point) => point.timeLabel), [metricHistory])
  const ramMax = useMemo(() => {
    const max = ramSeries.length > 0 ? Math.max(...ramSeries) : 100
    return Math.max(100, Math.ceil(max / 10) * 10)
  }, [ramSeries])

  return (
    <div className="min-h-screen px-4 py-10 sm:px-8">
      <div className="mx-auto max-w-7xl">
        <header className="mb-10 rounded-3xl border border-orange-200/70 bg-white/70 p-8 shadow-lg backdrop-blur sm:p-10">
          <p className="mb-3 inline-flex rounded-full bg-amber-100 px-3 py-1 text-xs font-bold uppercase tracking-wider text-orange-700">
            ToolDiscordVmix Web
          </p>
          <h1 className="text-3xl font-extrabold leading-tight text-ink sm:text-5xl">
            Backend Logs Dashboard
          </h1>
          <p className="mt-4 max-w-2xl text-sm text-slate-600 sm:text-base">
            Du lieu realtime qua WebSocket tu backend: {BACKEND_WS_URL}
          </p>
          <div className="mt-4 flex max-w-xl items-center gap-2">
            <label className="text-xs font-bold uppercase tracking-wide text-slate-600" htmlFor="machine-select">
              Bieu do theo may
            </label>
            <select
              id="machine-select"
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700"
              value={selectedStatisticsId}
              onChange={(event) => setSelectedStatisticsId(event.target.value)}
            >
              {statisticOptions.length === 0 ? <option value="">Chua co du lieu may</option> : null}
              {statisticOptions.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <div className="mt-6 flex flex-wrap items-center gap-3 text-sm font-semibold">
            <span className="rounded-xl bg-teal-100 px-3 py-2 text-teal-700">Tong may: {rows.length}</span>
            <span className="rounded-xl bg-emerald-100 px-3 py-2 text-emerald-700">Online: {totalOnline}</span>
            <span className="rounded-xl bg-slate-200 px-3 py-2 text-slate-700">Offline: {rows.length - totalOnline}</span>
            <span
              className={`rounded-xl px-3 py-2 ${
                wsStatus === 'connected'
                  ? 'bg-emerald-100 text-emerald-700'
                  : wsStatus === 'connecting'
                    ? 'bg-amber-100 text-amber-700'
                    : 'bg-rose-100 text-rose-700'
              }`}
            >
              WS: {wsStatus}
            </span>
            <button
              className="rounded-xl bg-orange-500 px-4 py-2 text-white transition hover:bg-orange-600"
              onClick={() => void loadData()}
              type="button"
            >
              Refresh HTTP
            </button>
          </div>
        </header>

        <section className="mb-8 grid gap-4 lg:grid-cols-2">
          <MetricChart
            title="CPU theo lich su database"
            values={cpuSeries}
            labels={timeLabels}
            colorClass="bg-emerald-100 text-emerald-700"
            maxValue={100}
            unit="%"
          />
          <MetricChart
            title="RAM theo lich su database"
            values={ramSeries}
            labels={timeLabels}
            colorClass="bg-sky-100 text-sky-700"
            maxValue={ramMax}
            unit="%"
          />
        </section>

        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          {loading ? (
            <div className="p-6 text-sm text-slate-600">Dang tai du lieu...</div>
          ) : error ? (
            <div className="p-6 text-sm font-semibold text-red-600">{error}</div>
          ) : rows.length === 0 ? (
            <div className="p-6 text-sm text-slate-600">Backend chua co du lieu logs.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-600">
                  <tr>
                    <th className="px-4 py-3">Time</th>
                    <th className="px-4 py-3">Name</th>
                    <th className="px-4 py-3">IP</th>
                    <th className="px-4 py-3">IP WAN</th>
                    <th className="px-4 py-3">Port</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Ping</th>
                    <th className="px-4 py-3">CPU</th>
                    <th className="px-4 py-3">RAM</th>
                    <th className="px-4 py-3">Resolution</th>
                    <th className="px-4 py-3">SRT Quality</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((item, index) => {
                    const isOnline = item.data.status?.toUpperCase() === 'ONLINE'
                    return (
                      <tr className="border-t border-slate-100" key={`${item.data.name}-${item.data.port}-${index}`}>
                        <td className="px-4 py-3 text-slate-600">{item.timestamp || '-'}</td>
                        <td className="px-4 py-3 font-semibold text-slate-900">{item.data.name || '-'}</td>
                        <td className="px-4 py-3">{item.data.ip || '-'}</td>
                        <td className="px-4 py-3">{item.data.ipwan || '-'}</td>
                        <td className="px-4 py-3">{item.data.port || '-'}</td>
                        <td className="px-4 py-3">
                          <span
                            className={`rounded-full px-2 py-1 text-xs font-semibold ${
                              isOnline ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'
                            }`}
                          >
                            {item.data.status || 'UNKNOWN'}
                          </span>
                        </td>
                        <td className="px-4 py-3">{item.data.ping ?? '-'}</td>
                        <td className="px-4 py-3">{item.data.cpu ?? '-'}</td>
                        <td className="px-4 py-3">{item.data.memory ?? '-'}</td>
                        <td className="px-4 py-3">{item.data.resolution || '-'}</td>
                        <td className="px-4 py-3">{item.data.srt_quality || '-'}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <footer className="mt-8 text-center text-xs font-medium uppercase tracking-widest text-slate-500">
          Built for ToolDiscordVmix
        </footer>
      </div>
    </div>
  )
}

export default App

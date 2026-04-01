import { useCallback, useMemo, useState } from 'react'
import { toNumber } from '../../types'
import {
  normalizeSrtList,
  normalizeStreamList,
  type BackendLogItem,
  type BackendSrtItem,
  type BackendStreamItem,
} from '../../services/api'
import Dialog from '../../components/ui/Dialog'
import { renderSrtCard, renderStreamCard, toOnOff } from '../../components/DialogHelpers'

/* ─── Helpers ─── */

/** Determine if a value looks boolean-ish for pill display */
function isBooleanish(value: unknown): boolean {
  const text = String(value ?? '').toUpperCase()
  return ['ONLINE', 'OFFLINE', 'ON', 'OFF', '1', '0', 'TRUE', 'FALSE',
    'RUNNING', 'STOPPED', 'LIVE', 'ACTIVE', 'INACTIVE'].includes(text)
}

function formatNumber(value: unknown, decimals = 2): string {
  const parsed = toNumber(value)
  return parsed === null ? '-' : parsed.toFixed(decimals)
}

/* ─── Dynamic column builder ─── */

const PRIORITY_KEYS = [
  'name', 'ip', 'ipwan', 'status', 'port', 'statusapp',
  'ping', 'ping_timeouts', 'cpu', 'temperature', 'memory', 'ram', 'gpu',
  'sender_mbps', 'receiver_mbps',
  'vmix_recording', 'vmix_streaming', 'vmix_external',
  'resolution', 'srt_quality', 'srt_off_time',
]

/** Keys to exclude from table columns (shown in dialog instead) */
const DIALOG_ONLY_KEYS = new Set(['SRT', 'stream'])

interface ColumnDef {
  key: string
  label: string
  isNested: boolean
}

function buildColumns(rows: BackendLogItem[]): ColumnDef[] {
  const seenKeys = new Set<string>()
  for (const row of rows) {
    if (row.data && typeof row.data === 'object') {
      for (const key of Object.keys(row.data)) {
        seenKeys.add(key)
      }
    }
  }

  const columns: ColumnDef[] = []
  const added = new Set<string>()

  for (const key of PRIORITY_KEYS) {
    if (seenKeys.has(key) && !DIALOG_ONLY_KEYS.has(key)) {
      columns.push({ key, label: key, isNested: false })
      added.add(key)
    }
  }

  const remaining = Array.from(seenKeys)
    .filter((k) => !added.has(k) && !DIALOG_ONLY_KEYS.has(k))
    .sort()

  for (const key of remaining) {
    const dataRecord = rows.find((row) => (row.data as Record<string, unknown>)[key] !== undefined)?.data as Record<string, unknown> | undefined
    const val = dataRecord?.[key]
    const isNested = val !== null && typeof val === 'object'
    columns.push({ key, label: key, isNested })
    added.add(key)
  }

  return columns
}

function renderCellValue(col: ColumnDef, item: BackendLogItem) {
  const raw = (item.data as Record<string, unknown>)[col.key]

  if (col.isNested && raw !== null && typeof raw === 'object') {
    return (
      <span className="mono" style={{ fontSize: '0.65rem', color: '#64748b' }}>
        {JSON.stringify(raw).slice(0, 60)}…
      </span>
    )
  }

  if (col.key === 'statusapp') {
    const on = Number(raw ?? 0) === 1
    return <span className={`status-pill ${on ? 'pill-on' : 'pill-off'}`}>{on ? 'ON' : 'OFF'}</span>
  }

  if (isBooleanish(raw)) {
    const text = toOnOff(raw)
    return <span className={`status-pill ${text === 'ON' ? 'pill-on' : 'pill-off'}`}>{text}</span>
  }

  const metricKeys = ['cpu', 'temperature', 'memory', 'ram', 'gpu']
  if (metricKeys.includes(col.key)) {
    const val = toNumber(raw)
    const isHigh = val !== null && val > 50
    return <span className={isHigh ? 'metric-danger bold' : ''}>{formatNumber(raw)}%</span>
  }

  if (col.key === 'sender_mbps' || col.key === 'receiver_mbps') {
    const v = toNumber(raw)
    if (v === null) return '-'
    const showV = (v > 0.02) ? v : 0
    return <>{showV.toFixed(2)} Mbps</>
  }

  if (col.key === 'ping') {
    return <>{String(raw ?? '-')}</>
  }

  const text = String(raw ?? '').trim() || '-'
  const monoKeys = ['ip', 'ipwan', 'port', 'srt_off_time']
  return <span className={monoKeys.includes(col.key) ? 'mono' : ''}>{text}</span>
}

/* ─── Dialog content types ─── */
type DialogInfo =
  | { type: 'srt'; machineName: string; srtList: BackendSrtItem[] }
  | { type: 'stream'; machineName: string; streamList: BackendStreamItem[] }

/* ─── Component ─── */

export default function StatusByTablePage({
  rows,
  loading,
  error,
}: {
  rows: BackendLogItem[]
  loading: boolean
  error: string
}) {
  const columns = useMemo(() => buildColumns(rows), [rows])
  const [dialogInfo, setDialogInfo] = useState<DialogInfo | null>(null)

  const openSrt = useCallback((item: BackendLogItem) => {
    setDialogInfo({
      type: 'srt',
      machineName: item.data.name || 'Unknown',
      srtList: normalizeSrtList(item.data.SRT),
    })
  }, [])

  const openStream = useCallback((item: BackendLogItem) => {
    setDialogInfo({
      type: 'stream',
      machineName: item.data.name || 'Unknown',
      streamList: normalizeStreamList(item.data.stream),
    })
  }, [])

  const closeDialog = useCallback(() => setDialogInfo(null), [])

  // Check if any row has SRT or stream data
  const hasSrt = rows.some((r) => normalizeSrtList(r.data.SRT).length > 0)
  const hasStream = rows.some((r) => normalizeStreamList(r.data.stream).length > 0)
  const hasActions = hasSrt || hasStream || true // always show actions column

  if (loading) {
    return (
      <div className="status-cards-grid">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={`table-skeleton-${i}`} className="glass-card skeleton-card shimmer-loading" />
        ))}
      </div>
    )
  }

  if (error) {
    return <div className="glass-card error-card">{error}</div>
  }

  if (rows.length === 0) {
    return <div className="glass-card empty-card">Chưa có dữ liệu từ backend.</div>
  }

  return (
    <>
      <div className="status-table-wrap glass-card">
        <div className="status-table-toolbar">
          <div className="status-table-title">Full Response Table</div>
        </div>
        <div className="status-table-scroll-shell">
          <div className="status-table-scroll">
            <table className="status-table">
            <thead>
              <tr>
                <th>#</th>
                <th>timestamp</th>
                {columns.map((col) => (
                  <th key={col.key}>{col.label}</th>
                ))}
                {hasActions && <th>Thao tác</th>}
              </tr>
            </thead>
            <tbody>
              {rows.map((item, index) => {
                const srtList = normalizeSrtList(item.data.SRT)
                const streamList = normalizeStreamList(item.data.stream)

                const c = toNumber(item.data.temperature) ?? 0
                const r = toNumber(item.data.memory) ?? 0
                const g = toNumber(item.data.gpu) ?? 0
                const isOverload = (c > 50 || r > 50 || g > 50)

                return (
                  <tr
                    key={`${item.data.name || 'machine'}-${item.data.ip || 'ip'}-${index}`}
                    className={isOverload ? 'row-overload' : ''}
                  >
                    <td className="status-table-index">{index + 1}</td>
                    <td className="mono" style={{ whiteSpace: 'nowrap' }}>{item.timestamp || '-'}</td>
                    {columns.map((col) => (
                      <td key={col.key}>
                        {renderCellValue(col, item)}
                      </td>
                    ))}
                    {hasActions && (
                      <td>
                        <div className="table-actions">
                          <button
                            type="button"
                            className="table-action-btn table-action-srt"
                            onClick={() => openSrt(item)}
                            title="Xem chi tiết SRT"
                          >
                            SRT FULL ({srtList.length})
                          </button>
                          <button
                            type="button"
                            className="table-action-btn table-action-stream"
                            onClick={() => openStream(item)}
                            title="Xem chi tiết Stream"
                          >
                            STREAM FULL ({streamList.length})
                          </button>
                        </div>
                      </td>
                    )}
                  </tr>
                )
              })}
            </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* SRT Detail Dialog */}
      <Dialog
        open={dialogInfo?.type === 'srt'}
        onClose={closeDialog}
        title={`SRT — ${dialogInfo?.type === 'srt' ? dialogInfo.machineName : ''}`}
      >
        {dialogInfo?.type === 'srt' && (
          dialogInfo.srtList.length > 0 ? (
            <div className="dialog-detail-grid">
              {dialogInfo.srtList.map(renderSrtCard)}
            </div>
          ) : (
            <div className="dialog-empty-state">Không có dữ liệu SRT cho máy này.</div>
          )
        )}
      </Dialog>

      {/* Stream Detail Dialog */}
      <Dialog
        open={dialogInfo?.type === 'stream'}
        onClose={closeDialog}
        title={`Stream — ${dialogInfo?.type === 'stream' ? dialogInfo.machineName : ''}`}
      >
        {dialogInfo?.type === 'stream' && (
          dialogInfo.streamList.length > 0 ? (
            <div className="dialog-detail-grid">
              {dialogInfo.streamList.map(renderStreamCard)}
            </div>
          ) : (
            <div className="dialog-empty-state">Không có dữ liệu Stream cho máy này.</div>
          )
        )}
      </Dialog>
    </>
  )
}

import { useState } from 'react'
import { toNumber } from '../../types'
import {
  normalizeSrtList,
  normalizeStreamList,
  normalizeFfmpegList,
  normalizeRecordList,
  normalizeMultiRecordList,
  getMachineStatisticsId,
  type BackendLogItem,
} from '../../services/api'
import Dialog from '../../components/ui/Dialog'
import { renderSrtCard, renderStreamCard, renderRecordCard, renderMultiRecordCard } from '../../components/DialogHelpers'


function toOnOff(value: unknown): string {
  const text = String(value || '').toUpperCase()
  if (['ONLINE', 'ON', '1', 'TRUE', 'RUNNING', 'LIVE', 'ACTIVE'].includes(text)) return 'ON'
  if (['OFFLINE', 'OFF', '0', 'FALSE', 'STOPPED', 'INACTIVE', 'BAD', 'ERROR'].includes(text)) return 'OFF'
  return text || '-'
}

function formatNumber(value: unknown, decimals = 2): string {
  const parsed = toNumber(value)
  return parsed === null ? '-' : parsed.toFixed(decimals)
}

export default function StatusByTablePage({
  rows,
  loading,
  error,
}: {
  rows: BackendLogItem[]
  loading: boolean
  error: string
}) {
  const [dialogState, setDialogState] = useState<{
    type: 'srt' | 'stream' | 'ffmpeg' | 'record' | null
    machineIndex: number
  }>({ type: null, machineIndex: -1 })


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

  const currentItem = dialogState.machineIndex >= 0 ? rows[dialogState.machineIndex] : null
  const currentSrtList = currentItem ? normalizeSrtList(currentItem.data.SRT) : []
  const currentStreamList = currentItem ? normalizeStreamList(currentItem.data.stream) : []
  const currentFfmpegList = currentItem ? normalizeFfmpegList(currentItem.data.ffmpeg) : []
  const currentRecordList = currentItem ? normalizeRecordList(currentItem.data.List_REcord) : []
  const currentMultiRecordList = currentItem ? normalizeMultiRecordList(currentItem.data.ListMultiREcord || (currentItem.data as any).ListMultiRecord) : []


  return (
    <>
      <div className="status-table-wrap glass-card">
        <div className="status-table-toolbar">
          <div className="status-table-title">Bảng tổng hợp</div>
          <div className="status-table-meta">{rows.length} máy</div>
        </div>
        <div className="status-table-scroll-hint">Cuộn ngang để xem đầy đủ cột · giữ Shift + lăn chuột để cuộn nhanh</div>
        <div className="status-table-scroll-shell">
          <div className="status-table-scroll">
            <table className="status-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Máy</th>
                  <th>timestamp</th>
                  <th>IP</th>
                  <th>WAN</th>
                  <th>status</th>
                  <th>port</th>
                  <th>APP</th>
                  <th>ping</th>
                  <th>Ping ISP</th>
                  <th>ping_timeouts</th>
                  <th>CPU</th>
                  <th>RAM</th>
                  <th>GPU</th>
                  <th>Sender</th>
                  <th>Receiver</th>
                  <th>MAC</th>
                  <th>Net Speed</th>
                  <th>REC</th>
                  <th>MULTI</th>
                  <th>LIVE</th>
                  <th>EXT</th>
                  <th>Resolution</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((item, index) => {
                  const srtList = normalizeSrtList(item.data.SRT)
                  const streamList = normalizeStreamList(item.data.stream)
                  const ffmpegList = normalizeFfmpegList(item.data.ffmpeg)
                  const recordList = normalizeRecordList(item.data.List_REcord)
                  const multiRecordList = normalizeMultiRecordList(item.data.ListMultiREcord || (item.data as any).ListMultiRecord)
                  const primaryPort = String(item.data.port || srtList[0]?.port || '-')


                  const machineId = getMachineStatisticsId(item) || `${item.data.ip || 'no-ip'}-${item.data.name || 'no-name'}`
                  return (
                    <tr key={`row-${machineId}`} className={index % 2 === 0 ? '' : 'row-alt'}>
                      <td className="status-table-index">{index + 1}</td>
                      <td className="status-table-main-cell">
                        <div className="status-table-machine">{item.data.name || 'Unknown'}</div>
                      </td>
                      <td className="mono">{item.timestamp || '-'}</td>
                      <td className="mono">{item.data.ip || '-'}</td>
                      <td className="mono">{item.data.ipwan || '-'}</td>
                      <td>{toOnOff(item.data.status)}</td>
                      <td className="mono">{primaryPort}</td>
                      <td>
                        <span className={`status-pill ${Number(item.data.statusapp ?? 0) === 1 ? 'pill-on' : 'pill-off'}`}>
                          {Number(item.data.statusapp ?? 0) === 1 ? 'ON' : 'OFF'}
                        </span>
                      </td>
                      <td>{String(item.data.ping ?? '-')}</td>
                      <td>{String(item.data.ping_isp ?? '-')}</td>
                      <td>{String(item.data.ping_timeouts ?? 0)}</td>
                      <td>{formatNumber(item.data.temperature ?? item.data.cpu)}%</td>
                      <td>{formatNumber(item.data.memory ?? item.data.ram)}%</td>
                      <td>{formatNumber(item.data.gpu)}%</td>
                      <td>{formatNumber(item.data.sender_mbps, 3)} Mbps</td>
                      <td>{formatNumber(item.data.receiver_mbps, 3)} Mbps</td>
                      <td className="mono">{item.data.mac_address || '-'}</td>
                      <td>{item.data.network_speed || '-'}</td>
                      <td>
                        <span className={`status-pill ${toOnOff(item.data.vmix_recording) === 'ON' ? 'pill-on' : 'pill-off'}`}>
                          {toOnOff(item.data.vmix_recording)}
                        </span>
                      </td>
                      <td>
                        <span className={`status-pill ${toOnOff(item.data.vmix_multicorder || item.data.MultirecordingStatus) === 'ON' ? 'pill-on' : 'pill-off'}`}>
                          {toOnOff(item.data.vmix_multicorder || item.data.MultirecordingStatus)}
                        </span>
                      </td>
                      <td>
                        <span className={`status-pill ${toOnOff(item.data.vmix_streaming) === 'ON' ? 'pill-on' : 'pill-off'}`}>
                          {toOnOff(item.data.vmix_streaming)}
                        </span>
                      </td>
                      <td>
                        <span className={`status-pill ${toOnOff(item.data.vmix_external) === 'ON' ? 'pill-on' : 'pill-off'}`}>
                          {toOnOff(item.data.vmix_external)}
                        </span>
                      </td>
                      <td>{item.data.resolution || '-'}</td>
                      <td className="status-table-actions">
                        <button
                          type="button"
                          className="card-footer-btn"
                          onClick={() => setDialogState({ type: 'srt', machineIndex: index })}
                          disabled={srtList.length === 0}
                          title={srtList.length === 0 ? 'No SRT data' : 'View SRT details'}
                        >
                          SRT ({srtList.length})
                        </button>
                        <button
                          type="button"
                          className="card-footer-btn"
                          onClick={() => setDialogState({ type: 'record', machineIndex: index })}
                          disabled={recordList.length === 0 && multiRecordList.length === 0}
                          title={recordList.length === 0 && multiRecordList.length === 0 ? 'No Record data' : 'View Record details'}
                        >
                          Record ({recordList.length + multiRecordList.length})
                        </button>
                        <button
                          type="button"
                          className="card-footer-btn"
                          onClick={() => setDialogState({ type: 'stream', machineIndex: index })}
                          disabled={streamList.length === 0}
                          title={streamList.length === 0 ? 'No Stream data' : 'View Stream details'}
                        >
                          Stream ({streamList.length})
                        </button>
                        <button
                          type="button"
                          className="card-footer-btn"
                          onClick={() => setDialogState({ type: 'ffmpeg', machineIndex: index })}
                          disabled={ffmpegList.length === 0}
                          title={ffmpegList.length === 0 ? 'No FFmpeg data' : 'View FFmpeg details'}
                        >
                          FFmpeg ({ffmpegList.length})
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* SRT Dialog */}
      <Dialog
        open={dialogState.type === 'srt' && currentItem !== null}
        onClose={() => setDialogState({ type: null, machineIndex: -1 })}
        title={`SRT · ${currentItem?.data.name || 'Unknown'}`}
      >
        {currentSrtList.length > 0 ? (
          <div className="dialog-detail-grid">
            {currentSrtList.map(renderSrtCard)}
          </div>
        ) : (
          <div className="dialog-empty-state">Không có dữ liệu SRT.</div>
        )}
      </Dialog>

      {/* Stream Dialog */}
      <Dialog
        open={dialogState.type === 'stream' && currentItem !== null}
        onClose={() => setDialogState({ type: null, machineIndex: -1 })}
        title={`Stream · ${currentItem?.data.name || 'Unknown'}`}
      >
        {currentStreamList.length > 0 ? (
          <div className="dialog-detail-grid">
            {currentStreamList.map((stream, idx) => renderStreamCard(stream, idx))}
          </div>
        ) : (
          <div className="dialog-empty-state">Không có dữ liệu stream.</div>
        )}
      </Dialog>

      {/* FFmpeg Dialog */}
      <Dialog
        open={dialogState.type === 'ffmpeg' && currentItem !== null}
        onClose={() => setDialogState({ type: null, machineIndex: -1 })}
        title={`FFmpeg · ${currentItem?.data.name || 'Unknown'}`}
      >
        {currentFfmpegList.length > 0 ? (
          <div className="dialog-detail-grid">
            {currentFfmpegList.map((ffmpegItem, idx) => (
              <div key={`ffmpeg-${idx}`} className="dialog-detail-card">
                <div className="dialog-detail-card-header">
                  <span className="dialog-detail-card-title">FFmpeg {idx + 1}</span>
                </div>
                <div className="dialog-detail-row">
                  <span className="dialog-detail-key">Name</span>
                  <span className="dialog-detail-value">{String(ffmpegItem.name ?? '-')}</span>
                </div>
                <div className="dialog-detail-row">
                  <span className="dialog-detail-key">PID</span>
                  <span className="dialog-detail-value mono">{String(ffmpegItem.pid ?? '-')}</span>
                </div>
                <div className="dialog-detail-row">
                  <span className="dialog-detail-key">Send</span>
                  <span className="dialog-detail-value">{String(ffmpegItem.send ?? '-')}</span>
                </div>
                <div className="dialog-detail-row">
                  <span className="dialog-detail-key">Recv</span>
                  <span className="dialog-detail-value">{String(ffmpegItem.recv ?? '-')}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="dialog-empty-state">Không có dữ liệu FFmpeg.</div>
        )}
      </Dialog>

      {/* Record Dialog */}
      <Dialog
        open={dialogState.type === 'record' && currentItem !== null}
        onClose={() => setDialogState({ type: null, machineIndex: -1 })}
        title={`Record & MultiCorder · ${currentItem?.data.name || 'Unknown'}`}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div>
            <h4 style={{ fontSize: '0.95rem', fontWeight: 800, marginBottom: '0.5rem', textTransform: 'uppercase', color: '#94a3b8', borderBottom: '1px solid rgba(148, 163, 184, 0.1)', paddingBottom: '0.25rem' }}>
              Standard Record ({currentRecordList.length})
            </h4>
            {currentRecordList.length > 0 ? (
              <div className="dialog-detail-grid">
                {currentRecordList.map(renderRecordCard)}
              </div>
            ) : (
              <div className="dialog-empty-state">Không có dữ liệu Standard Record.</div>
            )}
          </div>
          <div>
            <h4 style={{ fontSize: '0.95rem', fontWeight: 800, marginBottom: '0.5rem', textTransform: 'uppercase', color: '#94a3b8', borderBottom: '1px solid rgba(148, 163, 184, 0.1)', paddingBottom: '0.25rem' }}>
              MultiCorder ({currentMultiRecordList.length})
            </h4>
            {currentMultiRecordList.length > 0 ? (
              <div className="dialog-detail-grid">
                {currentMultiRecordList.map(renderMultiRecordCard)}
              </div>
            ) : (
              <div className="dialog-empty-state">Không có dữ liệu MultiCorder.</div>
            )}
          </div>
        </div>
      </Dialog>
    </>
  )
}

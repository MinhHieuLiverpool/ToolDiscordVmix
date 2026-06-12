import type { BackendSrtItem, BackendStreamItem, BackendStreamKeyItem } from '../services/api'

export function toOnOff(value: unknown): string {
    const text = String(value || '').toUpperCase()
    if (['ONLINE', 'ON', '1', 'TRUE', 'RUNNING', 'LIVE', 'ACTIVE'].includes(text)) return 'ON'
    if (['OFFLINE', 'OFF', '0', 'FALSE', 'STOPPED', 'INACTIVE', 'BAD', 'ERROR'].includes(text)) return 'OFF'
    return text || '-'
}

export function renderDetailLine(label: string, value: unknown, mono = false) {
    const text = String(value ?? '').trim() || '-'
    return (
        <div className="dialog-detail-row" key={label}>
            <span className="dialog-detail-key">{label}</span>
            <span className={`dialog-detail-value ${mono ? 'mono' : ''}`}>{text}</span>
        </div>
    )
}

function formatNumber(value: number) {
    if (value >= 100) return value.toFixed(0)
    if (value >= 10) return value.toFixed(1)
    return value.toFixed(2)
}

export function formatBitrate(value: unknown): string {
    const raw = String(value ?? '').trim()
    if (!raw) return '-'

    const normalized = raw.toLowerCase().replace(/\s+/g, '')
    const match = normalized.match(/^([\d.]+)([a-z]+)?$/)
    if (!match) return raw

    const num = Number(match[1])
    const unit = match[2] || ''
    if (!Number.isFinite(num)) return raw

    if (unit === 'kbps' || unit === 'k') {
        return num >= 1000 ? `${formatNumber(num / 1000)} Mbps` : `${formatNumber(num)} kbps`
    }
    if (unit === 'mbps' || unit === 'm') {
        return `${formatNumber(num)} Mbps`
    }
    if (unit === 'bps') {
        return `${formatNumber(num / 1_000_000)} Mbps`
    }

    return num >= 1000 ? `${formatNumber(num / 1000)} Mbps` : `${formatNumber(num)} kbps`
}

export function renderTypePill(type: string | undefined) {
    const text = String(type || '').trim()
    if (!text || text === '-') return '-'
    const isCaller = text.toLowerCase() === 'caller'
    const isListener = text.toLowerCase() === 'listener'

    if (isCaller) {
        return <span className="pill-light pill-caller">Caller</span>
    }
    if (isListener) {
        return <span className="pill-light pill-listener">Listener</span>
    }
    return <span className="pill-light" style={{ background: 'rgba(100,116,139,0.1)', color: '#64748b' }}>{text}</span>
}

export function renderTitlePill(title: string | undefined) {
    const text = String(title || '').trim()
    if (!text || text === '-') return '-'

    let colorClass = ''
    if (text === 'OutputsExternal') colorClass = 'pill-external-1'
    else if (text === 'OutputsExternal2') colorClass = 'pill-external-2'
    else if (text === 'OutputsExternal3') colorClass = 'pill-external-3'
    else if (text === 'OutputsExternal4') colorClass = 'pill-external-4'

    return <span className={`pill-light ${colorClass}`}>{text}</span>
}

export function renderSrtCard(srt: BackendSrtItem, index: number) {
    const statusText = toOnOff(srt.status)
    return (
        <div key={`srt-${index}`} className="dialog-detail-card">
            <div className="dialog-detail-card-header">
                <span className="dialog-detail-card-title">{srt.title ? renderTitlePill(srt.title) : (srt.nameSRT || `SRT ${index + 1}`)}</span>
                <span className={`status-pill ${statusText === 'ON' ? 'pill-on' : 'pill-off'}`}>{statusText}</span>
            </div>
            {srt.title && renderDetailLine('Tên SRT', srt.nameSRT)}
            {renderDetailLine('Port', srt.port, true)}
            <div className="dialog-detail-row">
                <span className="dialog-detail-key">Type</span>
                <span className="dialog-detail-value">{renderTypePill(srt.type)}</span>
            </div>
            {renderDetailLine('Host', srt.hostname)}
            {renderDetailLine('Stream ID', srt.stream_id, true)}
            {renderDetailLine('Quality', srt.quality)}
        </div>
    )
}

export function renderStreamCard(stream: BackendStreamItem, index: number, streamKey?: BackendStreamKeyItem) {
    const runtimeText = toOnOff(stream.runtime)
    const healthText = String(stream.health || '-').toUpperCase()
    const urlText = streamKey?.url || '-'
    const keyText = streamKey?.key || '-'
    const hasUrl = urlText !== '-' && urlText !== '(trong)'
    const hasKey = keyText !== '-' && keyText !== '' && keyText !== '(trong)'

    return (
        <div key={`stream-${index}`} className="dialog-detail-card">
            <div className="dialog-detail-card-header">
                <span className="dialog-detail-card-title">{stream.stream || `Stream ${index + 1}`}</span>
                <span className={`status-pill ${runtimeText === 'ON' ? 'pill-on' : 'pill-off'}`}>{runtimeText}</span>
            </div>
            {hasUrl && renderDetailLine('URL', urlText, true)}
            {hasKey && renderDetailLine('Stream Key', keyText, true)}
            {renderDetailLine('Health', healthText)}
            {renderDetailLine('Video Bitrate', formatBitrate(stream.vbit))}
            {renderDetailLine('Size', stream.size)}
            {renderDetailLine('Audio Bitrate', formatBitrate(stream.abit))}
            {renderDetailLine('Level', stream.level)}
            {renderDetailLine('Preset', stream.preset)}
            {renderDetailLine('Audio Format', stream.aformat)}
            {renderDetailLine('Channels', stream.channels)}
            {renderDetailLine('Keyframe', stream.keyframe)}
            {renderDetailLine('Actual', stream.actual)}
            {renderDetailLine('Target', stream.target)}
            {renderDetailLine('Ratio', stream.ratio)}
            {renderDetailLine('Speed', stream.speed)}
            {renderDetailLine('Dropped', stream.dropped)}
            {renderDetailLine('File', stream.file, true)}
        </div>
    )
}

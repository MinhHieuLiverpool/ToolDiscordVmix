import type { BackendSrtItem, BackendStreamItem } from '../services/api'

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

export function renderSrtCard(srt: BackendSrtItem, index: number) {
    const statusText = toOnOff(srt.status)
    return (
        <div key={`srt-${index}`} className="dialog-detail-card">
            <div className="dialog-detail-card-header">
                <span className="dialog-detail-card-title">{srt.nameSRT || `SRT ${index + 1}`}</span>
                <span className={`status-pill ${statusText === 'ON' ? 'pill-on' : 'pill-off'}`}>{statusText}</span>
            </div>
            {renderDetailLine('Port', srt.port, true)}
            {renderDetailLine('Quality', srt.quality)}
        </div>
    )
}

export function renderStreamCard(stream: BackendStreamItem, index: number) {
    const runtimeText = toOnOff(stream.runtime)
    const healthText = String(stream.health || '-').toUpperCase()
    return (
        <div key={`stream-${index}`} className="dialog-detail-card">
            <div className="dialog-detail-card-header">
                <span className="dialog-detail-card-title">{stream.stream || `Stream ${index + 1}`}</span>
                <span className={`status-pill ${runtimeText === 'ON' ? 'pill-on' : 'pill-off'}`}>{runtimeText}</span>
            </div>
            {renderDetailLine('Health', healthText)}
            {renderDetailLine('Video Bitrate', stream.vbit)}
            {renderDetailLine('Size', stream.size)}
            {renderDetailLine('Audio Bitrate', stream.abit)}
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

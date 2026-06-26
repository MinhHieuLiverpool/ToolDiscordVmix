import { useState } from 'react'
import type { BackendSrtItem, BackendStreamItem, BackendStreamKeyItem, RecordItem, MultiRecordItem } from '../services/api'

export function toOnOff(value: unknown): string {
    const text = String(value || '').toUpperCase()
    if (['ONLINE', 'ON', '1', 'TRUE', 'RUNNING', 'LIVE', 'ACTIVE'].includes(text)) return 'ON'
    if (['OFFLINE', 'OFF', '0', 'FALSE', 'STOPPED', 'INACTIVE', 'BAD', 'ERROR'].includes(text)) return 'OFF'
    return text || '-'
}

export function CopyButton({ text }: { text: string }) {
    const [copied, setCopied] = useState(false)

    const handleCopy = async (e: React.MouseEvent) => {
        e.stopPropagation()
        try {
            await navigator.clipboard.writeText(text)
            setCopied(true)
            setTimeout(() => setCopied(false), 2000)
        } catch (err) {
            console.error('Failed to copy text: ', err)
        }
    }

    return (
        <button
            type="button"
            className={`copy-btn ${copied ? 'copied' : ''}`}
            onClick={handleCopy}
            title={copied ? 'Đã copy!' : 'Copy'}
            style={{
                background: 'rgba(148, 163, 184, 0.1)',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                padding: '4px',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: copied ? '#10b981' : '#94a3b8',
                transition: 'all 0.2s',
                marginLeft: '6px',
                verticalAlign: 'middle',
                flexShrink: 0,
            }}
        >
            {copied ? (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ width: 12, height: 12 }}>
                    <polyline points="20 6 9 17 4 12" />
                </svg>
            ) : (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: 12, height: 12 }}>
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                </svg>
            )}
        </button>
    )
}

export function renderDetailLine(label: string, value: unknown, mono = false, copyable = false) {
    const text = String(value ?? '').trim() || '-'
    const showCopy = copyable && text !== '-' && text !== ''
    return (
        <div className="dialog-detail-row" key={label}>
            <span className="dialog-detail-key">{label}</span>
            <span 
                className={`dialog-detail-value ${mono ? 'mono' : ''}`}
                style={showCopy ? { display: 'inline-flex', alignItems: 'center', gap: '4px', justifyContent: 'flex-end', width: '100%', maxWidth: '70%' } : undefined}
            >
                <span style={showCopy ? { wordBreak: 'break-all', textAlign: 'right' } : undefined}>{text}</span>
                {showCopy && <CopyButton text={text} />}
            </span>
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
            {hasUrl && renderDetailLine('URL', urlText, true, true)}
            {hasKey && renderDetailLine('Stream Key', keyText, true, true)}
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

export function renderRecordCard(record: RecordItem, index: number) {
    return (
        <div key={`record-${index}`} className="dialog-detail-card">
            <div className="dialog-detail-card-header">
                <span className="dialog-detail-card-title">{record.profile || `Profile ${index + 1}`}</span>
                <span className="pill-light" style={{ background: 'rgba(124, 58, 237, 0.1)', color: '#7c3aed', fontWeight: 600 }}>Standard</span>
            </div>
            {renderDetailLine('Filename', record.filename, true, true)}
            {renderDetailLine('Format', record.format)}
            {renderDetailLine('Resolution', record.resolution)}
            {renderDetailLine('FPS', record.fps)}
            {renderDetailLine('Video Bitrate', formatBitrate(record.v_bitrate))}
            {renderDetailLine('Audio Bitrate', formatBitrate(record.a_bitrate))}
            {renderDetailLine('Audio Delay', record.audio_delay)}
            {record.hw_accel && renderDetailLine('HW Accel', record.hw_accel)}
            {record.audio_enabled && renderDetailLine('Audio', record.audio_enabled)}
            {record.audio_channel && renderDetailLine('Audio Ch', record.audio_channel)}
            {record.source_channel && renderDetailLine('Source Ch', record.source_channel)}
            {record.fragmented && renderDetailLine('Fragmented', record.fragmented)}
        </div>
    )
}

export function renderMultiRecordCard(mRecord: MultiRecordItem, index: number) {
    const statusText = toOnOff(mRecord.status)
    return (
        <div key={`multirecord-${index}`} className="dialog-detail-card">
            <div className="dialog-detail-card-header">
                <span className="dialog-detail-card-title">{mRecord.source || `Source ${index + 1}`}</span>
                <span className={`status-pill ${statusText === 'ON' ? 'pill-on' : 'pill-off'}`}>{statusText}</span>
            </div>
            {renderDetailLine('Folder', mRecord.folder, true, true)}
            {renderDetailLine('Format', mRecord.format)}
            {renderDetailLine('Video Bitrate', formatBitrate(mRecord.v_bitrate))}
            {renderDetailLine('Audio Bitrate', formatBitrate(mRecord.a_bitrate))}
            {mRecord.audio_src && renderDetailLine('Audio Source', mRecord.audio_src)}
            {mRecord.interval && renderDetailLine('Interval', mRecord.interval)}
            {mRecord.show_all && renderDetailLine('Show All', mRecord.show_all)}
        </div>
    )
}


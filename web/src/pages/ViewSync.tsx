import { useEffect, useMemo, useState } from 'react'
import { hasActionPermission } from '../services/auth'
import { useLanguage } from '../config/i18n'

type VideoItem = {
    id: string
    url: string
    title: string
    startTime: number
}

type LayoutOption = {
    id: string
    name: string
    max: number
    columns: number
    rows: number
    spans?: Record<number, { gridColumn?: string; gridRow?: string }>
}

const LAYOUTS: LayoutOption[] = [
    { id: 'l1', name: '1 x 1', max: 1, columns: 1, rows: 1 },
    { id: 'l2', name: '1 x 2', max: 2, columns: 2, rows: 1 },
    { id: 'l3', name: 'Master + 2', max: 3, columns: 2, rows: 2, spans: { 0: { gridRow: 'span 2' } } },
    { id: 'l4', name: '2 x 2', max: 4, columns: 2, rows: 2 },
    { id: 'l5', name: '2 + 3', max: 5, columns: 3, rows: 2, spans: { 0: { gridColumn: 'span 2' } } },
    { id: 'l6', name: '3 x 2', max: 6, columns: 3, rows: 2 },
    { id: 'l7', name: '4 x 2', max: 8, columns: 4, rows: 2 },
    { id: 'l8', name: '3 x 3', max: 9, columns: 3, rows: 3 },
    { id: 'l9', name: '4 x 3', max: 10, columns: 4, rows: 3 },
]

function formatTime(seconds: number) {
    const safeSeconds = Number.isFinite(seconds) ? Math.max(0, Math.floor(seconds)) : 0
    const minutes = Math.floor(safeSeconds / 60)
    const remain = String(safeSeconds % 60).padStart(2, '0')
    return `${String(minutes).padStart(2, '0')}:${remain}`
}

function buildParams(videos: VideoItem[], layout: string) {
    const params = new URLSearchParams()
    videos.forEach((video, index) => {
        params.append(`video${index}`, video.url)
        params.append(`start${index}`, String(video.startTime))
    })
    params.set('layout', layout)
    return params
}

function buildShareUrl(videos: VideoItem[]) {
    const params = buildParams(videos, 'auto')
    return `${window.location.origin}${window.location.pathname}?${params.toString()}`
}

export default function ViewSyncPage() {
    const { t } = useLanguage()
    const canAdd = hasActionPermission('ViewSync', 'add')
    const canDelete = hasActionPermission('ViewSync', 'delete')
    const [videos, setVideos] = useState<VideoItem[]>([])
    const [newVideoUrl, setNewVideoUrl] = useState('')
    const [layoutId, setLayoutId] = useState<string>('auto')
    const [shareUrl, setShareUrl] = useState<string>('')

    useEffect(() => {
        const params = new URLSearchParams(window.location.search)
        const parsed: VideoItem[] = []
        let index = 0
        while (params.has(`video${index}`)) {
            const url = params.get(`video${index}`) || ''
            const startTime = Number(params.get(`start${index}`) || 0)
            if (url) {
                parsed.push({
                    id: `${Date.now()}-${index}`,
                    url,
                    title: `Video ${index + 1}`,
                    startTime,
                })
            }
            index += 1
        }
        if (parsed.length > 0) {
            setVideos(parsed)
            const paramLayout = params.get('layout')
            if (paramLayout) setLayoutId(paramLayout)
        }
    }, [])

    useEffect(() => {
        setShareUrl(videos.length > 0 ? buildShareUrl(videos) : '')
    }, [videos])

    const addVideo = () => {
        const trimmed = newVideoUrl.trim()
        if (!trimmed) return
        if (videos.length >= 10) return
        const next: VideoItem = {
            id: `${Date.now()}-${videos.length}`,
            url: trimmed,
            title: `Video ${videos.length + 1}`,
            startTime: 0,
        }
        setVideos((prev) => [...prev, next])
        setNewVideoUrl('')
    }

    const removeVideo = (id: string) => {
        setVideos((prev) => prev.filter((item) => item.id !== id))
    }

    const copyShareUrl = async () => {
        if (!shareUrl) return
        try {
            await navigator.clipboard.writeText(shareUrl)
        } catch {
            // fallback
        }
    }

    const openMultiView = () => {
        const params = buildParams(videos, layoutId)
        window.open(`/viewsync/multi?${params.toString()}`, '_blank')
    }

    const activeLayout = useMemo(() => {
        if (layoutId !== 'auto') {
            return LAYOUTS.find((layout) => layout.id === layoutId) || LAYOUTS[0]
        }
        const count = Math.max(1, Math.min(videos.length, 10))
        return LAYOUTS.find((layout) => layout.max >= count) || LAYOUTS[LAYOUTS.length - 1]
    }, [layoutId, videos.length])

    const gridStyle = useMemo(() => (
        {
            gridTemplateColumns: `repeat(${activeLayout.columns}, minmax(0, 1fr))`,
            gridTemplateRows: `repeat(${activeLayout.rows}, minmax(0, 1fr))`,
        }
    ), [activeLayout.columns, activeLayout.rows])

    useEffect(() => {
        if (layoutId === 'auto') return
        if (videos.length <= activeLayout.max) return
        setLayoutId('auto')
    }, [activeLayout.max, layoutId, videos.length])

    return (
        <div className="viewsync-shell viewsync-minimal">
            <section className="viewsync-input">
                <div>
                    <h3>{t('viewsync.addVideo')}</h3>
                    <p>{t('viewsync.addVideoDesc')}</p>
                </div>
                <div className="viewsync-input-row">
                    <input
                        className="viewsync-input-field"
                        type="text"
                        placeholder={t('viewsync.placeholder')}
                        value={newVideoUrl}
                        onChange={(event) => setNewVideoUrl(event.target.value)}
                        onKeyDown={(event) => {
                            if (event.key === 'Enter') addVideo()
                        }}
                    />
                    {canAdd && (
                        <button className="viewsync-primary-btn" type="button" onClick={addVideo}>{t('viewsync.addBtn')}</button>
                    )}
                </div>
                <div className="viewsync-input-meta">
                    <span>{videos.length} video(s)</span>
                    <div className="viewsync-input-actions">
                        {shareUrl && (
                            <button className="viewsync-outline-btn" type="button" onClick={copyShareUrl}>{t('viewsync.copyShareUrl')}</button>
                        )}
                        <button className="viewsync-outline-btn" type="button" onClick={openMultiView} disabled={videos.length === 0}>
                            {t('viewsync.openMultiview')}
                        </button>
                    </div>
                </div>
                {shareUrl && (
                    <input className="viewsync-share-input" type="text" value={shareUrl} readOnly />
                )}
            </section>

            <section className="viewsync-preview">
                <div className="viewsync-preview-header">
                    <div>
                        <h3>{t('viewsync.videoLayout')}</h3>
                        <p>{t('viewsync.videoLayoutDesc')}</p>
                    </div>
                </div>
                {videos.length === 0 ? (
                    <div className="viewsync-empty">
                        <h4>{t('viewsync.noVideos')}</h4>
                        <p>{t('viewsync.noVideosDesc')}</p>
                    </div>
                ) : (
                    <div className="viewsync-video-grid" style={gridStyle}>
                        {videos.map((item, index) => (
                            <div key={item.id} className="viewsync-video-card" style={activeLayout.spans?.[index]}>
                                <div className="viewsync-video-top">
                                    <span>{item.title}</span>
                                    <span className={`viewsync-video-pill ${index === 0 ? 'viewsync-pill-master' : 'viewsync-pill-sync'}`}>
                                        {index === 0 ? 'MASTER' : 'SYNC'}
                                    </span>
                                </div>
                                <div className="viewsync-video-frame">
                                    <div className="viewsync-video-body">
                                        <div className="viewsync-video-label">URL</div>
                                        <div className="viewsync-video-url" title={item.url}>{item.url}</div>
                                    </div>
                                </div>
                                <div className="viewsync-video-footer">
                                    <span>Start: {formatTime(item.startTime)}</span>
                                    {canDelete && (
                                        <button className="viewsync-remove-btn" type="button" onClick={() => removeVideo(item.id)}>
                                            {t('viewsync.remove')}
                                        </button>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </section>

            <section className="viewsync-controls">
                <div>
                    <h3>Chon bo cuc</h3>
                    <p>Toi da 10 video. Chon khung bo cuc phu hop nhu cau xem.</p>
                </div>
                <div className="viewsync-layout-grid">
                    <button
                        type="button"
                        className={`viewsync-layout-card ${layoutId === 'auto' ? 'viewsync-layout-active' : ''}`}
                        onClick={() => setLayoutId('auto')}
                    >
                        <div className="viewsync-layout-name">Auto</div>
                        <div className="viewsync-layout-desc">Tu dong theo so video</div>
                        <div className="viewsync-layout-preview">
                            <span className="viewsync-layout-cell" />
                            <span className="viewsync-layout-cell" />
                            <span className="viewsync-layout-cell" />
                            <span className="viewsync-layout-cell" />
                        </div>
                    </button>
                    {LAYOUTS.map((layout) => (
                        <button
                            key={layout.id}
                            type="button"
                            className={`viewsync-layout-card ${layoutId === layout.id ? 'viewsync-layout-active' : ''}`}
                            onClick={() => setLayoutId(layout.id)}
                        >
                            <div className="viewsync-layout-name">{layout.name}</div>
                            <div className="viewsync-layout-desc">Toi da {layout.max} video</div>
                            <div
                                className="viewsync-layout-preview"
                                style={{
                                    gridTemplateColumns: `repeat(${layout.columns}, minmax(0, 1fr))`,
                                    gridTemplateRows: `repeat(${layout.rows}, minmax(0, 1fr))`,
                                }}
                            >
                                {Array.from({ length: layout.columns * layout.rows }).map((_, index) => (
                                    <span key={`${layout.id}-${index}`} className="viewsync-layout-cell" />
                                ))}
                            </div>
                        </button>
                    ))}
                </div>
            </section>
        </div>
    )
}

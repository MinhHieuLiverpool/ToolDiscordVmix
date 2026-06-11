import { useEffect, useMemo, useState } from 'react'

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

function extractVideoId(url: string): string | null {
    const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|&v=)([^#&?]*).*/
    const match = url.match(regExp)
    return match && match[2].length === 11 ? match[2] : null
}

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

function buildMultiUrl(videos: VideoItem[], layout: string) {
    const params = buildParams(videos, layout)
    return `${window.location.origin}/viewsync/multi?${params.toString()}`
}

export default function ViewSyncPage() {
    const [videos, setVideos] = useState<VideoItem[]>([])
    const [newVideoUrl, setNewVideoUrl] = useState('')
    const [shareUrl, setShareUrl] = useState('')
    const [currentTime] = useState(0)
    const [layoutId, setLayoutId] = useState<string>('auto')

    useEffect(() => {
        if (!window.name) {
            window.name = 'viewsync-main'
        }
        const params = new URLSearchParams(window.location.search)
        if (params.get('mode') === 'multi') {
            params.delete('mode')
            const nextUrl = `${window.location.origin}/viewsync/multi?${params.toString()}`
            window.location.replace(nextUrl)
        }
    }, [])

    useEffect(() => {
        if (videos.length === 0) {
            setShareUrl('')
            return
        }
        setShareUrl(buildShareUrl(videos))
    }, [videos])

    const addVideo = () => {
        const trimmed = newVideoUrl.trim()
        if (!trimmed) return
        if (videos.length >= 10) {
            alert('Tối đa 10 video.')
            return
        }
        
        let videoId = extractVideoId(trimmed)
        const isYouTube = !!videoId

        if (!videoId) {
            // Check if it's a valid URL
            try {
                new URL(trimmed)
                videoId = `custom-${videos.length}`
            } catch {
                alert('URL không hợp lệ. Vui lòng nhập link YouTube hoặc link stream trực tiếp (http/https).')
                return
            }
        }

        if (videos.some((video) => video.url === trimmed)) {
            alert('Video này đã có trong danh sách.')
            return
        }

        const newVideo: VideoItem = {
            id: videoId,
            url: trimmed,
            title: isYouTube ? `YouTube ${videos.length + 1}` : `Live ${videos.length + 1}`,
            startTime: Math.floor(currentTime),
        }
        setVideos((prev) => [...prev, newVideo])
        setNewVideoUrl('')
    }

    const removeVideo = (videoId: string) => {
        setVideos((prev) => prev.filter((video) => video.id !== videoId))
    }

    const copyShareUrl = () => {
        if (!shareUrl) return
        navigator.clipboard.writeText(shareUrl)
    }

    const openMultiView = () => {
        if (videos.length === 0) return
        const url = buildMultiUrl(videos, layoutId)
        window.open(url, 'viewsync-multi', 'width=1200,height=760,scrollbars=yes,resizable=yes')
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
                    <h3>Add video</h3>
                    <p>Them link YouTube de tao bo cuc dong bo.</p>
                </div>
                <div className="viewsync-input-row">
                    <input
                        className="viewsync-input-field"
                        type="text"
                        placeholder="Nhap YouTube URL..."
                        value={newVideoUrl}
                        onChange={(event) => setNewVideoUrl(event.target.value)}
                        onKeyDown={(event) => {
                            if (event.key === 'Enter') addVideo()
                        }}
                    />
                    <button className="viewsync-primary-btn" type="button" onClick={addVideo}>Add Video</button>
                </div>
                <div className="viewsync-input-meta">
                    <span>{videos.length} video(s)</span>
                    <div className="viewsync-input-actions">
                        {shareUrl && (
                            <button className="viewsync-outline-btn" type="button" onClick={copyShareUrl}>Copy Share URL</button>
                        )}
                        <button className="viewsync-outline-btn" type="button" onClick={openMultiView} disabled={videos.length === 0}>
                            Open Multiview
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
                        <h3>Video Layout</h3>
                        <p>Bo cuc theo so luong video dang hoat dong.</p>
                    </div>
                </div>
                {videos.length === 0 ? (
                    <div className="viewsync-empty">
                        <h4>Chua co video nao</h4>
                        <p>Nhap YouTube URL de bat dau dong bo.</p>
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
                                    <button className="viewsync-remove-btn" type="button" onClick={() => removeVideo(item.id)}>
                                        Remove
                                    </button>
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

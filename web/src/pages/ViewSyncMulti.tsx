import { useEffect, useMemo, useRef, useState } from 'react'

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

type PlayerEvent = {
    target: any
    data?: number
}

declare global {
    interface Window {
        YT?: any
        onYouTubeIframeAPIReady?: () => void
    }
}

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

function YouTubePlayer({
    videoId,
    onPlayerReady,
    startTime,
}: {
    videoId: string
    onPlayerReady: (videoId: string, event: PlayerEvent) => void
    startTime: number
}) {
    const playerRef = useRef<any>(null)
    const containerRef = useRef<HTMLDivElement>(null)
    const readyRef = useRef(false)
    const origin = window.location.origin
    const originParam = encodeURIComponent(origin)

    useEffect(() => {
        let initTimeout: ReturnType<typeof setTimeout> | null = null

        const initializePlayer = () => {
            if (!window.YT || !window.YT.Player) return
            if (!containerRef.current) return
            if (playerRef.current && readyRef.current) return

            if (playerRef.current) {
                try {
                    playerRef.current.destroy()
                } catch {
                    // ignore destroy errors
                }
                readyRef.current = false
            }

            initTimeout = setTimeout(() => {
                if (!containerRef.current) return
                playerRef.current = new window.YT.Player(containerRef.current, {
                    height: '100%',
                    width: '100%',
                    videoId,
                    playerVars: {
                        autoplay: 0,
                        controls: 1,
                        modestbranding: 1,
                        rel: 0,
                        fs: 1,
                        enablejsapi: 1,
                        origin,
                        widget_referrer: window.location.href,
                    },
                    events: {
                        onReady: (event: PlayerEvent) => {
                            readyRef.current = true
                            onPlayerReady(videoId, event)
                            if (startTime > 0) {
                                event.target.seekTo(startTime, true)
                            }
                        },
                    },
                })
            }, 100)
        }

        if (window.YT && window.YT.Player) {
            initializePlayer()
        } else {
            const originalCallback = window.onYouTubeIframeAPIReady
            window.onYouTubeIframeAPIReady = () => {
                if (originalCallback) originalCallback()
                initializePlayer()
            }
        }

        return () => {
            if (initTimeout) clearTimeout(initTimeout)
            if (playerRef.current) {
                try {
                    playerRef.current.destroy()
                } catch {
                    // ignore destroy errors
                }
            }
            readyRef.current = false
        }
    }, [videoId, startTime, onPlayerReady])

    // Always render the container div so the YouTube API can replace it
    // with a controllable player when it becomes available. While the
    // API is loading, show the standard iframe as a visual fallback.
    return (
        <div ref={containerRef} className="viewsync-player">
            {(!window.YT || !window.YT.Player) && (
                <iframe
                    title={`YouTube ${videoId}`}
                    className="viewsync-iframe"
                    src={`https://www.youtube.com/embed/${videoId}?enablejsapi=1&origin=${originParam}&start=${startTime}`}
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                    allowFullScreen
                />
            )}
        </div>
    )
}

export default function ViewSyncMultiPage() {
    const [videos, setVideos] = useState<VideoItem[]>([])
    const [, setCurrentTime] = useState(0)
    const playersRef = useRef<Record<string, any>>({})
    const [layoutId, setLayoutId] = useState<string>('auto')

    useEffect(() => {
        if (!window.name) {
            window.name = 'viewsync-multi'
        }
        document.body.classList.add('viewsync-multi-body')
        return () => {
            document.body.classList.remove('viewsync-multi-body')
        }
    }, [])

    useEffect(() => {
        const scriptId = 'viewsync-yt-api'
        if (window.YT && window.YT.Player) return
        if (document.getElementById(scriptId)) return
        const script = document.createElement('script')
        script.id = scriptId
        script.src = 'https://www.youtube.com/iframe_api'
        script.async = true
        document.head.appendChild(script)
    }, [])

    useEffect(() => {
        const params = new URLSearchParams(window.location.search)
        const loaded: VideoItem[] = []
        let index = 0
        while (params.has(`video${index}`)) {
            const url = params.get(`video${index}`) || ''
            const startTime = Number(params.get(`start${index}`) || '0')
            const videoId = extractVideoId(url)
            if (videoId) {
                loaded.push({
                    id: videoId,
                    url,
                    title: `Video ${index + 1}`,
                    startTime,
                })
            }
            index += 1
        }
        setVideos(loaded)
        const requestedLayout = params.get('layout') || 'auto'
        setLayoutId(requestedLayout)
    }, [])

    useEffect(() => {
        if (videos.length === 0) return
        const masterId = videos[0].id
        const timer = setInterval(() => {
            const master = playersRef.current[masterId]
            if (master && typeof master.getCurrentTime === 'function') {
                setCurrentTime(master.getCurrentTime())
            }
        }, 1000)
        return () => clearInterval(timer)
    }, [videos])

    const onPlayerReady = (videoId: string, event: PlayerEvent) => {
        playersRef.current[videoId] = event.target
    }

    const activeLayout = useMemo(() => {
        if (layoutId !== 'auto') {
            return LAYOUTS.find((layout) => layout.id === layoutId) || LAYOUTS[0]
        }
        const count = Math.max(1, Math.min(videos.length, 10))
        return LAYOUTS.find((layout) => layout.max >= count) || LAYOUTS[LAYOUTS.length - 1]
    }, [layoutId, videos.length])

    const playAll = () => {
        Object.values(playersRef.current).forEach((player, index) => {
            if (!player || typeof player.playVideo !== 'function') return
            setTimeout(() => {
                try {
                    player.playVideo()
                } catch {
                    // ignore play errors
                }
            }, index * 120)
        })
    }

    const pauseAll = () => {
        Object.values(playersRef.current).forEach((player) => {
            if (!player || typeof player.pauseVideo !== 'function') return
            try {
                player.pauseVideo()
            } catch {
                // ignore pause errors
            }
        })
    }

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
            <section className="viewsync-preview">
                <div className="viewsync-multi-controls">
                    <button className="viewsync-primary-btn" type="button" onClick={playAll}>Play All</button>
                    <button className="viewsync-ghost-btn" type="button" onClick={pauseAll}>Pause All</button>
                </div>
                {videos.length === 0 ? (
                    <div className="viewsync-empty">
                        <h4>Khong co video</h4>
                        <p>URL chua co video de render.</p>
                    </div>
                ) : (
                    <div className="viewsync-video-grid" style={gridStyle}>
                        {videos.map((item, index) => (
                            <div key={item.id} className="viewsync-video-card" style={activeLayout.spans?.[index]}>
                                <div className="viewsync-video-top">
                                    <div className="viewsync-video-title">
                                        <span>{item.title}</span>
                                        <span className={`viewsync-video-pill ${index === 0 ? 'viewsync-pill-master' : 'viewsync-pill-sync'}`}>
                                            {index === 0 ? 'MASTER' : 'SYNC'}
                                        </span>
                                    </div>
                                </div>
                                <div className="viewsync-video-frame">
                                    <div className="viewsync-video-frame-media">
                                        <YouTubePlayer
                                            videoId={item.id}
                                            onPlayerReady={onPlayerReady}
                                            startTime={item.startTime}
                                        />
                                    </div>
                                </div>
                                <div className="viewsync-video-footer">
                                    <span>Start: {formatTime(item.startTime)}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </section>
        </div>
    )
}

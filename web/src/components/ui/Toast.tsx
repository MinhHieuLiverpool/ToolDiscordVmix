import { useCallback, useEffect, useRef, useState } from 'react'

export type ToastType = 'success' | 'error' | 'info' | 'warning'

export interface ToastItem {
    id: number
    message: string
    type: ToastType
    duration?: number
}

let _globalAddToast: ((message: string, type: ToastType, duration?: number) => void) | null = null
let _idCounter = 0

/**
 * Global function to show a toast from anywhere.
 */
export function showToast(message: string, type: ToastType = 'info', duration = 3500) {
    _globalAddToast?.(message, type, duration)
}

const ICONS: Record<ToastType, string> = {
    success: '✓',
    error: '✕',
    warning: '⚠',
    info: 'ℹ',
}

function ToastCard({ item, onRemove }: { item: ToastItem; onRemove: (id: number) => void }) {
    const [exiting, setExiting] = useState(false)
    const timerRef = useRef<number | null>(null)

    const startExit = useCallback(() => {
        setExiting(true)
        setTimeout(() => onRemove(item.id), 340)
    }, [item.id, onRemove])

    useEffect(() => {
        timerRef.current = window.setTimeout(startExit, item.duration ?? 3500)
        return () => {
            if (timerRef.current) window.clearTimeout(timerRef.current)
        }
    }, [item.duration, startExit])

    return (
        <div className={`toast-card toast-${item.type} ${exiting ? 'toast-exit' : 'toast-enter'}`}>
            <span className="toast-icon">{ICONS[item.type]}</span>
            <span className="toast-msg">{item.message}</span>
            <button className="toast-close" type="button" onClick={startExit} aria-label="Close">
                ✕
            </button>
        </div>
    )
}

export default function ToastContainer() {
    const [toasts, setToasts] = useState<ToastItem[]>([])

    const addToast = useCallback((message: string, type: ToastType, duration?: number) => {
        const id = ++_idCounter
        setToasts((prev) => [...prev, { id, message, type, duration }])
    }, [])

    const removeToast = useCallback((id: number) => {
        setToasts((prev) => prev.filter((t) => t.id !== id))
    }, [])

    useEffect(() => {
        _globalAddToast = addToast
        return () => {
            _globalAddToast = null
        }
    }, [addToast])

    if (toasts.length === 0) return null

    return (
        <div className="toast-container">
            {toasts.map((item) => (
                <ToastCard key={item.id} item={item} onRemove={removeToast} />
            ))}
        </div>
    )
}

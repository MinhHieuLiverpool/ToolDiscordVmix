import { useEffect, useRef, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

interface DialogProps {
    open: boolean
    onClose: () => void
    title: string
    children: ReactNode
}

export default function Dialog({ open, onClose, title, children }: DialogProps) {
    const overlayRef = useRef<HTMLDivElement>(null)
    const panelRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        if (!open) return
        const handleEsc = (e: KeyboardEvent) => {
            if (e.key === 'Escape') onClose()
        }
        document.addEventListener('keydown', handleEsc)
        document.body.style.overflow = 'hidden'
        return () => {
            document.removeEventListener('keydown', handleEsc)
            document.body.style.overflow = ''
        }
    }, [open, onClose])

    if (!open) return null

    return createPortal(
        <div
            className="dialog-overlay"
            ref={overlayRef}
            onClick={(e) => {
                if (e.target === overlayRef.current) onClose()
            }}
        >
            <div className="dialog-panel" ref={panelRef}>
                <div className="dialog-header">
                    <h3 className="dialog-title">{title}</h3>
                    <button
                        type="button"
                        className="dialog-close-btn"
                        onClick={onClose}
                        aria-label="Close"
                    >
                        Đóng
                    </button>
                </div>
                <div className="dialog-body">
                    {children}
                </div>
            </div>
        </div>,
        document.body,
    )
}

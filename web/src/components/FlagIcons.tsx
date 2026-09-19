export function FlagVN({ className = '', size = 16 }: { className?: string; size?: number }) {
    const height = Math.round((size * 2) / 3)
    return (
        <svg
            viewBox="0 0 30 20"
            width={size}
            height={height}
            className={`lang-flag-icon ${className}`}
            style={{
                borderRadius: '2.5px',
                overflow: 'hidden',
                display: 'inline-block',
                verticalAlign: 'middle',
                flexShrink: 0,
                boxShadow: '0 0 0 1px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.15)'
            }}
            aria-hidden="true"
        >
            <rect width="30" height="20" fill="#DA251D" />
            <polygon
                fill="#FFFF00"
                points="15,4 16.41,8.35 20.98,8.35 17.28,11.04 18.7,15.39 15,12.7 11.3,15.39 12.72,11.04 9.02,8.35 13.59,8.35"
            />
        </svg>
    )
}

export function FlagEN({ className = '', size = 16 }: { className?: string; size?: number }) {
    const height = Math.round((size * 2) / 3)
    return (
        <svg
            viewBox="0 0 30 20"
            width={size}
            height={height}
            className={`lang-flag-icon ${className}`}
            style={{
                borderRadius: '2.5px',
                overflow: 'hidden',
                display: 'inline-block',
                verticalAlign: 'middle',
                flexShrink: 0,
                boxShadow: '0 0 0 1px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.15)'
            }}
            aria-hidden="true"
        >
            <rect width="30" height="20" fill="#012169" />
            <path d="M0,0 L30,20 M30,0 L0,20" stroke="#FFFFFF" strokeWidth="4" />
            <path d="M0,0 L30,20 M30,0 L0,20" stroke="#C8102E" strokeWidth="2.2" />
            <path d="M15,0 v20 M0,10 h30" stroke="#FFFFFF" strokeWidth="6" />
            <path d="M15,0 v20 M0,10 h30" stroke="#C8102E" strokeWidth="3.6" />
        </svg>
    )
}

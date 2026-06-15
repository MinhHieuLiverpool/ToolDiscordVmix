import { useEffect, useRef, useState } from 'react'
import type { DeviceFilter, TimeFilter } from '../types'

export default function FilterBar({
    deviceFilter,
    setDeviceFilter,
    activeView,
    setActiveView,
    machineOptions,
    onRefresh,
    dailyLabel = 'Cả ngày',
    dailyDesc = '15 phút avg',
}: {
    deviceFilter: DeviceFilter
    setDeviceFilter: (v: DeviceFilter) => void
    activeView: TimeFilter
    setActiveView: (v: TimeFilter) => void
    machineOptions: { id: string; label: string }[]
    onRefresh: () => void
    dailyLabel?: string
    dailyDesc?: string
}) {
    const [dropdownOpen, setDropdownOpen] = useState(false)
    const [searchTerm, setSearchTerm] = useState('')
    const dropdownRef = useRef<HTMLDivElement>(null)

    // Close dropdown on outside click
    useEffect(() => {
        function handleClick(e: MouseEvent) {
            if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
                setDropdownOpen(false)
            }
        }
        document.addEventListener('mousedown', handleClick)
        return () => document.removeEventListener('mousedown', handleClick)
    }, [])

    const filteredOptions = machineOptions.filter((opt) =>
        opt.label.toLowerCase().includes(searchTerm.toLowerCase()),
    )

    const selectedLabel = deviceFilter === '__all__'
        ? 'Tất cả máy'
        : machineOptions.find((opt) => opt.id === deviceFilter)?.label ?? deviceFilter

    return (
        <div className="filter-bar">
            {/* Custom Dropdown */}
            <div className="filter-group">
                <label className="filter-label" htmlFor="device-filter">
                    Bộ lọc máy
                </label>
                <div className="custom-dropdown" ref={dropdownRef}>
                    <button
                        type="button"
                        className={`dropdown-trigger ${dropdownOpen ? 'dropdown-open' : ''}`}
                        onClick={() => setDropdownOpen(!dropdownOpen)}
                    >
                        <span className="dropdown-trigger-text">{selectedLabel}</span>
                        <svg className={`dropdown-chevron ${dropdownOpen ? 'chevron-up' : ''}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="6 9 12 15 18 9" />
                        </svg>
                    </button>

                    {dropdownOpen && (
                        <div className="dropdown-menu">
                            <div className="dropdown-search-wrap">
                                <input
                                    className="dropdown-search"
                                    type="text"
                                    placeholder="Tìm kiếm máy..."
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                    autoFocus
                                />
                            </div>
                            <div className="dropdown-options">
                                <button
                                    type="button"
                                    className={`dropdown-option ${deviceFilter === '__all__' ? 'option-active' : ''}`}
                                    onClick={() => {
                                        setDeviceFilter('__all__')
                                        setDropdownOpen(false)
                                        setSearchTerm('')
                                    }}
                                >
                                    <span className="option-dot option-dot-all" />
                                    Tất cả máy
                                    <span className="option-count">{machineOptions.length}</span>
                                </button>
                                {filteredOptions.map((opt) => (
                                    <button
                                        type="button"
                                        key={opt.id}
                                        className={`dropdown-option ${deviceFilter === opt.id ? 'option-active' : ''}`}
                                        onClick={() => {
                                            setDeviceFilter(opt.id)
                                            setDropdownOpen(false)
                                            setSearchTerm('')
                                        }}
                                    >
                                        <span className="option-dot option-dot-single" />
                                        {opt.label}
                                    </button>
                                ))}
                                {filteredOptions.length === 0 && (
                                    <div className="dropdown-empty">Không tìm thấy máy nào</div>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* View Navigation Buttons - text only, no icons */}
            <div className="filter-group">
                <label className="filter-label">
                    Chế độ xem
                </label>
                <div className="view-nav-buttons">
                    <button
                        type="button"
                        className={`view-nav-btn ${activeView === 'realtime' ? 'view-nav-active' : ''}`}
                        onClick={() => setActiveView('realtime')}
                    >
                        <span className="view-nav-label">Realtime</span>
                        <span className="view-nav-desc">3 phút</span>
                    </button>
                    <button
                        type="button"
                        className={`view-nav-btn ${activeView === 'daily' ? 'view-nav-active' : ''}`}
                        onClick={() => setActiveView('daily')}
                    >
                        <span className="view-nav-label">{dailyLabel}</span>
                        <span className="view-nav-desc">{dailyDesc}</span>
                    </button>
                </div>
            </div>

            {/* Refresh - text button */}
            <button className="refresh-btn" onClick={onRefresh} type="button">
                <svg className="refresh-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M23 4v6h-6" />
                    <path d="M1 20v-6h6" />
                    <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
                </svg>
                REFRESH
            </button>
        </div>
    )
}

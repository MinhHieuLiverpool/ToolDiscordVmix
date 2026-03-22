import { useEffect, useRef, useState } from 'react'
import type { DeviceFilter, TimeFilter } from '../types'

export default function FilterBar({
    deviceFilter,
    setDeviceFilter,
    activeView,
    setActiveView,
    machineOptions,
    onRefresh,
}: {
    deviceFilter: DeviceFilter
    setDeviceFilter: (v: DeviceFilter) => void
    activeView: TimeFilter
    setActiveView: (v: TimeFilter) => void
    machineOptions: { id: string; label: string }[]
    onRefresh: () => void
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
                    <svg className="filter-label-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
                        <line x1="8" y1="21" x2="16" y2="21" />
                        <line x1="12" y1="17" x2="12" y2="21" />
                    </svg>
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
                                <svg className="dropdown-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <circle cx="11" cy="11" r="8" />
                                    <line x1="21" y1="21" x2="16.65" y2="16.65" />
                                </svg>
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

            {/* View Navigation Buttons */}
            <div className="filter-group">
                <label className="filter-label">
                    <svg className="filter-label-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <line x1="18" y1="20" x2="18" y2="10" />
                        <line x1="12" y1="20" x2="12" y2="4" />
                        <line x1="6" y1="20" x2="6" y2="14" />
                    </svg>
                    Chế độ xem
                </label>
                <div className="view-nav-buttons">
                    <button
                        type="button"
                        className={`view-nav-btn ${activeView === 'realtime' ? 'view-nav-active' : ''}`}
                        onClick={() => setActiveView('realtime')}
                    >
                        <span className="view-nav-icon">⏱</span>
                        <span className="view-nav-label">Realtime</span>
                        <span className="view-nav-desc">3 phút</span>
                    </button>
                    <button
                        type="button"
                        className={`view-nav-btn ${activeView === 'daily' ? 'view-nav-active' : ''}`}
                        onClick={() => setActiveView('daily')}
                    >
                        <span className="view-nav-icon">📅</span>
                        <span className="view-nav-label">Cả ngày</span>
                        <span className="view-nav-desc">15 phút avg</span>
                    </button>
                </div>
            </div>

            {/* Refresh */}
            <button className="refresh-btn" onClick={onRefresh} type="button">
                <svg className="refresh-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="23 4 23 10 17 10" />
                    <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
                </svg>
                Refresh
            </button>
        </div>
    )
}

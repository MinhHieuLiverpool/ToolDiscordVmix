import type { DeviceFilter, TimeFilter } from '../types'

export default function FilterBar({
    deviceFilter,
    setDeviceFilter,
    timeFilter,
    setTimeFilter,
    machineOptions,
    onRefresh,
}: {
    deviceFilter: DeviceFilter
    setDeviceFilter: (v: DeviceFilter) => void
    timeFilter: TimeFilter
    setTimeFilter: (v: TimeFilter) => void
    machineOptions: { id: string; label: string }[]
    onRefresh: () => void
}) {
    return (
        <div className="filter-bar">
            <div className="filter-group">
                <label className="filter-label" htmlFor="device-filter">
                    🖥️ Bộ lọc máy
                </label>
                <select
                    id="device-filter"
                    className="filter-select"
                    value={deviceFilter}
                    onChange={(e) => setDeviceFilter(e.target.value as DeviceFilter)}
                >
                    <option value="__all__">Tất cả máy</option>
                    {machineOptions.map((opt) => (
                        <option key={opt.id} value={opt.id}>
                            {opt.label}
                        </option>
                    ))}
                </select>
            </div>

            <div className="filter-group">
                <label className="filter-label">📊 Dữ liệu</label>
                <div className="toggle-buttons">
                    <button
                        type="button"
                        className={`toggle-btn ${timeFilter === 'realtime' ? 'toggle-active' : ''}`}
                        onClick={() => setTimeFilter('realtime')}
                    >
                        ⏱ Hiện tại
                    </button>
                    <button
                        type="button"
                        className={`toggle-btn ${timeFilter === 'daily' ? 'toggle-active' : ''}`}
                        onClick={() => setTimeFilter('daily')}
                    >
                        📅 Cả ngày
                    </button>
                </div>
            </div>

            <button className="refresh-btn" onClick={onRefresh} type="button">
                ↻ Refresh
            </button>
        </div>
    )
}

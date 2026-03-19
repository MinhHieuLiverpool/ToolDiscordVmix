import { useCallback, useMemo, useRef, useState } from 'react'
import { buildPath, buildAreaPath } from '../types'
import type { MachineMetrics, MetricPoint, TimeFilter } from '../types'

const COLORS = {
    cpu: { stroke: '#818cf8', fill: 'rgba(129,140,248,0.13)' },
    ram: { stroke: '#38bdf8', fill: 'rgba(56,189,248,0.13)' },
}

const CHART_W = 640
const PLOT_H = 120

/* ─── Tooltip component ──────────────────────────────── */
function ChartTooltip({
    point,
    x,
    y,
    containerRect,
}: {
    point: MetricPoint
    x: number
    y: number
    containerRect: DOMRect | null
}) {
    if (!containerRect) return null

    // Position tooltip
    const tooltipStyle: React.CSSProperties = {
        position: 'absolute',
        left: x,
        top: y - 8,
        transform: 'translate(-50%, -100%)',
        pointerEvents: 'none',
        zIndex: 100,
    }

    // If tooltip would go off left edge, align left
    if (x < 100) {
        tooltipStyle.left = x
        tooltipStyle.transform = 'translate(0, -100%)'
    }
    // If tooltip would go off right edge, align right
    if (containerRect && x > containerRect.width - 100) {
        tooltipStyle.left = x
        tooltipStyle.transform = 'translate(-100%, -100%)'
    }

    return (
        <div className="chart-tooltip" style={tooltipStyle}>
            <div className="chart-tooltip-title">{point.timeLabel}</div>
            <div className="chart-tooltip-row">
                <span className="chart-tooltip-label">CPU:</span>
                <span className="chart-tooltip-val val-cpu">{point.cpu.toFixed(1)}%</span>
            </div>
            <div className="chart-tooltip-row">
                <span className="chart-tooltip-label">RAM:</span>
                <span className="chart-tooltip-val val-ram">{point.ram.toFixed(1)}%</span>
            </div>

        </div>
    )
}

/* ─── MiniChart ──────────────────────────────────────── */
function MiniChart({
    title,
    icon,
    values,
    maxVal,
    labels,
    color,
    lastVal,
    unit,
    accentClass,
    isDaily,
    points,
}: {
    title: string
    icon: string
    values: number[]
    maxVal: number
    labels: string[]
    color: { stroke: string; fill: string }
    lastVal: number
    unit: string
    accentClass: string
    isDaily: boolean
    points: MetricPoint[]
}) {
    const svgRef = useRef<SVGSVGElement>(null)
    const containerRef = useRef<HTMLDivElement>(null)
    const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)
    const [tooltipPos, setTooltipPos] = useState<{ x: number; y: number }>({ x: 0, y: 0 })
    const [containerRect, setContainerRect] = useState<DOMRect | null>(null)

    const xTickIndices = useMemo(() => {
        if (labels.length === 0) return [] as number[]
        if (isDaily) {
            // Daily: chỉ hiện đầu và cuối
            if (labels.length === 1) return [0]
            return [0, labels.length - 1]
        }
        const desired = Math.min(6, labels.length)
        if (desired <= 1) return [0]
        const indices = Array.from({ length: desired }, (_, i) =>
            Math.round((i * (labels.length - 1)) / (desired - 1)),
        )
        return Array.from(new Set(indices))
    }, [labels, isDaily])

    const stepX = labels.length > 1 ? CHART_W / (labels.length - 1) : 0
    const linePath = buildPath(values, CHART_W, PLOT_H, maxVal)
    const areaPath = buildAreaPath(values, CHART_W, PLOT_H, maxVal)

    const handleDotHover = useCallback((index: number) => {
        setHoveredIndex(index)
        if (svgRef.current && containerRef.current) {
            const svg = svgRef.current
            const container = containerRef.current
            const rect = container.getBoundingClientRect()
            setContainerRect(rect)

            // Convert SVG coords to screen coords
            const svgRect = svg.getBoundingClientRect()
            const scaleX = svgRect.width / CHART_W
            const scaleY = svgRect.height / (PLOT_H + 22)
            const dotX = stepX * index
            const dotY = PLOT_H - (values[index] / maxVal) * PLOT_H
            const screenX = svgRect.left - rect.left + dotX * scaleX
            const screenY = svgRect.top - rect.top + dotY * scaleY
            setTooltipPos({ x: screenX, y: screenY })
        }
    }, [stepX, values, maxVal])

    return (
        <div className="mini-chart" ref={containerRef} style={{ position: 'relative' }}>
            <div className="mini-chart-header">
                <span className="mini-chart-title">
                    {icon} {title}
                </span>
                <span className={`mini-chart-value ${accentClass}`}>
                    {lastVal.toFixed(1)}{unit}
                </span>
            </div>
            <svg
                ref={svgRef}
                className="mini-chart-svg"
                viewBox={`0 0 ${CHART_W} ${PLOT_H + 22}`}
                preserveAspectRatio="none"
            >
                {[0, 0.5, 1].map((ratio) => {
                    const y = PLOT_H * (1 - ratio)
                    return (
                        <line
                            key={`g-${ratio}`}
                            x1="0" y1={y} x2={CHART_W} y2={y}
                            className="chart-grid-line"
                        />
                    )
                })}
                {areaPath && <path d={areaPath} style={{ fill: color.fill }} />}
                {linePath && (
                    <path d={linePath} fill="none" style={{ stroke: color.stroke, strokeWidth: 2 }} />
                )}
                {/* Daily dots */}
                {isDaily && values.map((v, i) => {
                    const cx = stepX * i
                    const cy = PLOT_H - (v / maxVal) * PLOT_H
                    const isHovered = hoveredIndex === i
                    return (
                        <circle
                            key={`dot-${i}`}
                            cx={cx}
                            cy={cy}
                            r={isHovered ? 6 : 3.5}
                            fill={isHovered ? '#fff' : color.stroke}
                            stroke={color.stroke}
                            strokeWidth={isHovered ? 2.5 : 1.5}
                            className="chart-dot"
                            onMouseEnter={() => handleDotHover(i)}
                            onMouseLeave={() => setHoveredIndex(null)}
                            style={{ cursor: 'pointer' }}
                        />
                    )
                })}
                {xTickIndices.map((index, i) => {
                    const x = stepX * index
                    const isFirst = i === 0
                    const isLast = i === xTickIndices.length - 1
                    const anchor = isFirst ? 'start' : isLast ? 'end' : 'middle'
                    return (
                        <text
                            key={`t-${index}`}
                            x={x} y={PLOT_H + 14}
                            textAnchor={anchor}
                            className="chart-tick-label"
                            style={{ fontWeight: 700 }}
                        >
                            {labels[index]}
                        </text>
                    )
                })}
            </svg>
            {/* Tooltip */}
            {isDaily && hoveredIndex !== null && points[hoveredIndex] && (
                <ChartTooltip
                    point={points[hoveredIndex]}
                    x={tooltipPos.x}
                    y={tooltipPos.y}
                    containerRect={containerRect}
                />
            )}
        </div>
    )
}

export default function MachineChartCard({ machine, timeFilter }: { machine: MachineMetrics; timeFilter: TimeFilter }) {
    const cpuValues = machine.history.map((p) => p.cpu)
    const ramValues = machine.history.map((p) => p.ram)
    const labels = machine.history.map((p) => p.timeLabel)
    const isDaily = timeFilter === 'daily'

    const ramMax = useMemo(() => {
        const max = ramValues.length > 0 ? Math.max(...ramValues) : 100
        return Math.max(100, Math.ceil(max / 10) * 10)
    }, [ramValues])

    const lastCpu = cpuValues.length > 0 ? cpuValues[cpuValues.length - 1] : 0
    const lastRam = ramValues.length > 0 ? ramValues[ramValues.length - 1] : 0

    return (
        <div className="machine-chart-card glass-card card-animate">
            <div className="machine-chart-header">
                <h3 className="machine-chart-name">{machine.label}</h3>
                <div className="machine-chart-stats">
                    <span className="live-stat stat-cpu-live">CPU: {lastCpu.toFixed(1)}%</span>
                    <span className="live-stat stat-ram-live">RAM: {lastRam.toFixed(1)}%</span>
                </div>
            </div>

            <MiniChart
                title="CPU" icon="🔥"
                values={cpuValues} maxVal={100} labels={labels}
                color={COLORS.cpu} lastVal={lastCpu} unit="%" accentClass="val-cpu"
                isDaily={isDaily} points={machine.history}
            />
            <MiniChart
                title="RAM" icon="💾"
                values={ramValues} maxVal={ramMax} labels={labels}
                color={COLORS.ram} lastVal={lastRam} unit="%" accentClass="val-ram"
                isDaily={isDaily} points={machine.history}
            />
        </div>
    )
}

import { useMemo } from 'react'
import { buildPath, buildAreaPath } from '../types'
import type { MachineMetrics } from '../types'

const COLORS = {
    cpu: { stroke: '#818cf8', fill: 'rgba(129,140,248,0.13)' },
    ram: { stroke: '#38bdf8', fill: 'rgba(56,189,248,0.13)' },
}

const CHART_W = 640
const PLOT_H = 120

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
}) {
    const xTickIndices = useMemo(() => {
        if (labels.length === 0) return [] as number[]
        const desired = Math.min(6, labels.length)
        if (desired <= 1) return [0]
        const indices = Array.from({ length: desired }, (_, i) =>
            Math.round((i * (labels.length - 1)) / (desired - 1)),
        )
        return Array.from(new Set(indices))
    }, [labels])

    const stepX = labels.length > 1 ? CHART_W / (labels.length - 1) : 0
    const linePath = buildPath(values, CHART_W, PLOT_H, maxVal)
    const areaPath = buildAreaPath(values, CHART_W, PLOT_H, maxVal)

    return (
        <div className="mini-chart">
            <div className="mini-chart-header">
                <span className="mini-chart-title">
                    {icon} {title}
                </span>
                <span className={`mini-chart-value ${accentClass}`}>
                    {lastVal.toFixed(1)}{unit}
                </span>
            </div>
            <svg
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
                {xTickIndices.map((index) => {
                    const x = stepX * index
                    return (
                        <text
                            key={`t-${index}`}
                            x={x} y={PLOT_H + 14}
                            textAnchor="middle"
                            className="chart-tick-label"
                        >
                            {labels[index]}
                        </text>
                    )
                })}
            </svg>
        </div>
    )
}

export default function MachineChartCard({ machine }: { machine: MachineMetrics }) {
    const cpuValues = machine.history.map((p) => p.cpu)
    const ramValues = machine.history.map((p) => p.ram)
    const labels = machine.history.map((p) => p.timeLabel)

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
            />
            <MiniChart
                title="RAM" icon="💾"
                values={ramValues} maxVal={ramMax} labels={labels}
                color={COLORS.ram} lastVal={lastRam} unit="%" accentClass="val-ram"
            />
        </div>
    )
}

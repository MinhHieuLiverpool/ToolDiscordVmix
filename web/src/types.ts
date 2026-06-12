/* ─── Shared types ─────────────────────────────────────────── */

export type DailyExtras = {
    windowStart: string
    windowEnd: string
    samples: number
    cpuPoints: number
    ramPoints: number
    calculatedAt: string
}

export type MetricPoint = {
    timeLabel: string
    cpu: number
    ram: number
    gpu?: number
    ping?: number | null
    timeMs?: number
    extras?: DailyExtras
}

import type { BackendLogItem } from './services/api'

export type MachineMetrics = {
    id: string
    label: string
    history: MetricPoint[]
    latestItem?: BackendLogItem
}

export type DeviceFilter = '__all__' | string
export type TimeFilter = 'realtime' | 'daily'

/* ─── Utility helpers ──────────────────────────────────────── */

export function toNumber(value: unknown): number | null {
    if (value === null || value === undefined || value === '') return null
    const parsed = Number.parseFloat(String(value).replace(',', '.'))
    return Number.isFinite(parsed) ? parsed : null
}

/* ─── SVG chart helpers ────────────────────────────────────── */

export function buildPath(values: number[], w: number, h: number, max: number): string {
    if (values.length === 0) return ''
    if (values.length === 1) {
        const y = h - (values[0] / max) * h
        return `M 0 ${y}`
    }
    const step = w / (values.length - 1)
    return values
        .map((v, i) => {
            const x = i * step
            const y = h - (v / max) * h
            return `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`
        })
        .join(' ')
}

export function buildAreaPath(values: number[], w: number, h: number, max: number): string {
    const line = buildPath(values, w, h, max)
    if (!line) return ''
    if (values.length === 1) {
        const y = h - (values[0] / max) * h
        return `M 0 ${h} L 0 ${y} L 0 ${h} Z`
    }
    return `${line} L ${w} ${h} L 0 ${h} Z`
}

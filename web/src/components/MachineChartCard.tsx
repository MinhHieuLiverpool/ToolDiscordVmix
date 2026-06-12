import { useMemo, useRef, useEffect } from 'react'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import {
    GridComponent,
    TooltipComponent,
    LegendComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { MachineMetrics, TimeFilter } from '../types'

// Register ECharts modules
echarts.use([LineChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const COLORS = {
    cpu: { line: '#818cf8', area: 'rgba(129,140,248,0.18)' },
    ram: { line: '#38bdf8', area: 'rgba(56,189,248,0.18)' },
    gpu: { line: '#f97316', area: 'rgba(249,115,22,0.18)' },
    ping: { line: '#10b981', area: 'rgba(16,185,129,0.88)' },
}

function EChartsLine({
    labels,
    cpuValues,
    ramValues,
    gpuValues,
    pingValues = [],
    isDaily,
    showXAxisLabels,
}: {
    labels: string[]
    cpuValues: number[]
    ramValues: number[]
    gpuValues: number[]
    pingValues?: (number | null)[]
    isDaily: boolean
    showXAxisLabels: boolean
}) {
    const chartRef = useRef<HTMLDivElement>(null)
    const chartInstanceRef = useRef<echarts.ECharts | null>(null)

    // Map null values to 0 for ECharts line representation
    const chartPingData = useMemo(() => {
        return pingValues.map((v) => (v === null || v === undefined ? 0 : v))
    }, [pingValues])

    // Build option
    const option = useMemo(() => {
        return {
            animation: false,
            grid: {
                top: 8,
                right: 12,
                bottom: showXAxisLabels ? 28 : 10,
                left: 36,
            },
            tooltip: {
                trigger: 'axis' as const,
                backgroundColor: 'rgba(15,23,42,0.92)',
                borderColor: 'rgba(99,102,241,0.3)',
                borderWidth: 1,
                textStyle: {
                    color: '#e2e8f0',
                    fontSize: 11,
                    fontFamily: 'Inter, sans-serif',
                },
                formatter: (params: Array<{ seriesName: string; value: number | null; axisValueLabel: string; color: string; dataIndex: number }>) => {
                    if (!Array.isArray(params) || params.length === 0) return ''
                    const time = params[0].axisValueLabel || ''
                    let html = `<div style="font-weight:700;margin-bottom:4px;font-size:11px">${time}</div>`
                    params.forEach((p) => {
                        const rawVal = isDaily ? pingValues[p.dataIndex] : p.value
                        let valString = ''
                        let colorString = p.color
                        if (isDaily && (rawVal === null || rawVal === undefined)) {
                            valString = '<span style="color:#ef4444;font-weight:800">Timeout</span>'
                            colorString = '#ef4444'
                        } else {
                            const numVal = p.value ?? 0
                            valString = `<span style="font-weight:800">${numVal.toFixed(0)}${isDaily ? ' ms' : '%'}</span>`
                        }
                        html += `<div style="display:flex;align-items:center;gap:6px;font-size:11px">
                            <span style="width:8px;height:8px;border-radius:50%;background:${colorString};display:inline-block"></span>
                            <span style="font-weight:600">${p.seriesName}:</span>
                            ${valString}
                        </div>`
                    })
                    return html
                },
            },
            xAxis: {
                type: 'category' as const,
                data: labels,
                axisLine: { show: false },
                axisTick: { show: false },
                axisLabel: {
                    show: showXAxisLabels,
                    color: '#94a3b8',
                    fontSize: 9,
                    fontWeight: 700,
                    fontFamily: 'Inter, sans-serif',
                    interval: isDaily
                        ? (labels.length <= 2 ? 0 : Math.floor(labels.length / 2))
                        : Math.max(0, Math.floor(labels.length / 5) - 1),
                },
                splitLine: { show: false },
            },
            yAxis: {
                type: 'value' as const,
                min: 0,
                max: isDaily ? undefined : 100,
                splitNumber: 3,
                axisLine: { show: false },
                axisTick: { show: false },
                axisLabel: {
                    color: '#94a3b8',
                    fontSize: 9,
                    fontWeight: 600,
                    formatter: isDaily ? '{value} ms' : '{value}%',
                },
                splitLine: {
                    lineStyle: { color: '#e2e8f0', width: 1, type: 'dashed' as const },
                },
            },
            series: isDaily ? [
                {
                    name: 'Ping',
                    type: 'line',
                    data: chartPingData,
                    smooth: true,
                    symbol: 'circle',
                    symbolSize: 6,
                    connectNulls: true,
                    lineStyle: { color: COLORS.ping.line, width: 2 },
                    itemStyle: {
                        color: (params: { dataIndex: number }) => {
                            const val = pingValues[params.dataIndex]
                            return val === null || val === undefined ? '#ef4444' : COLORS.ping.line
                        }
                    },
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: COLORS.ping.area },
                            { offset: 1, color: 'rgba(16,185,129,0.04)' },
                        ]),
                    },
                }
            ] : [
                {
                    name: 'CPU',
                    type: 'line',
                    data: cpuValues,
                    smooth: true,
                    symbol: 'none',
                    symbolSize: 0,
                    lineStyle: { color: COLORS.cpu.line, width: 2 },
                    itemStyle: { color: COLORS.cpu.line },
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: COLORS.cpu.area },
                            { offset: 1, color: 'rgba(129,140,248,0.02)' },
                        ]),
                    },
                },
                {
                    name: 'RAM',
                    type: 'line',
                    data: ramValues,
                    smooth: true,
                    symbol: 'none',
                    symbolSize: 0,
                    lineStyle: { color: COLORS.ram.line, width: 2 },
                    itemStyle: { color: COLORS.ram.line },
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: COLORS.ram.area },
                            { offset: 1, color: 'rgba(56,189,248,0.02)' },
                        ]),
                    },
                },
                {
                    name: 'GPU',
                    type: 'line',
                    data: gpuValues,
                    smooth: true,
                    symbol: 'none',
                    symbolSize: 0,
                    lineStyle: { color: COLORS.gpu.line, width: 2 },
                    itemStyle: { color: COLORS.gpu.line },
                    areaStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: COLORS.gpu.area },
                            { offset: 1, color: 'rgba(249,115,22,0.02)' },
                        ]),
                    },
                },
            ],
        }
    }, [labels, cpuValues, ramValues, gpuValues, pingValues, chartPingData, isDaily, showXAxisLabels])

    // Init chart
    useEffect(() => {
        if (!chartRef.current) return
        const chart = echarts.init(chartRef.current, undefined, { renderer: 'canvas' })
        chartInstanceRef.current = chart

        const resizeObserver = new ResizeObserver(() => {
            chart.resize()
        })
        resizeObserver.observe(chartRef.current)

        return () => {
            resizeObserver.disconnect()
            chart.dispose()
            chartInstanceRef.current = null
        }
    }, [])

    // Update option
    useEffect(() => {
        if (chartInstanceRef.current) {
            chartInstanceRef.current.setOption(option, { notMerge: true, lazyUpdate: true })
        }
    }, [option])

    return <div ref={chartRef} style={{ width: '100%', height: 180 }} />
}

export default function MachineChartCard({
    machine,
    timeFilter,
    showXAxisLabels = true,
}: {
    machine: MachineMetrics
    timeFilter: TimeFilter
    showXAxisLabels?: boolean
}) {
    const cpuValues = machine.history.map((p) => p.cpu)
    const ramValues = machine.history.map((p) => p.ram)
    const gpuValues = machine.history.map((p) => p.gpu ?? 0)
    const pingValues = machine.history.map((p) => p.ping ?? null)
    const labels = machine.history.map((p) => p.timeLabel)
    const isDaily = timeFilter === 'daily'

    const lastCpu = cpuValues.length > 0 ? cpuValues[cpuValues.length - 1] : 0
    const lastRam = ramValues.length > 0 ? ramValues[ramValues.length - 1] : 0
    const lastGpu = gpuValues.length > 0 ? gpuValues[gpuValues.length - 1] : 0
    const lastPing = pingValues.length > 0 ? pingValues[pingValues.length - 1] : null

    return (
        <div className="machine-chart-card glass-card card-animate">
            <div className="machine-chart-header">
                <h3 className="machine-chart-name">{machine.label}</h3>
                <div className="machine-chart-stats">
                    {isDaily ? (
                        lastPing !== null && lastPing !== undefined ? (
                            <span className="live-stat stat-ping-live">
                                Ping: {lastPing.toFixed(0)} ms
                            </span>
                        ) : (
                            <span className="live-stat stat-ping-timeout">
                                Ping: 0 ms
                            </span>
                        )
                    ) : (
                        <>
                            <span className="live-stat stat-cpu-live">CPU: {lastCpu.toFixed(1)}%</span>
                            <span className="live-stat stat-ram-live">RAM: {lastRam.toFixed(1)}%</span>
                            <span className="live-stat stat-gpu-live">GPU: {lastGpu.toFixed(1)}%</span>
                        </>
                    )}
                </div>
            </div>

            <EChartsLine
                labels={labels}
                cpuValues={cpuValues}
                ramValues={ramValues}
                gpuValues={gpuValues}
                pingValues={pingValues}
                isDaily={isDaily}
                showXAxisLabels={showXAxisLabels}
            />
        </div>
    )
}

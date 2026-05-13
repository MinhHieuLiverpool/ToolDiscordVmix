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
}

function EChartsLine({
    labels,
    cpuValues,
    ramValues,
    gpuValues,
    isDaily,
    showXAxisLabels,
}: {
    labels: string[]
    cpuValues: number[]
    ramValues: number[]
    gpuValues: number[]
    isDaily: boolean
    showXAxisLabels: boolean
}) {
    const chartRef = useRef<HTMLDivElement>(null)
    const chartInstanceRef = useRef<echarts.ECharts | null>(null)

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
                formatter: (params: Array<{ seriesName: string; value: number; axisValueLabel: string; color: string }>) => {
                    if (!Array.isArray(params) || params.length === 0) return ''
                    const time = params[0].axisValueLabel || ''
                    let html = `<div style="font-weight:700;margin-bottom:4px;font-size:11px">${time}</div>`
                    params.forEach((p) => {
                        html += `<div style="display:flex;align-items:center;gap:6px;font-size:11px">
                            <span style="width:8px;height:8px;border-radius:50%;background:${p.color};display:inline-block"></span>
                            <span style="font-weight:600">${p.seriesName}:</span>
                            <span style="font-weight:800">${(p.value ?? 0).toFixed(1)}%</span>
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
                max: 100,
                splitNumber: 3,
                axisLine: { show: false },
                axisTick: { show: false },
                axisLabel: {
                    color: '#94a3b8',
                    fontSize: 9,
                    fontWeight: 600,
                    formatter: '{value}%',
                },
                splitLine: {
                    lineStyle: { color: '#e2e8f0', width: 1, type: 'dashed' as const },
                },
            },
            series: [
                {
                    name: 'CPU',
                    type: 'line',
                    data: cpuValues,
                    smooth: true,
                    symbol: isDaily ? 'circle' : 'none',
                    symbolSize: isDaily ? 6 : 0,
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
                    symbol: isDaily ? 'circle' : 'none',
                    symbolSize: isDaily ? 6 : 0,
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
                    symbol: isDaily ? 'circle' : 'none',
                    symbolSize: isDaily ? 6 : 0,
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
    }, [labels, cpuValues, ramValues, gpuValues, isDaily, showXAxisLabels])

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
            chartInstanceRef.current.setOption(option, { notMerge: false, lazyUpdate: true })
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
    const labels = machine.history.map((p) => p.timeLabel)
    const isDaily = timeFilter === 'daily'

    const lastCpu = cpuValues.length > 0 ? cpuValues[cpuValues.length - 1] : 0
    const lastRam = ramValues.length > 0 ? ramValues[ramValues.length - 1] : 0

    return (
        <div className="machine-chart-card glass-card card-animate">
            <div className="machine-chart-header">
                <h3 className="machine-chart-name">{machine.label}</h3>
                <div className="machine-chart-stats">
                    <span className="live-stat stat-cpu-live">CPU: {lastCpu.toFixed(1)}%</span>
                    <span className="live-stat stat-ram-live">RAM: {lastRam.toFixed(1)}%</span>
                    <span className="live-stat stat-gpu-live">GPU: {(machine.history[machine.history.length - 1]?.gpu ?? 0).toFixed(1)}%</span>
                </div>
            </div>

            <EChartsLine
                labels={labels}
                cpuValues={cpuValues}
                ramValues={ramValues}
                gpuValues={gpuValues}
                isDaily={isDaily}
                showXAxisLabels={showXAxisLabels}
            />
        </div>
    )
}

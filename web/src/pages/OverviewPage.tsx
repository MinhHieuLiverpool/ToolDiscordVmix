import { useDashboardContext } from '../hooks/useDashboardContext'
import StatusSection from '../components/StatusSection'
import { useState, useMemo, useRef, useEffect } from 'react'
import Dialog from '../components/ui/Dialog'
import { saveGameSelected } from '../services/api'
import { showToast } from '../components/ui/Toast'
import { hasActionPermission } from '../services/auth'
import { useLanguage } from '../config/i18n'

export default function OverviewPage() {
    const { t } = useLanguage()
    const canEditOverview = hasActionPermission('Tổng quan', 'edit')

    const {
        rows,
        allRows,
        loading,
        error,
        selectedGame,
        setSelectedGame,
        gameAssignments,
        loadAssignments,
        isGameLocked,
        visibilityFilter,
        setVisibilityFilter,
    } = useDashboardContext() as any

    const [searchTerm, setSearchTerm] = useState('')
    const [dropdownOpen, setDropdownOpen] = useState(false)
    const [visibilityDropdownOpen, setVisibilityDropdownOpen] = useState(false)
    const [isEditMode, setIsEditMode] = useState(false)

    const dropdownRef = useRef<HTMLDivElement>(null)
    const visibilityDropdownRef = useRef<HTMLDivElement>(null)

    // Dialog states
    const [isDialogOpen, setIsDialogOpen] = useState(false)
    const [dialogSearchTerm, setDialogSearchTerm] = useState('')
    const [dialogGame, setDialogGame] = useState('Liên Quân Mobile')
    const [dialogSelectedMachines, setDialogSelectedMachines] = useState<string[]>([])
    const [savingAssignments, setSavingAssignments] = useState(false)

    // Close dropdown on outside click
    useEffect(() => {
        function handleClick(e: MouseEvent) {
            if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
                setDropdownOpen(false)
            }
            if (visibilityDropdownRef.current && !visibilityDropdownRef.current.contains(e.target as Node)) {
                setVisibilityDropdownOpen(false)
            }
        }
        document.addEventListener('mousedown', handleClick)
        return () => document.removeEventListener('mousedown', handleClick)
    }, [])

    // Sync selected machines in dialog when dialogGame or assignments change
    useEffect(() => {
        const assignment = gameAssignments.find((a: any) => a.game === dialogGame)
        setDialogSelectedMachines(assignment ? assignment.machines : [])
        setDialogSearchTerm('')
    }, [dialogGame, gameAssignments, isDialogOpen])

    const games = useMemo(() => {
        const list = [
            { id: '__all__', label: t('overview.allGames') }
        ]
        if (gameAssignments) {
            gameAssignments.forEach((assignment: any) => {
                if (assignment.game && assignment.visible_status !== 'OFF' && !list.some(g => g.id === assignment.game)) {
                    list.push({ id: assignment.game, label: assignment.game })
                }
            })
        }
        return list
    }, [gameAssignments, t])

    const uniqueMachineNames = useMemo(() => {
        const names = new Set<string>()
        allRows.forEach((row: any) => {
            if (row.data.name) {
                names.add(row.data.name)
            }
        })
        return Array.from(names).sort()
    }, [allRows])

    // Filter machines in overview dashboard by searchTerm (name, name_edit, ip, ipwan, port)
    const filteredRows = useMemo(() => {
        if (!searchTerm.trim()) return rows
        const term = searchTerm.toLowerCase().trim()
        return (rows || []).filter((r: any) => {
            const name = (r.data?.name || '').toLowerCase()
            const nameEdit = (r.data?.name_edit || '').toLowerCase()
            const ip = (r.data?.ip || '').toLowerCase()
            const ipwan = (r.data?.ipwan || '').toLowerCase()
            const port = String(r.data?.port || '').toLowerCase()
            const fullIp = `${ip}:${port}`
            return (
                name.includes(term) ||
                nameEdit.includes(term) ||
                ip.includes(term) ||
                ipwan.includes(term) ||
                fullIp.includes(term)
            )
        })
    }, [rows, searchTerm])

    // Filter machines in dialog checklist by dialogSearchTerm (name, name_edit, ip, ipwan, port)
    const filteredDialogMachines = useMemo(() => {
        if (!dialogSearchTerm.trim()) return uniqueMachineNames
        const term = dialogSearchTerm.toLowerCase().trim()
        return uniqueMachineNames.filter((name) => {
            const machineRow = allRows.find((r: any) => r.data.name === name)
            const nameEdit = (machineRow?.data?.name_edit || '').toLowerCase()
            const ip = (machineRow?.data?.ip || '').toLowerCase()
            const ipwan = (machineRow?.data?.ipwan || '').toLowerCase()
            const port = String(machineRow?.data?.port || '').toLowerCase()
            const fullIp = `${ip}:${port}`
            return (
                name.toLowerCase().includes(term) ||
                nameEdit.includes(term) ||
                ip.includes(term) ||
                ipwan.includes(term) ||
                fullIp.includes(term)
            )
        })
    }, [uniqueMachineNames, dialogSearchTerm, allRows])

    const selectedLabel = games.find(g => g.id === selectedGame)?.label || t('overview.selectGame')

    const handleSaveAssignments = async () => {
        setSavingAssignments(true)
        try {
            const res = await saveGameSelected(dialogGame, dialogSelectedMachines)
            if (res.success) {
                showToast(t('overview.savedSuccess').replace('{game}', dialogGame), 'success')
                await loadAssignments()
                setIsDialogOpen(false)
            } else {
                showToast(res.message || t('overview.saveError'), 'error')
            }
        } catch (err: any) {
            console.error('Error saving assignments:', err)
            showToast(t('common.error') + ': ' + (err.message || err), 'error')
        } finally {
            setSavingAssignments(false)
        }
    }

    return (
        <>
            <div className="page-header flex flex-col md:flex-row justify-end items-start md:items-center gap-4">
                {/* Actions container */}
                <div className="flex items-center gap-3 flex-wrap">
                    {/* Machine Search */}
                    <div className="table-search-wrap" style={{ minWidth: '190px' }}>
                        <svg className="table-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                            <circle cx="11" cy="11" r="8" />
                            <line x1="21" y1="21" x2="16.65" y2="16.65" />
                        </svg>
                        <input
                            type="text"
                            className="table-search-input"
                            placeholder={t('overview.searchPlaceholder')}
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                        />
                        {searchTerm && (
                            <button
                                type="button"
                                onClick={() => setSearchTerm('')}
                                style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '0 4px', color: '#94a3b8', fontSize: '0.8rem' }}
                                title={t('common.close')}
                            >
                                ✕
                            </button>
                        )}
                    </div>

                    {/* Game Filter */}
                    {!isGameLocked ? (
                        <div className="flex items-center gap-2">
                            <span className="text-xs font-semibold text-slate-400">{t('overview.gameChannel')}</span>
                            <div className="custom-dropdown" ref={dropdownRef} style={{ minWidth: '180px' }}>
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
                                        <div className="dropdown-options">
                                            {games.map((g) => (
                                                <button
                                                    type="button"
                                                    key={g.id}
                                                    className={`dropdown-option ${selectedGame === g.id ? 'option-active' : ''}`}
                                                    onClick={() => {
                                                        setSelectedGame(g.id)
                                                        setDropdownOpen(false)
                                                    }}
                                                >
                                                    {g.label}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    ) : (
                        selectedGame !== '__all__' ? (
                            <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-100 dark:bg-slate-900 rounded-lg">
                                <span className="text-xs font-semibold text-slate-400">{t('overview.gameChannel')}</span>
                                <span className="text-xs font-bold text-purple-600 dark:text-purple-400">{selectedLabel}</span>
                            </div>
                        ) : null
                    )}

                    {/* Visibility Filter */}
                    <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-slate-400">{t('overview.display')}</span>
                        <div className="custom-dropdown" ref={visibilityDropdownRef} style={{ minWidth: '110px' }}>
                            <button
                                type="button"
                                className={`dropdown-trigger ${visibilityDropdownOpen ? 'dropdown-open' : ''}`}
                                onClick={() => setVisibilityDropdownOpen(!visibilityDropdownOpen)}
                            >
                                <span className="dropdown-trigger-text">
                                    {visibilityFilter === 'all' && t('overview.displayAll')}
                                    {visibilityFilter === 'visible' && t('overview.displayVisible')}
                                    {visibilityFilter === 'hidden' && t('overview.displayHidden')}
                                </span>
                                <svg className={`dropdown-chevron ${visibilityDropdownOpen ? 'chevron-up' : ''}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                    <polyline points="6 9 12 15 18 9" />
                                </svg>
                            </button>

                            {visibilityDropdownOpen && (
                                <div className="dropdown-menu">
                                    <div className="dropdown-options">
                                        {[
                                            { id: 'all', label: t('overview.displayAll') },
                                            { id: 'visible', label: t('overview.displayVisible') },
                                            { id: 'hidden', label: t('overview.displayHidden') }
                                        ].map((item) => (
                                            <button
                                                type="button"
                                                key={item.id}
                                                className={`dropdown-option ${visibilityFilter === item.id ? 'option-active' : ''}`}
                                                onClick={() => {
                                                    setVisibilityFilter(item.id)
                                                    setVisibilityDropdownOpen(false)
                                                }}
                                            >
                                                {item.label}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Add to channel button */}
                    {!isGameLocked && canEditOverview && (
                        <button
                            onClick={() => {
                                setDialogGame(selectedGame === '__all__' ? 'Liên Quân Mobile' : selectedGame)
                                setIsDialogOpen(true)
                            }}
                            className="bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold px-3 py-2 rounded-lg flex items-center gap-1.5 transition-colors shrink-0"
                            title={t('overview.assignChannelsTooltip')}
                        >
                            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                            </svg>
                            {t('overview.assignChannels')}
                        </button>
                    )}

                    {/* Edit mode toggle */}
                    {canEditOverview && (
                        <button
                            onClick={() => setIsEditMode(!isEditMode)}
                            className={`text-xs font-bold px-3 py-2 rounded-lg flex items-center gap-1.5 transition-all shrink-0 ${
                                isEditMode
                                    ? 'bg-red-500/90 hover:bg-red-500 text-white ring-2 ring-red-400/40'
                                    : 'bg-slate-700/60 hover:bg-slate-600/80 text-slate-300 hover:text-white'
                            }`}
                            title={isEditMode ? t('overview.exitEditMode') : t('overview.editMode')}
                        >
                            {isEditMode ? (
                                <>
                                    <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                                    </svg>
                                    {t('overview.exitEditMode')}
                                </>
                            ) : (
                                <>
                                    <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                                    </svg>
                                    {t('overview.editMode')}
                                </>
                            )}
                        </button>
                    )}
                </div>
            </div>

            <StatusSection rows={filteredRows} loading={loading} error={error} isEditMode={isEditMode} />

            {/* Config Game assignments dialog */}
            <Dialog
                open={isDialogOpen}
                onClose={() => setIsDialogOpen(false)}
                title={t('overview.dialogTitle')}
            >
                <div className="flex flex-col gap-4 text-slate-800 dark:text-slate-100">
                    <div>
                        <label className="block text-xs font-bold text-slate-400 mb-1.5 uppercase">{t('overview.dialogGameLabel')}:</label>
                        <input
                            type="text"
                            value={dialogGame}
                            onChange={(e) => setDialogGame(e.target.value)}
                            placeholder={t('overview.dialogGameLabel')}
                            className="w-full bg-white dark:bg-slate-950 border border-purple-500/30 dark:border-purple-500/20 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 rounded-xl px-3 py-2.5 text-xs font-semibold text-slate-800 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 outline-none transition-all"
                        />
                    </div>

                    <div>
                        <div className="flex items-center justify-between mb-1.5 flex-wrap gap-2">
                            <label className="block text-xs font-bold text-slate-400 uppercase">
                                {t('overview.dialogMachinesLabel')} ({dialogSelectedMachines.length}/{uniqueMachineNames.length}):
                            </label>
                            <div className="flex items-center gap-1.5">
                                <button
                                    type="button"
                                    onClick={() => {
                                        if (dialogSearchTerm.trim()) {
                                            setDialogSelectedMachines(prev => Array.from(new Set([...prev, ...filteredDialogMachines])))
                                        } else {
                                            setDialogSelectedMachines([...uniqueMachineNames])
                                        }
                                    }}
                                    className="text-[11px] font-semibold text-purple-600 hover:text-purple-700 dark:text-purple-400 px-1.5 py-0.5 rounded hover:bg-purple-50 dark:hover:bg-purple-950/30 transition-colors"
                                >
                                    {t('channels.selectAll')}
                                </button>
                                <span className="text-slate-300 dark:text-slate-700 text-xs">|</span>
                                <button
                                    type="button"
                                    onClick={() => {
                                        if (dialogSearchTerm.trim()) {
                                            const setFiltered = new Set(filteredDialogMachines)
                                            setDialogSelectedMachines(prev => prev.filter(m => !setFiltered.has(m)))
                                        } else {
                                            setDialogSelectedMachines([])
                                        }
                                    }}
                                    className="text-[11px] font-semibold text-slate-500 hover:text-slate-700 dark:text-slate-400 px-1.5 py-0.5 rounded hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                                >
                                    {t('channels.deselectAll')}
                                </button>
                            </div>
                        </div>

                        {/* Search input in dialog */}
                        <div className="table-search-wrap mb-2" style={{ maxWidth: '100%', boxSizing: 'border-box' }}>
                            <svg className="table-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                <circle cx="11" cy="11" r="8" />
                                <line x1="21" y1="21" x2="16.65" y2="16.65" />
                            </svg>
                            <input
                                type="text"
                                className="table-search-input"
                                placeholder={t('overview.searchMachinesPlaceholder')}
                                value={dialogSearchTerm}
                                onChange={(e) => setDialogSearchTerm(e.target.value)}
                            />
                            {dialogSearchTerm && (
                                <button
                                    type="button"
                                    onClick={() => setDialogSearchTerm('')}
                                    style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '0 4px', color: '#94a3b8', fontSize: '0.8rem' }}
                                >
                                    ✕
                                </button>
                            )}
                        </div>

                        <div className="max-h-60 overflow-y-auto border border-slate-200 dark:border-slate-800 rounded-lg p-2 bg-slate-50 dark:bg-slate-950/40 flex flex-col gap-2">
                            {filteredDialogMachines.map((name) => {
                                const isChecked = dialogSelectedMachines.includes(name)
                                const machineRow = allRows.find((r: any) => r.data.name === name)
                                const displayName = machineRow?.data.name_edit
                                    ? `${machineRow.data.name_edit} (${name})`
                                    : name
                                const ip = machineRow?.data?.ip
                                return (
                                    <label key={name} className="flex items-center gap-2.5 px-2 py-1.5 rounded hover:bg-slate-200 dark:hover:bg-white/5 cursor-pointer text-xs font-medium text-slate-700 dark:text-slate-200 select-none">
                                        <input
                                            type="checkbox"
                                            checked={isChecked}
                                            onChange={(e) => {
                                                if (e.target.checked) {
                                                    setDialogSelectedMachines([...dialogSelectedMachines, name])
                                                } else {
                                                    setDialogSelectedMachines(dialogSelectedMachines.filter(m => m !== name))
                                                }
                                            }}
                                            className="rounded border-slate-300 dark:border-slate-700 text-purple-600 focus:ring-purple-500/30 bg-white dark:bg-slate-800 h-4 w-4 cursor-pointer"
                                        />
                                        <div className="flex items-center gap-1.5 flex-wrap">
                                            <span className="break-all">{displayName}</span>
                                            {ip && <span className="font-mono text-[11px] text-slate-400">({ip})</span>}
                                        </div>
                                    </label>
                                )
                            })}
                            {filteredDialogMachines.length === 0 && (
                                <div className="text-center text-slate-500 py-6 text-xs">
                                    {t('overview.noMachinesFound')}
                                </div>
                            )}
                        </div>
                    </div>

                    <div className="flex justify-end gap-2 mt-2">
                        <button
                            onClick={() => setIsDialogOpen(false)}
                            className="px-4 py-2 rounded-lg text-xs font-semibold text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/5 transition-colors"
                        >
                            {t('common.cancel')}
                        </button>
                        <button
                            onClick={handleSaveAssignments}
                            disabled={savingAssignments}
                            className="bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold px-4 py-2 rounded-lg transition-colors flex items-center gap-1.5 disabled:opacity-50"
                        >
                            {savingAssignments ? t('overview.savingAssignments') : t('common.save')}
                        </button>
                    </div>
                </div>
            </Dialog>
        </>
    )
}

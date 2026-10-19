import { useLanguage } from '../config/i18n'

const EXTENSIONS = [
  {
    id: 'studio-media-toolkit',
    nameKey: 'extensions.studioMediaToolkit',
    descKey: 'extensions.studioMediaToolkitDesc',
    filename: 'StudioMediaToolkit.exe',
    downloadUrl: '/extensions/StudioMediaToolkit.exe',
    size: '248.8 MB',
    version: '1.0.0',
    platform: 'Windows',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <rect x="2" y="3" width="20" height="14" rx="2" />
        <path d="M8 21h8" />
        <path d="M12 17v4" />
        <path d="M7 8l3 3-3 3" />
        <line x1="13" y1="14" x2="17" y2="14" />
      </svg>
    ),
    accent: 'indigo',
  },
  {
    id: 'win-admin-toolkit',
    nameKey: 'extensions.winAdminToolkit',
    descKey: 'extensions.winAdminToolkitDesc',
    filename: 'WinAdminToolkit.exe',
    downloadUrl: '/extensions/WinAdminToolkit.exe',
    size: '10.8 MB',
    version: '1.0.0',
    platform: 'Windows',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
        <circle cx="12" cy="12" r="3" />
      </svg>
    ),
    accent: 'emerald',
  },
]

const ACCENT_MAP: Record<string, { iconBg: string; iconText: string; badge: string; btnBg: string; border: string }> = {
  indigo: {
    iconBg: 'bg-indigo-50 dark:bg-indigo-950/25',
    iconText: 'text-indigo-500 dark:text-indigo-400',
    badge: 'bg-indigo-50 text-indigo-600 border-indigo-100 dark:bg-indigo-950/20 dark:text-indigo-400 dark:border-indigo-900/30',
    btnBg: 'bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-600 dark:hover:bg-indigo-500',
    border: 'border-indigo-200/60 dark:border-indigo-800/30',
  },
  emerald: {
    iconBg: 'bg-emerald-50 dark:bg-emerald-950/25',
    iconText: 'text-emerald-500 dark:text-emerald-400',
    badge: 'bg-emerald-50 text-emerald-600 border-emerald-100 dark:bg-emerald-950/20 dark:text-emerald-400 dark:border-emerald-900/30',
    btnBg: 'bg-emerald-600 hover:bg-emerald-700 dark:bg-emerald-600 dark:hover:bg-emerald-500',
    border: 'border-emerald-200/60 dark:border-emerald-800/30',
  },
}

export default function ExtensionsPage() {
  const { t } = useLanguage()

  return (
    <div className="p-6">
      {/* Header */}
      <div className="page-header mb-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h2 className="page-title text-2xl font-black text-slate-800 dark:text-slate-100">
            {t('extensions.title')}
          </h2>
          <p className="page-description text-slate-500 text-sm mt-1">
            {t('extensions.desc')}
          </p>
        </div>
      </div>

      {/* Extensions Table */}
      <div className="bg-white dark:bg-slate-900/40 rounded-[12px] border border-slate-200 dark:border-slate-800/80 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th className="py-3 px-5">{t('extensions.title')}</th>
                <th className="py-3 px-5 text-center">Version</th>
                <th className="py-3 px-5 text-center">Platform</th>
                <th className="py-3 px-5 text-center">{t('common.status')}</th>
                <th className="py-3 px-5 text-right">{t('common.actions')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-900">
              {EXTENSIONS.map((ext) => {
                const colors = ACCENT_MAP[ext.accent]
                return (
                  <tr key={ext.id} className="text-xs hover:bg-slate-50/50 dark:hover:bg-slate-900/10 transition-all">
                    {/* Name + Description */}
                    <td className="py-4 px-5">
                      <div className="flex items-center gap-3">
                        <div className={`w-9 h-9 rounded-lg ${colors.iconBg} ${colors.iconText} flex items-center justify-center shrink-0 [&>svg]:w-[18px] [&>svg]:h-[18px]`}>
                          {ext.icon}
                        </div>
                        <div className="min-w-0">
                          <div className="font-black text-slate-800 dark:text-slate-200 text-sm leading-tight">
                            {t(ext.nameKey)}
                          </div>
                          <div className="text-[10.5px] text-slate-400 dark:text-slate-500 mt-0.5 leading-snug max-w-xs">
                            {t(ext.descKey)}
                          </div>
                        </div>
                      </div>
                    </td>

                    {/* Version */}
                    <td className="py-4 px-5 text-center">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold border ${colors.badge}`}>
                        v{ext.version}
                      </span>
                    </td>

                    {/* Platform */}
                    <td className="py-4 px-5 text-center">
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400">
                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                          <rect x="2" y="3" width="20" height="14" rx="2" /><path d="M8 21h8M12 17v4" />
                        </svg>
                        {ext.platform}
                      </span>
                    </td>

                    {/* Size */}
                    <td className="py-4 px-5 text-center">
                      <span className="text-[11px] font-mono font-bold text-slate-500 dark:text-slate-400">
                        {ext.size}
                      </span>
                    </td>

                    {/* Download */}
                    <td className="py-4 px-5 text-right">
                      <a
                        href={ext.downloadUrl}
                        download={ext.filename}
                        className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-[11px] font-bold text-white ${colors.btnBg} transition-all shadow-sm hover:shadow active:scale-[0.97]`}
                      >
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                          <polyline points="7 10 12 15 17 10" />
                          <line x1="12" y1="15" x2="12" y2="3" />
                        </svg>
                        {t('extensions.download')}
                      </a>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

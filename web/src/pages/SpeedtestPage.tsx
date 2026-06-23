export default function SpeedtestPage() {
    return (
        <div className="p-6">
            {/* Header */}
            <div className="page-header mb-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                <div>
                    <h2 className="page-title text-2xl font-black text-slate-800 dark:text-slate-100">Speedtest</h2>
                    <p className="page-description text-slate-500 text-sm">Kiểm tra tốc độ băng thông internet hiện tại của hệ thống.</p>
                </div>
                <a
                    href="https://www.speedtest.net/"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl text-xs flex items-center gap-1.5 transition-colors self-start md:self-auto"
                    style={{ textDecoration: 'none' }}
                >
                    Mở Speedtest.net (Tab mới)
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14L21 3" />
                    </svg>
                </a>
            </div>

            {/* Embedded Speedtest Widget */}
            <div className="bg-white dark:bg-slate-900/45 rounded-2xl overflow-hidden shadow-sm border border-slate-100 dark:border-slate-800/80 h-[620px] w-full relative">
                <iframe
                    src="https://openspeedtest.com/speedtest"
                    className="w-full h-full border-0 absolute inset-0"
                    title="OpenSpeedTest Widget"
                    allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture"
                    sandbox="allow-scripts allow-same-origin"
                />
            </div>
        </div>
    )
}

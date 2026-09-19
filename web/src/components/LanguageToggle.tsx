import { useLanguage } from '../config/i18n'
import { FlagVN, FlagEN } from './FlagIcons'

export default function LanguageToggle({ className = '' }: { className?: string }) {
    const { lang, setLang, t } = useLanguage()

    const toggleLang = () => {
        setLang(lang === 'vi' ? 'en' : 'vi')
    }

    return (
        <button
            type="button"
            onClick={toggleLang}
            className={`lang-toggle-btn ${className}`}
            title={t('language.label')}
            aria-label="Toggle language"
        >
            <span className={`lang-toggle-option ${lang === 'vi' ? 'lang-toggle-active' : ''}`}>
                <FlagVN size={16} />
                <span>VN</span>
            </span>
            <span className={`lang-toggle-option ${lang === 'en' ? 'lang-toggle-active' : ''}`}>
                <FlagEN size={16} />
                <span>EN</span>
            </span>
            <span
                className="lang-toggle-slider"
                style={{ transform: lang === 'en' ? 'translateX(100%)' : 'translateX(0)' }}
            />
        </button>
    )
}

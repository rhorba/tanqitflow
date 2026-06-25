import { useTranslation } from 'react-i18next'

const LANGUAGES = [
  { code: 'fr', label: 'FR' },
  { code: 'ar', label: 'ع' },
]

export default function Header() {
  const { t, i18n } = useTranslation()

  const switchLanguage = (code: string) => {
    i18n.changeLanguage(code)
  }

  return (
    <header className="bg-white border-b border-gray-200 shadow-sm">
      <div className="container mx-auto px-4 h-16 flex items-center justify-between">
        {/* Logo + name */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-sm">T</span>
          </div>
          <span className="font-semibold text-gray-900 text-lg">{t('app.name')}</span>
        </div>

        {/* Language switcher */}
        <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
          {LANGUAGES.map((lang) => (
            <button
              key={lang.code}
              onClick={() => switchLanguage(lang.code)}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                i18n.language === lang.code
                  ? 'bg-white text-brand-700 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
              aria-label={`Switch to ${lang.code === 'fr' ? 'French' : 'Arabic'}`}
            >
              {lang.label}
            </button>
          ))}
        </div>
      </div>
    </header>
  )
}

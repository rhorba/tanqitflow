import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'

import frCommon from './fr/common.json'
import arCommon from './ar/common.json'

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      fr: { common: frCommon },
      ar: { common: arCommon },
    },
    defaultNS: 'common',
    fallbackLng: 'fr',
    supportedLngs: ['fr', 'ar'],
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
      lookupLocalStorage: 'tanqitflow_lang',
    },
    interpolation: {
      escapeValue: false,
    },
  })

export default i18n

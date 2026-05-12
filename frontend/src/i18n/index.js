import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import en from './en.json';
import hi from './hi.json';
import ta from './ta.json';
import kn from './kn.json';

i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, hi: { translation: hi }, ta: { translation: ta }, kn: { translation: kn } },
  lng: localStorage.getItem('language') || 'en',
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
  missingKeyHandler: (lngs, ns, key) => {
    console.warn(`[i18n] Missing key: "${key}" for language: ${lngs}`);
  },
  saveMissing: true,
});

export default i18n;
